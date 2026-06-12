#!/bin/bash

set -e

# configure locale to en_US.UTF-8
export DEBIAN_FRONTEND=noninteractive
export LC_CTYPE=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# install basic utils
echo "Installing basic utilities"
apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends sudo nano curl wget htop ncdu nfs-common iptables

# install k3s agent
if [ "$INSTALL_K3S" == "true" ]; then
    echo "Installing k3s: $K3S_VERSION"
    wget https://get.k3s.io -O /root/get-k3s.sh
    chmod +x /root/get-k3s.sh

    if [ -z "$K3S_URL" ] || [ -z "$K3S_TOKEN" ]; then
        INSTALL_K3S_SKIP_ENABLE=true INSTALL_K3S_VERSION=$K3S_VERSION /root/get-k3s.sh
    else
        INSTALL_K3S_SKIP_START=true K3S_URL="$K3S_URL" K3S_TOKEN="$K3S_TOKEN" INSTALL_K3S_VERSION=$K3S_VERSION /root/get-k3s.sh
    fi
    sysctl -w fs.inotify.max_user_watches=2099999999
    sysctl -w fs.inotify.max_user_instances=2099999999
    sysctl -w fs.inotify.max_queued_events=2099999999
fi

if [ "$INSTALL_ISCSI" == "true" ]; then
    # install open-iscsi and rebuild initramfs
    echo "Installing iSCSI initiator"
    apt-get install -y open-iscsi initramfs-tools

    touch /etc/iscsi/iscsi.initramfs

    if [ "$TARGET_PLATFORM" == "rpi" ]; then
        kernel_version=$(dd if=/boot/kernel8.img 2>/dev/null | gunzip | strings | grep "Linux version" | awk '{print $3}' | head -n 1)
        echo "Detected kernel version: $kernel_version"
        echo "CONFIG_RD_ZSTD=y" > /boot/config-$kernel_version
        mkinitramfs -o /boot/initramfs8 $kernel_version
    else
        update-initramfs -u
    fi
fi

if [ "$INSTALL_DYNHOSTNAME" == "true" ]; then
    echo "Installing dynamic hostname service"
    script_data="$(cat <<-EOF
#!/bin/bash
set -e  
# Find the first active network interface (excluding loopback)
interface=\$(find /sys/class/net -mindepth 1 -maxdepth 1 -type l ! -name 'lo' -exec basename {} \; | head -n1)
echo "Using network interface: \$interface"
mac_addr=\$(cat /sys/class/net/\$interface/address 2>/dev/null || echo "00:00:00:00:00:00")
short_mac=\$(echo \$mac_addr | tr -d ':' | cut -c7-12)
new_hostname="k3s-\$short_mac"
echo "Setting new hostname to \$new_hostname"
echo "\$new_hostname" > /etc/hostname
hostname "\$new_hostname"
EOF
)"
    echo "$script_data" > /usr/local/bin/dynhostname
    chmod +x /usr/local/bin/dynhostname

    service_data="$(cat <<-EOF
[Unit]
Description=Set dynamic hostname based on MAC address
Wants=network-pre.target
Before=network-pre.target

[Service]
ExecStart=/usr/local/bin/dynhostname
Type=oneshot

[Install]
WantedBy=multi-user.target
EOF
)"
    echo "$service_data" > /etc/systemd/system/dynhostname.service
    systemctl enable dynhostname.service
fi

if [ "$INSTALL_CLOUD_INIT" == "true" ]; then
    echo "Configuring cloud-init"
    apt-get install -y --no-install-recommends cloud-init cloud-guest-utils cloud-utils
fi

if [ "$TARGET_PLATFORM" == "rpi" ]; then
    echo "Configuring Raspberry Pi specific settings"
    systemctl disable userconfig.service
fi

# configure networking
if [ "$TARGET_PLATFORM" != "rpi" ]; then
    echo "Configuring networking"
    apt-get install -y --no-install-recommends netplan.io systemd-resolved libnss-resolve libnss-myhostname systemd-timesyncd
    apt-get remove -y --purge ifupdown
    rm -rf /etc/network/interfaces.d
    systemctl enable systemd-networkd.service
    systemctl enable systemd-resolved.service
fi

if [ "$INSTALL_CLOUD_INIT" == "true" ]; then
    rm -rf /etc/netplan/* # cloud-init will handle netplan configs, so remove any existing files
fi

echo "Installation complete"
