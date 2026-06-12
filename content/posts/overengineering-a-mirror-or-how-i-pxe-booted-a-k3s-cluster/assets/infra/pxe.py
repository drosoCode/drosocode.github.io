#!python3

import shutil
import yaml
import os
import subprocess

MOUNT_POINT = "/mnt/packer_data_tmp"

def mount_image(src_img_path, partition):
    if not os.path.exists(MOUNT_POINT):
        os.makedirs(MOUNT_POINT)
    
    loop_dev = subprocess.run(["losetup", "-f", "--show", "-P", src_img_path], stdout=subprocess.PIPE, check=True)
    loop_dev_path = loop_dev.stdout.decode().strip()
    subprocess.run(["mount", f"{loop_dev_path}p{partition}", MOUNT_POINT], check=True)
    return loop_dev_path

def unmount_image(loop_dev_path):
    subprocess.run(["umount", MOUNT_POINT], check=True)
    subprocess.run(["losetup", "-d", loop_dev_path], check=True)

def expand_image(img_path, size_mb):
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Image not found: {img_path}")
    if not os.path.isfile(img_path):
        raise ValueError(f"Image is not a file: {img_path}")

    # Create a sparse file of the desired size
    subprocess.run(["dd", "if=/dev/zero", f"of={img_path}", "bs=1M", "count=0", f"seek={size_mb}"], check=True)
    
    loop_dev = subprocess.run(["losetup", "-f", "--show", "-P", img_path], stdout=subprocess.PIPE, check=True)
    loop_dev_path = loop_dev.stdout.decode().strip()

    # Move GPT backup header to end of disk if required
    parted_output = subprocess.run(["parted", loop_dev_path, "--script", "print"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    is_gpt = "gpt" in parted_output.stdout.decode().lower()
    if is_gpt:
        subprocess.run(["sgdisk", "-e", loop_dev_path], check=True)

    # Resize partition 2 to fill the disk
    subprocess.run(["parted", loop_dev_path, "--script", "resizepart 2 100%"], check=True)

    # Resize filesystem on partition 2
    subprocess.run(["fsck", "-f", f"{loop_dev_path}p2"], check=True)
    subprocess.run(["resize2fs", f"{loop_dev_path}p2"], check=True)
    subprocess.run(["fsck", "-f", f"{loop_dev_path}p2"], check=True)

    subprocess.run(["losetup", "-d", loop_dev_path], check=True)



class PXEDispatcher:
    def __init__(self, config_path, src_img_path, output_path):
        self.script_root = os.getcwd()
        self.src_img_path = src_img_path

        self.tftp_dir = os.path.join(output_path, "tftp")
        self.iscsi_dir = os.path.join(output_path, "iscsi")

        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.makedirs(self.tftp_dir)
        os.makedirs(self.iscsi_dir)

        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)

        self.target_iscsi_args = f"ISCSI_TARGET_NAME={self.cfg['iscsi_target']['iqn']} ISCSI_TARGET_IP={self.cfg['iscsi_target']['ip']} ISCSI_TARGET_PORT={self.cfg['iscsi_target']['port']} ISCSI_AUTHMETHOD=CHAP ISCSI_USER={self.cfg['iscsi_target']['username']} ISCSI_PW={self.cfg['iscsi_target']['password']}"

        subprocess.run(["docker", "build", "-t", "ipxe_builder", "."], cwd=self.script_root, check=True)


    def build_ipxe_efi(self, tftp_dir, dst_path):
        tmp_dir = os.path.join(self.script_root, "tmp_ipxe_build")
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)

        tftp_dir = tftp_dir.strip("/")
        if tftp_dir != "":
            tftp_dir += "/"

        with open(os.path.join(tmp_dir, "boot.ipxe"), 'w') as f:
            f.write("#!ipxe\n")
            f.write("dhcp\n")
            f.write(f"kernel {tftp_dir}vmlinuz root=/dev/sda2 ro quiet ip=dhcp ISCSI_INITIATOR={self.cfg['ipxe']['iscsi_initiator_iqn']} {self.target_iscsi_args}\n")
            f.write(f"initrd {tftp_dir}initrd.img\n")
            f.write("boot\n")

        build_cmd = [
            "docker", "run", "-it", "--rm",
            "-v", f"{tmp_dir}:/data",
            "ipxe_builder"
        ]
        subprocess.run(build_cmd, check=True)

        shutil.move(os.path.join(tmp_dir, "ipxe.efi"), dst_path)
        shutil.rmtree(tmp_dir)



    def process_ipxe_config(self, boot_config, matching_pxe_entries):
        tftp_dir = os.path.join(self.tftp_dir, boot_config["tftp_dir"])
        os.makedirs(tftp_dir, exist_ok=True)

        src_img = os.path.join(self.src_img_path, boot_config["source_image_path"])
        if not os.path.exists(src_img):
            raise FileNotFoundError(f"Source image not found: {src_img}")

        # extract boot file from source image
        loopdev = mount_image(src_img, "2")
        shutil.copy(os.path.join(MOUNT_POINT, boot_config["initrd_path"]), os.path.join(tftp_dir, "initrd.img"))
        shutil.copy(os.path.join(MOUNT_POINT, boot_config["kernel_path"]), os.path.join(tftp_dir, "vmlinuz"))
        unmount_image(loopdev)

        # copy ipxe bootloader
        self.build_ipxe_efi(boot_config["tftp_dir"], os.path.join(tftp_dir, "ipxe.efi"))

        # add disk image for each initiator
        for pxe in matching_pxe_entries:
            dst = os.path.join(self.iscsi_dir, pxe["iscsi_target_path"])
            shutil.copy(src_img, dst)
            expand_image(dst, pxe["image_size_gb"] * 1024)


    def process_rpi_entry(self, pxe_entry):
        tftp_dir = os.path.join(self.tftp_dir, pxe_entry["serial_number"])
        os.makedirs(tftp_dir, exist_ok=True)

        src_img = os.path.join(self.src_img_path, pxe_entry["source_image_path"])
        if not os.path.exists(src_img):
            raise FileNotFoundError(f"Source image not found: {src_img}")

        # extract boot files from source image
        loopdev = mount_image(src_img, "1")
        subprocess.run(["rsync", "-avhP", f"{MOUNT_POINT}/", tftp_dir], check=True)
        unmount_image(loopdev)

        # copy bootcode.bin if missing
        bootcode_dst = os.path.join(self.tftp_dir, "bootcode.bin")
        if not os.path.exists(bootcode_dst):
            shutil.copy(os.path.join(tftp_dir, "bootcode.bin"), bootcode_dst)

        # patch cmdline.txt and config.txt
        # cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory are required for k3s
        cmdline = "console=serial0,115200 console=tty1 ip=dhcp root=/dev/sda2 rootfstype=ext4 elevator=deadline cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory rootwait rw "
        iscsi_params = f"ISCSI_INITIATOR={pxe_entry['iscsi_initiator_iqn']} {self.target_iscsi_args}"

        cmdline_path = os.path.join(tftp_dir, "cmdline.txt")
        with open(cmdline_path, 'w+') as f:
            f.write(cmdline + iscsi_params + "\n")

        # The 2712 suffix is for Raspberry Pi 5, while v8 is for all previous generations
        config_path = os.path.join(tftp_dir, "config.txt")
        with open(config_path, 'a') as f:
            f.write("\n")
            f.write("kernel=kernel8.img\n")
            f.write("initramfs initramfs8 followkernel\n")

        # add disk image for each initiator
        dst = os.path.join(self.iscsi_dir, pxe_entry["iscsi_target_path"])
        shutil.copy(src_img, dst)
        expand_image(dst, pxe_entry["image_size_gb"] * 1024)

    def run(self):
        matching_pxe_entries = {}

        for pxe_entry in self.cfg["pxe"]:
            if pxe_entry["boot_type"] == "rpi":
                self.process_rpi_entry(pxe_entry)
            elif pxe_entry["boot_type"] == "ipxe":
                matching_pxe_entries.setdefault(pxe_entry["ipxe_boot_config"], []).append(pxe_entry)
            else:
                raise ValueError(f"Unknown PXE boot_type: {pxe_entry['boot_type']}")
    
        for boot_config_name, entries in matching_pxe_entries.items():
            self.process_ipxe_config(self.cfg["ipxe"]["boot_config"][boot_config_name], entries)




if __name__ == "__main__":
    dispatcher = PXEDispatcher("../settings/pxe.yaml", "../packer/output", "./output")
    dispatcher.run()
