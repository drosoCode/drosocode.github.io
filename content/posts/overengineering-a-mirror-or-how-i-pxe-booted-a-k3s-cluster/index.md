---
title: "Overengineering a mirror or how I PXE-booted a k3s cluster"
date: 2026-02-14T00:00:00+00:00
draft: true
tags:
- hardware
- infra
- k8s
---

## Introduction

From the last years, I started to gain interest in another new hobby: dancing. Naturally, I would like to practice at home. The ideal environment would be a large empty room with full size mirrors on the wall, but I live in Paris so the rent is very expensive and thus I do not have this kind of space, actually I do not even have free wall without any furniture where I could place a mirror. 

So, there was two problems: getting enough empty space to move, and getting some kind of visual feedback.

The free space problem can be solved quite easily by lifting my bed against the wall (see the bonus at the end of this post). But for the mirror, I wanted to take advantage of my existing infrastructure and software development background.

## The Idea

While I do not have any free space on my walls, I do have a quite large TV in front of my bed. I also happen to have an old Kinect (v2) laying around, so with the help of a tiny computer I could place the Kinect on top of the tv, capture the video from the kinect and display it directly on the TV.

But where is the fun if there's no overly-complex infra involved ?

So, I decided to package the application capturing and restreaming the Kinect video as a container and deploy this container in my k3s cluster.

I already have a k3s master node on my proxmox server (installed using packer/terraform/fluxcd), so I can just add my mini-PC as another node on this cluster. And since we want some complexity (-and to learn a few new things), I decided to make this mini-PC use network boot (with PXE and iSCSI) to boot from a pre-configured disk image for the cluster (generated using packer) on my storage server.

Initially I wanted to go with the Raspberry Pi 4 (as the Kinect V2 uses a much higher USB bandwidth than the Kinect V1 and thus requires a USB 3 port), but it just wasn't powerful enough (got around 7-14 fps, depending on the power supply). So I bought a Dell OptiPlex 3050 Tiny as I wanted to test this kind of mini PC for a while.

Since the configuration is a bit different between the mini-PC (amd64) and the rpi (arm64), I will show the network boot process for both.

## Network Boot

### Boot Process

There are multiple stages to boot using the network:
- First you must configure the device to use network boot (as this is usually not enabled by default)
- Then, when booting, the device will send a DHCP request (DHCPDISCOVER), for PXE there are additional fields:
    -  Vendor-Class Identifier (Option 60): the vendor class identifier
        - "PXEClient" for the Raspberry PI
        - "PXEClient:Arch:00007" for UEFI x64 firmwares [TODO: check this]
        - "PXEClient:Arch:00006" for UEFI x86 firmwares
- The DHCP server then responds with the proposed IP-address (DHCPOFFER) and additional parameters:
    - Vendor-specific Information (Option 43): not required for amd64, but for RPI this needs to be set to "Raspberry Pi Boot   " (with the 3 spaces at the end)
    - TFTP Server Name (Option 66): the IP of the TFTP server that will be used to load the bootfile
    - Bootfile Name (Option 67): the path (on the TFTP server) of the boot file to fetch and load
    - Next-Server: This corresponds to the `siaddr` field in the DHCP packet, for iPXE, we will also need to set the it to the IP of the TFTP server to load the kernel/initramfs [TODO: check this]
- The client accepts the DHCP offer, fetches the Bootfile on the specified TFTP server and loads it [TODO: check this]
- For Linux (the only case exposed here), the kernel and initramfs will be fetched from the TFTP server by the bootfile and then be loaded
- Then, the iSCSI drive will be mounted as the root path and the system will finish starting up

For more info on DHCP, see the [RFC2131](https://www.rfc-editor.org/rfc/rfc2131) and [RFC2132](https://www.rfc-editor.org/rfc/rfc2132).

### Creating disk images

To make disk image easily buildable and reproducibles, I will use Hashicorp's [Packer](https://developer.hashicorp.com/packer) tool (that I'm already using to build my cloud-init images for k3s on proxmox).

#### For amd64 devices

For the amd64 devices, I will use the debian installer to create the image.

We first need to import the qemu builder in packer:
```hcl
packer {
  required_plugins {
    qemu = {
      version = "~> 1"
      source  = "github.com/hashicorp/qemu"
    }
  }
}
```

Make sure you also have qemu installed and that you have the required OMVF files for the UEFI VM firmware.

We can then define a source and a builder:
{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/builder/debian_amd64.pkr.hcl" >}}

The http options allows to create a local http server that serves the files located in the "http" folder (relative to our packer script). This will be used to load our preseed file.
```hcl
http_directory = "http"
http_port_min  = 8100
http_port_max  = 8100
```

Then, the boot_command set the command that will be executed immediately when the VM boots, the command is entered directly on the console using an emulated keyboard. The "url" parameter specifies the path to our preseed file (with the HTTPIP and HTTPPort being automatically replaced by packer by the running server params).
```hcl
boot_command = [
    "<wait>c<wait>",
    "linux /install.amd/vmlinuz ",
    "auto=true ",
    "url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/qemu_uefi_preseed.cfg ",
    "hostname=${var.template_name} ",
    "domain=lan ",
    "interface=auto ",
    "vga=788 noprompt quiet --<enter>",
    "initrd /install.amd/initrd.gz<enter>",
    "boot<enter>"
]
```

The preseed file is the file that we can load in the debian installer to enable unattended installations. Most of this file is copied from the [example provided by debian](https://www.debian.org/releases/stable/example-preseed.txt).

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/builder/qemu_uefi_preseed.cfg" >}}

For partitioning, we're using a custom recipe to add an EFI boot partition (in FAT32) and then use all of the remaining space for the root partition (EXT4). I wanted to explicitely disable the swap, but if you choose to keep it, make sure that you create the swap partition BEFORE the root partition, otherwise if will be difficult to expand the root filesystem later:
```ini
d-i partman-basicfilesystems/no_swap boolean false
d-i partman-auto/expert_recipe string myroot :: 512 512 512 fat32 \
     $primary{ } $bootable{ } method{ efi } \
     format{ } \
    . \
    1000 50 -1 ext4 \
     $primary{ } method{ format } \
     format{ } use_filesystem{ } filesystem{ ext4 } \
     mountpoint{ / } \
    .
d-i partman-auto/choose_recipe select myroot
```

At the end of the file, I also added a line to permit password login for packer to be able to ssh into the VM after the system install has finished:
```ini
d-i preseed/late_command string in-target sed -e 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' -i /etc/ssh/sshd_config
```

Once the initial system installation is completed, packer can ssh to the VM and execute our provisionners.

The first provisionner is used to execute our custom installation script, with some options to set the K3S version, and enable/disable some components.

The other provisionners are used to define `authorized_keys` and revert the sshd changes to re-enable publickey-only auth.

#### For Raspberry PIs

For the Raspberry PI, instead of creating a debian image from scratch, I'm using the raspios-lite official image (which is itself based on debian).

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/builder/rpi_arm64.pkr.hcl" >}}

Since the rpi architecture is different from my base system (x64), I used a custom builder for ARM:
 - A few of them are listed on the [packer docs](https://developer.hashicorp.com/packer/docs/builders/community-supported)
 - The one that I actually setteld with was this fork: https://github.com/michalfita/packer-plugin-cross which added support for the new packer plugin system
 - The plugin relies on `qemu-aarch64-static`, so make sure that this is installed on your machine

Import it with:
```hcl
packer {
  required_plugins {
    cross = {
      version = ">= 1.1.3"
      source  = "github.com/michalfita/cross"
    }
  }
}
```

As the image file is compressed with xz, we need to add a custom command for extracting the downloaded image: `file_unarchive_cmd = ["xz", "--decompress", "$ARCHIVE_PATH"]`

We then need to map the partitions to match the ones defined in the raspios image, to do this:
- download the image and extract it
- run `fdisk -lu disk.img`
- create the partitions blocks and set the starting blocks and size accordingly

In my case, I ended up with this:
```
image_partitions {
    filesystem   = "vfat"
    mountpoint   = "/boot"
    name         = "boot"
    size         = "512M"
    start_sector = "16384"
    type         = "c"
  }
  image_partitions {
    filesystem   = "ext4"
    mountpoint   = "/"
    name         = "root"
    size         = "0"
    start_sector = "1064960"
    type         = "83"
  }
```

Since the installation of the base system is already done, we just need to run our install script and add our ssh keys.

In the install script, there are sections that are specific to RPis (activated with `TARGET_PLATFORM=rpi`), we'll get to them in the next sections.

For now, the only ones worth mentionning are:
  - `systemctl disable userconfig.service` that is used to disable the userconfig service since we don't want any additional configuration happening after the creation of the image by packer.
  - `K3S_EXEC="agent --node-taint droso/target-type=lowpower:NoSchedule"` that is used to apply a taint on k3s nodes running on a raspberry pi. This is done in order to prevent scheduling by default, so that the little rpi only runs the containers that strictly requires running on it.

#### Installation Script

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/builder/install.sh" >}}

This is a simple script to do the initial installation of packages and configuration for all build images.

The config options are the following:
<br/>

`INSTALL_CLOUD_INIT`: if set to true, will install and configure the cloud-init packages, in my case this is only used to build images for proxmox, so it will not be used here
<br/><br/>

`INSTALL_K3S` is used to install the K3S agent or server. 

If `K3S_URL` (the url to the master node) and `K3S_TOKEN` (the join token) are provided, the scripts configures k3s as an agent, else, it is configured as a server. 

If `TARGET_PLATFORM=rpi` is set, the taint cli arg will also be added: `--node-taint droso/target-type=lowpower:NoSchedule`.

We also increase the `fs.inotify` limits by writing a config file in `/etc/sysctl.d/10-ionotify.conf` since the defaults are not sufficient when running a lot of containers.
<br/><br/>

`INSTALL_DYNHOSTNAME` is used to add a script to set the hostname of the device at boot. 

The script is executed as a `network-pre.target` systemd service, it lists the ethernet network interfaces and uses a short form of the mac address of the first insterface as the hostname. 

This is required as k8s requires a unique hostname for each node (but our images are generic and used by multiple nodes).
<br/><br/>

`INSTALL_ISCSI` is used to install the ISCSI 


### Configuring the iSCSI server

#### Server

#### Data Upload

### Configuring the TFTP server

#### For amd64 devices

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/builder/Dockerfile" >}}

#### For Raspberry PIs

### Configuring the DHCP server

### For amd64 devices

#### For Raspberry PIs

While I didn't ended up using it for this project, I still wanted to connect an RPI to my cluster, here I will be using a RPI 3.

## Compiling libfreenect2

## Cluster configuration

## Final Configuration

## Bonus: Easily lifting the bed

## Conclusion

