
source "cross" "rpi_arm64" {
  file_checksum_type    = "sha256"
  file_checksum_url     = "https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2025-12-04/2025-12-04-raspios-trixie-arm64-lite.img.xz.sha256"
  file_target_extension = "xz"
  file_unarchive_cmd    = ["xz", "--decompress", "$ARCHIVE_PATH"]
  file_urls             = ["https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2025-12-04/2025-12-04-raspios-trixie-arm64-lite.img.xz"]
  image_build_method    = "reuse"
  image_chroot_env      = ["PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"]
  // use fdisk -lu disk.img to find partition info
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
  image_path                   = "output/rpi_arm64.img"
  image_size                   = "5G"
  image_type                   = "dos"
  qemu_binary_destination_path = "/usr/bin/qemu-aarch64-static"
  qemu_binary_source_path      = "/usr/bin/qemu-aarch64-static"
}

build {
  name = "rpi3_image"
  sources = ["source.cross.rpi_arm64"]

  # Run our install script
  provisioner "shell" {
    script = "./scripts/install.sh"
    environment_vars = [
      "K3S_VERSION=${var.k3s_version}",
      "K3S_TOKEN=${var.k3s_token}",
      "K3S_URL=${var.k3s_url}",
      "INSTALL_K3S=true",
      "INSTALL_ISCSI=true",
      "INSTALL_DYNHOSTNAME=true",
      "TARGET_PLATFORM=rpi",
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
