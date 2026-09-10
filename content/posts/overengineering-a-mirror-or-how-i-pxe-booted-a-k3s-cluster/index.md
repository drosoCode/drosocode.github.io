---
title: "Overengineering a mirror or how I PXE-booted a k3s cluster - Part 1"
date: 2026-02-14T00:00:00+00:00
draft: true
tags:
- hardware
- infra
- k8s
---

From the last years, I started to gain interest in another new hobby: dancing. Naturally, I would like to practice at home. The ideal environment would be a large empty room with a full size mirror on the wall, but I live in Paris so the rent is very expensive and thus I do not have this kind of space, actually I do not even have any free wall without any furniture where I could place a mirror. 

So, there was two problems: getting enough empty space to move, and getting some kind of visual feedback.

The free space problem can be solved quite easily by lifting my bed against the wall (see the bonus at the end of this series). But for the mirror, I wanted to take advantage of my existing infrastructure and software development background.

This is the first part of a series of 3 posts:
- Part 1: Network Booting
- [Part 2: Kinect Setup]()
- [Part 3: K8s Deployment]()

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
- Then, when booting, the device will send a DHCP request (DHCPDISCOVER), with additional fields and options for PXE
- The DHCP server then responds with the proposed IP-address (DHCPOFFER) and additional PXE parameters
- The client accepts the DHCP offer (DHCPREQUEST + DHCPACK), fetches the Bootfile on the specified TFTP server and loads it
- For Linux (the only case exposed here), the kernel and initramfs will be fetched from the TFTP server by the bootfile and then be loaded
- Then, the iSCSI drive will be mounted as the root path and the system will finish starting up


{{< admonition type=warning title="Warning" open=true >}}
Only the Raspberry PI models >= 3B can be used to boot from the network.
{{< /admonition >}}

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

`INSTALL_ISCSI` is used to install the ISCSI initiator. This is the most important part as this is the software used at startup to mount the ISCSI share at the root of filesystem (effectively, replacing the need for a local drive). Here, we'll be using `open-iscsi`.

The debian package supports [booting on an ISCSI drive](https://sources.debian.org/src/open-iscsi/2.0.874-7.1/debian/README.Debian/#L68), to enable it we need to create a `/etc/iscsi/iscsi.initramfs` file. Options such as the initiator iqn can be set in this file, but to keep this image generic, we'll use the second option which is to provide these option directly as cmdline when booting.

We then need to rebuild the initramfs:
- On the x64 version, is as easy as running `update-initramfs -u`
- On the raspberry version, this doesn't work (at least in the packer builder), so we need to manually find the kernel version with this *beautiful* command `kernel_version=$(dd if=/boot/kernel8.img 2>/dev/null | gunzip | strings | grep "Linux version" | awk '{print $3}' | head -n 1)` and run `mkinitramfs -o /boot/initramfs8 $kernel_version`.

### Configuring the iSCSI server

Now that we have build generic disk images for both raspberry and x64 devices, we need to configure the ISCSI server to serve these images.

There are [multiple implementations](https://wiki.debian.org/SAN/iSCSI/) of iscsi servers (also called `targets`) available on linux. Here, we'll be using the in-kernel implementation. To manage its configuration, we'll need to install `targetcli-fb`.

First, we need to create the LUNs which are the actual storage spaces. You can of couse use block devices (such as physical disks or partitions), but here what's really interesting is the `fileio` backstore that enables you to use a disk image file as a storage medium.

I created two LUNs, one for my raspberry of 32gb at the path `/srv/iscsi/nvme1/pxe/rpi3b.img` and one for my dell micro-pc of 64gb at `/srv/iscsi/nvme1/pxe/srvdell.img` (I allocated more space to the dell pc because since it way more powerful than the raspberry, it will receive more pods and thus require more storage for the container images).

The disk images don't actually need to exist yet, just ensure that the size that you define in the backstore corresponds to the actual size that you want your img file to be (for example if you have a disk image of 64gb but the backstore is only defined for 32gb, only the 32gb will be accessible when mounting the drive over iscsi).

You can now define the portal and targets:

First, ensure that you have at least one portal configured and that it listens on the correct IP/Port for our initators to connect to.

An ISCSI target is defined by its `iqn`, this is a unique identifier that we can use to assing ACLs to access our LUNs, the iqn should be formatted as follows: `iqn.yyyy-mm.domain:name` with "yyyy-mm" the date of acquisition of the domain, "domain" the reverse domain name, and "name" any unique name. For example, I'm using the following iqn format: `iqn.2023-06.tld.mydomain.pxe:macaddress_of_the_device`.

For each device, create an iqn and associate a new acl to this iqn. The ACL contains the username and password used to mount the iscsi share, and the mapped_lun indicates the physical storage that this iqn can access (here, just add one LUN created previously to each iqn).

Here is an example output of `targetcli ls` after finishing the configuration:
```
/> ls
o- / ............................................................................................................. [...]
  o- backstores .................................................................................................. [...]
  | o- fileio ..................................................................................... [Storage Objects: 2]
  | | o- lun_rpi3b ..................................... [/srv/iscsi/nvme1/pxe/rpi3b.img (32.0GiB) write-back activated]
  | | | o- alua ....................................................................................... [ALUA Groups: 1]
  | | |   o- default_tg_pt_gp ........................................................... [ALUA state: Active/optimized]
  | | o- lun_srv_dell ................................ [/srv/iscsi/nvme1/pxe/srvdell.img (64.0GiB) write-back activated]
  | |   o- alua ....................................................................................... [ALUA Groups: 1]
  | |     o- default_tg_pt_gp ........................................................... [ALUA state: Active/optimized]
  | o- pscsi ...................................................................................... [Storage Objects: 0]
  | o- ramdisk .................................................................................... [Storage Objects: 0]
  o- iscsi ................................................................................................ [Targets: 2]
  | o- iqn.2023-06.tld.mydomain.myserver:nvme1.pxe ........................................................... [TPGs: 1]
  |   o- tpg1 ................................................................................... [no-gen-acls, no-auth]
  |     o- acls .............................................................................................. [ACLs: 2]
  |     | o- iqn.2023-06.tld.mydomain.pxe:aa-aa-aa-aa-aa-aa ........................................... [Mapped LUNs: 1]
  |     | | o- mapped_lun0 ................................................................ [lun1 fileio/lun_rpi3b (rw)]
  |     | o- iqn.2023-06.tld.mydomain.pxe:bb-bb-bb-bb-bb-bb ........................................... [Mapped LUNs: 1]
  |     |   o- mapped_lun0 ............................................................. [lun0 fileio/lun_srv_dell (rw)]
  |     o- luns .............................................................................................. [LUNs: 2]
  |     | o- lun0 .......................... [fileio/lun_srv_dell (/srv/iscsi/nvme1/pxe/srvdell.img) (default_tg_pt_gp)]
  |     | o- lun1 ............................... [fileio/lun_rpi3b (/srv/iscsi/nvme1/pxe/rpi3b.img) (default_tg_pt_gp)]
  |     o- portals ........................................................................................ [Portals: 1]
  |       o- 0.0.0.0:3260 ......................................................................................... [OK]
  o- loopback ............................................................................................. [Targets: 0]
  o- srpt ................................................................................................. [Targets: 0]
  o- vhost ................................................................................................ [Targets: 0]
  o- xen-pvscsi ........................................................................................... [Targets: 0]
/>
```

To make things easier, instead of configuring everything manually, I'm using Ansible and a `pxe.yaml` configuration file to define my options for each device.

I was using the [ricsanfre/ansible-role-iscsi_target](https://github.com/ricsanfre/ansible-role-iscsi_target) role, but ended up forking it here: [ drosoCode/ansible-role-iscsi_target](https://github.com/drosoCode/ansible-role-iscsi_target) to add missing configuration option (especially regarding the fileio storage size). To use the forked version, add this in your ansible's `requirements.yaml`:

```yaml
roles:
  - name: ricsanfre.iscsi_target
    src: https://github.com/drosoCode/ansible-role-iscsi_target
    version: master
```

You can find the playbook and pxe config below.

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/infra/setup-iscsi-target.yaml" >}}

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/infra/pxe.yaml" >}}

### Extracting and customizing the images

To customize our disk images and upload them to the right location, we'll continue to use the `pxe.yaml` config file created above to centralize the pxe configuration (since there are many moving parts).

*But why do we need to "customize" the images ?*

At this point, we've built a generic disk image for amd64 and RPI devices. But to actually make them boot we need to tell the BIOS how to boot these disk images and how to mount the root partition. To do this, we need to extract some files from the build images and customize them.

We'll be using the following python script to automate these steps:

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/infra/pxe.py" >}}

Note that for this step, you will have to already have configured an iSCSI target (previous step) and a TFTP server (a tftp package is often installable on good routers).

**TFTP** is the protocol used by the PXE firmware to fetch the files to boot, the TFTP server url and the actual path to the bootfile are configured using DHCP options (we'll see this in the next step).

#### For amd64 devices

The legacy "PXE" booting doesn't allows to directly boot from a disk image on an iSCSI server, so we'll first need to boot into a more featureful bootloader such as [iPXE](https://ipxe.org/). This is called [chainloading](https://ipxe.org/howto/chainloading), depending on your network card firmware you may not need to do this (since some of them already supports iPXE out of the box).

iPXE then allows you to write [scripts](https://ipxe.org/scripting) to control the boot process.

There are two ways to use these scripts: 
- You can pass the URL of the script to iPXE directly and it will fetch and execute it at runtime (ex `http://192.168.0.1/boot.php?mac=${net0/mac}&asset=${asset:uristring}`)
- Or you can embed the script directly in the iPXE binary

I've selected the second option (since it's required anyways to build iPXE if you want the chainloadable PXE binary), but I strongly suggest you to use the first method if your network card firmware already supports iPXE.

In theory, you can use the [sanboot](https://ipxe.org/cmd/sanboot) command to directly boot from an iSCSI disk, but I haven't been able to make it work, so we'll use a little workaround:
- We'll extract the kernel and initrd from our generic amd64 disk image and upload them to the TFTP server (along with the iPXE binary)
- The legacy-PXE will boot the iPXE binary fetched from the TFTP server (the bootfile is specified in the dhcp responses)
- Once loaded, the iPXE binary will fetch the kernel (and initrd) from the TFTP server and start it
- The kernel will start the iscsi initiator (`open-iscsi` installed in the previous steps) and this initiator will use some arguments in the kernel cmdline to mount the iSCSI disk as the root partition

The required kernel cmdline args for `open-iscsi` are:
- `ISCSI_INITIATOR`: the IQN to use for this device, with iPXE we can use the `${mac:hexhyp}` substitution to use the mac address of the network card used to boot. (ex: `iqn.2023-06.tld.domain.pxe:${mac:hexhyp}`)
- `ISCSI_TARGET_NAME`: the IQN of the iSCSI target (ex `iqn.2023-06.tld.domain.storage_server_name:nvme1.pxe`)
- `ISCSI_TARGET_IP`: the IP address of the iSCSI target
- `ISCSI_TARGET_PORT`: the port of the iSCSI target
- `ISCSI_AUTHMETHOD=CHAP`: to use secure authentication
- `ISCSI_USER`: the username to use with the iSCSI target
- `ISCSI_PW`: the password to use with the iSCSI target

Out of all these parameters, the `ISCSI_INITIATOR` is the only one that changes dynamically (depending on the mac address of the machine that is booting).

Now here's what our iPXE script looks like:
```
#!ipxe
dhcp
kernel k3s/vmlinuz root=/dev/sda2 ro quiet ip=dhcp ISCSI_INITIATOR=iqn.2023-06.tld.domain.pxe:${mac:hexhyp} ISCSI_TARGET_NAME=iqn.2023-06.tld.domain.storage_server_name:nvme1.pxe ISCSI_TARGET_IP=10.10.2.1 ISCSI_TARGET_PORT=3260 ISCSI_AUTHMETHOD=CHAP ISCSI_USER=user ISCSI_PW=password
initrd k3s/initrd.img
boot
```
\* `k3s/` is the directory that I'm using in the TFTP server to store the kernel and initrd

Then to build iPXE, we'll use a docker container:

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/builder/Dockerfile" >}}

- Name your script `boot.ipxe`
- Build the container with: `docker build -t ipxe_builder .`
- Create the iPXE binary with: `docker run -it --rm -v ./path/to/ipxe_script_dir:/data ipxe_builder`

We now need to extract the kernel and initrd from our disk image.

In linux, it's pretty easy: all we need to do is mount the image and copy the right files
- Create some folder to mount your disk to `mkdir /mnt/mountpoint`
- Add a loopback device pointing to your disk image `losetup -f --show -P /path/to/disk.img`
- Note the displayed path of your loopback device (ex: `/dev/loop0`)
- Mount the partition `mount /dev/loop0p2 /mnt/mountpoint`: in this case `p2` means we're mounting the second partition (this is the root partition, the first one being the EFI partition)
- Copy the kernel `cp /mnt/mountpoint/vmlinuz /some/backup/path/`
- Copy the initrd `cp /mnt/mountpoint/initrd.img /some/backup/path/` 
- Unmount the partition `umount /mnt/mountpoint`
- Remove the loopback device `losetup -d /dev/loop0`

Now, copy the kernel, initrd and iPXE files to the TFTP server.

#### For Raspberry PIs

On the Rapsberry PI, the boot process is a bit different: the firwmare directly expects a predetermined file structure on the tftp server and will try to load only this one (see [here](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#network-booting)).

This part is largely inspired from the [blog post from warmestrobot](https://warmestrobot.com/blog/2024/06/27/raspberry-pi-network-boot-guide-2/), please check it out for more details on the differences between the RPi versions.

First, you need to boot from the sdcard (use any distribution as long as you have access to a terminal). Once connected to the PI:
- Run `vcgencmd otp_dump | grep 17`, if the result is not `1020000a`, edit `/boot/config.txt` and set `program_usb_boot_mode=1` to enable the correct boot mode, reboot and verify the result
- Find the RPi serial number with `grep Serial /proc/cpuinfo` (ignore the preceding zeros)
- Find the RPi eth0 mac address with `ip a`
- That's it for the on-device part

{{< admonition type=warning title="Warning" open=true >}}
If you're using the RPi model 3B, you need to format a SD Card to FAT32, place the `bootcode.bin` (extracted from the image, see below) at the root and put (and keep it all the time) the SD Card in the RPi to work around some hardcoded bugs in the network boot.
{{< /admonition >}}

Now, let's extract the boot files from our build image:
- Create some folder to mount your disk to `mkdir /mnt/mountpoint`
- Add a loopback device pointing to your disk image `losetup -f --show -P /path/to/disk.img`
- Note the displayed path of your loopback device (ex: `/dev/loop0`)
- Mount the partition `mount /dev/loop0p1 /mnt/mountpoint`: in this case `p1` means we're mounting the first partition
- Copy the boot files `rsync -avhP /mnt/mountpoint/boot/ /some/backup/dir`
- Unmount the partition `umount /mnt/mountpoint`
- Remove the loopback device `losetup -d /dev/loop0`


In the bootfiles destination folder (here `/some/backup/dir`), you will find a `cmdline.txt` file, edit it to look like this:
- `console=serial0,115200 console=tty1 ip=dhcp root=/dev/sda2 rootfstype=ext4 elevator=deadline cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory rootwait rw ISCSI_INITIATOR=iqn.2023-06.tld.domain.pxe:bb-bb-bb-bb-bb-bb ISCSI_TARGET_NAME=iqn.2023-06.tld.domain.storage_server_name:nvme1.pxe ISCSI_TARGET_IP=10.10.2.1 ISCSI_TARGET_PORT=3260 ISCSI_AUTHMETHOD=CHAP ISCSI_USER=user ISCSI_PW=password`

Customize the `ISCSI_*` parameters according the their description (see the `amd64` section above). The only difference is that here, we need to specify the exact initiator value (so `${mac:hexhyp}` can't be used, we need to set a real unique value, here I'm still using the RPi mac address, but this config is now specific to each RPi device, this isn't really a problem since the RPi will look for this file in a folder named after their serial number anyways).

Still in the same folder, edit the `config.txt` file and add at the end of the file:
- `kernel=kernel8.img`
- `initramfs initramfs8 followkernel`

{{< admonition type=info title="Notice" open=true >}}
If using a RPi model 5, instead of `kernel8` and `initramfs8`, use `kernel2712` and `initramfs2712`
{{< /admonition >}}

Now copy rename your bootfiles destination folder to the serial number of the RPi and copy this folder to your TFTP server.

In this folder, you will also find the `bootcode.bin`, make sure to also copy this file to the root of the TFTP server as most RPi models will search for it at the root of the TFTP server.


### Resizing and uploading the images

The TFTP server layout should now look like this (if using both RPi and amd64):
```
| / 
|   /k3s
|     /k3s/vmlinuz
|     /k3s/initrd.img
|     /k3s/ipxe.efi
|   /bootcode.bin
|   /aabbccdd (<-- this is the RPi serial number)
|     /aabbccdd/config.txt
|     /aabbccdd/cmdline.txt
|     /aabbccdd/bootcode.bin
|     /aabbccdd/kernel8.img
|     /aabbccdd/initramfs8
|     /aabbccdd/<and a bunch of .dtb,.dat,.elf files ...>
```

Now the last step for storage is uploading the disk images to the iSCSI server.

The generic image that we have generated have a quite small disk size to be easier to manipulate, but we may want to resize them to be larger (especially when running a lot of containeres, k3s will use quite a lot of space), so let's do this:


{{< admonition type=warning title="Warning" open=true >}}
The following process is only possible because the DATA partition (the one we want to expand) is the LAST partition. If you have followed this entire tutorial it should be fine, but for example if you've enabled the SWAP on debian, usually the SWAP partition is located *after* the DATA one, in that case, we can't expand the DATA part *this easily* since it's stuck between the EFI and SWAP partitions.
{{< /admonition >}}

- Create sparse data at the end of your disk image: `dd if=/dev/zero of=/path/to/disk.img bs=1M count=0 seek=SIZE` (replace SIZE by the actual size in megabytes, ex: `32768` for 32gb, it should be greater than the current image size)
- Create a loopback device for the image: `losetup -f --show -P /path/to/disk.img`
- Note the displayed path of your loopback device (ex: `/dev/loop0`)
- Run: `parted /dev/loop0 --script print` and check if the output contains `gpt`
  - If yes, move the gpt backup header to the end of the disk with `sgdisk -e /dev/loop0`
- Now resize the data partition (here partition 2) to completely fill the end of the disk: `parted /dev/loop0 --script resizepart 2 100%`
- And resize the filesystem with (still partition 2 here):
  - `fsck -f /dev/loop0p2`
  - `resize2fs /dev/loop0p2`
  - `fsck -f /dev/loop0p2`
- Finally, remove the loopback device `losetup -d /dev/loop0`

Now to upload the image to the server, we can use `rsync` with the `--sparse --inplace` options, this will ensure that rsync will only copy the actual data (and not the zeroed free space that we added) thus ensuring a much faster transfer speed.

I've created an ansible playbook to automate the task of uploading data to both the TFTP server and iSCSI server:

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/assets/infra/upload.yaml" >}}

### Configuring the DHCP server

You're almost there ! 

The last step is now to configure your DHCP server to tell our devices where to find their bootfiles on the TFTP server.

The client usually sends the following information with their DHCPDISCOVER and DHCREQUEST requests:
-  Vendor-Class Identifier (Option 60): the vendor class identifier
    - "PXEClient:Arch:00000" for the Raspberry PI (but not limited to it)
    - "PXEClient:Arch:00007" for UEFI x64 firmwares
- .... for iPXE

The following options/fields are expected in the DHCPOFFER and DHCPACK responses to make the network boot work:
  - TFTP Server Name (Option 66): the IP of the TFTP server that will be used to load the bootfile (used by both RPi and amd64)
  - Bootfile Name (Option 67): the path (on the TFTP server) of the boot file to fetch and load (only used for the amd64 boot)
  - Next-Server: (or `siaddr`) a field in the DHCP packet. For iPXE, we will also need to set the it to the IP of the TFTP server to use to load the kernel/initramfs (so only required for amd64 boot)
  - Vendor-specific Information (Option 43): set to "Raspberry Pi Boot" (only required for the RPi boot)

On dnsmasq, you can add rules like this (not the actual syntax) to limit the reach of these options:
- if "vendor-class id == PXEClient:Arch:00007" set "bootfile_name = k3s/ipxe.efi"
- if "client mac_address == xxxxxxxx" set "vendor-specific info = Raspberry Pi Boot"

On OPNsense, you can configure this in `Services > Dnsmasq DNS & DHCP > DHCP Options`. If you don't have any other devices that requires Vendor-specific Information, it's also fine to leave everything set all the time. 

{{< admonition type=info title="Notice" open=true >}}
For more info on DHCP (especially the fields and options), see the [RFC2131](https://www.rfc-editor.org/rfc/rfc2131) and [RFC2132](https://www.rfc-editor.org/rfc/rfc2132).
{{< /admonition >}}



## Overview

### amd64 Boot

{{< mermaid >}}
sequenceDiagram
    actor User
    User->>+BIOS: Start
    BIOS->>+DHCP_SRV: DHCPDISCOVER
    DHCP_SRV-->>-BIOS: DHCPOFFER
    BIOS->>+DHCP_SRV: DHCPREQUEST
    DHCP_SRV-->>-BIOS: DHCPACK
    BIOS->>+TFTP_SRV: Fetch PXE bootfile (option 67) from TFTP Server (option 66)
    TFTP_SRV-->>-BIOS: bootfile (ipxe.efi)
    BIOS->>+PXE_IMAGE: Execute bootfile
    PXE_IMAGE->>+DHCP_SRV: DHCPDISCOVER
    DHCP_SRV-->>-PXE_IMAGE: DHCPOFFER
    PXE_IMAGE->>+DHCP_SRV: DHCPREQUEST
    DHCP_SRV-->>-PXE_IMAGE: DHCPACK
    PXE_IMAGE->>+TFTP_SRV: Fetch kernel from TFTP Server (next-server field)
    TFTP_SRV-->>-PXE_IMAGE: kernel
    PXE_IMAGE->>+TFTP_SRV: Fetch initrd from TFTP Server
    TFTP_SRV-->>-PXE_IMAGE: initrd
    PXE_IMAGE->>+KERNEL: Boot kernel with initrd
    KERNEL->>+DHCP_SRV: DHCPDISCOVER
    DHCP_SRV-->>-KERNEL: DHCPOFFER
    KERNEL->>+DHCP_SRV: DHCPREQUEST
    DHCP_SRV-->>-KERNEL: DHCPACK
    KERNEL->>+ISCSI_TARGET: Mount root partition
    ISCSI_TARGET->>+DISK_IMG: R/W
    DISK_IMG-->>-ISCSI_TARGET: 
    ISCSI_TARGET-->>-KERNEL: 
    KERNEL-->-User: Started
{{< /mermaid >}}

### RPi Boot



### Conclustion


## References

- https://sources.debian.org/src/open-iscsi/2.0.874-7.1/debian/README.Debian/
- https://linuxhit.com/build-a-raspberry-pi-image-packer-packer-builder-arm/
- https://developer.hashicorp.com/packer/docs/builders/community-supported
- https://warmestrobot.com/blog/2024/06/27/raspberry-pi-network-boot-guide-2/
- https://vwannabe.com/2024/01/11/cloning-linux-a-step-by-step-guide-to-booting-from-iscsi-lun/
- https://forum.level1techs.com/t/gnu-linux-installation-server-ipxe-menu-sanboot/186919
- https://romain.therrat.fr/posts/2011/04/iscsi-installation-dun-serveur-iscsi-sous-debian-et-connexion-dun-client/
- https://wiki.debian.org/SAN/iSCSI/LIO
- https://manpages.ubuntu.com/manpages/jammy/man8/targetctl.8.html
- https://ipxe.org/cmd/kernel
- https://ipxe.org/embed
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#network-booting
- https://kb.isc.org/docs/standard-dhcp-options
- https://www.rfc-editor.org/rfc/rfc2132
