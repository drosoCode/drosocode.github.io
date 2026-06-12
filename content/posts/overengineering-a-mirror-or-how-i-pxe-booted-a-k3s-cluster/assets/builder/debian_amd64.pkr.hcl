
source "qemu" "amd64_uefi" {
  iso_url           = var.iso_url
  iso_checksum      = var.iso_checksum
  output_directory  = "output/qemu_amd64_uefi"
  
  shutdown_command = "poweroff"
  disk_size         = "5G"
  memory            = "4096"
  cpus              = 4
  machine_type    = "q35"
  format            = "raw"
  accelerator       = "kvm"

  vm_name = "debian"
  efi_boot         = true
  efi_firmware_code = "/usr/share/edk2/x64/OVMF_CODE.4m.fd"
  efi_firmware_vars = "/usr/share/edk2/x64/OVMF_VARS.4m.fd"
  //headless = true

  ssh_username      = "root"
  ssh_password      = "packer"
  ssh_timeout       = "20m"

  // see: https://developer.hashicorp.com/packer/guides/automatic-operating-system-installs/preseed_ubuntu
  http_directory = "http"
  http_port_min  = 8100
  http_port_max  = 8100

  boot_wait         = "5s"
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
}

build {
  name = "debian_image"

  sources = ["source.qemu.amd64_uefi"]

  # Run our install script
  provisioner "shell" {
    script = "./scripts/install.sh"
    environment_vars = [
      "K3S_VERSION=${var.k3s_version}",
      "K3S_TOKEN=${var.k3s_token}",
      "K3S_URL=${var.k3s_url}",
      "INSTALL_K3S=true",
      "INSTALL_ISCSI=true",
      "INSTALL_DYNHOSTNAME=true"
    ]
  }

  provisioner "file" {
    content = join("\n", var.authorized_keys)
    destination = "/root/.ssh/authorized_keys"
  }

  provisioner "shell" {
    # make login public key only
    inline = [
      "chmod 600 /root/.ssh/authorized_keys",
      "sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config",
      "sed -i 's/^PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config",
    ]
  }
}
