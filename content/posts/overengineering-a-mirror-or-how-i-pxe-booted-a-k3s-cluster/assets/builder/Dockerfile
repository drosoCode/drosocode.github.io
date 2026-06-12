FROM debian:13-slim

RUN apt-get update && apt-get install -y build-essential git liblzma-dev && \
    git clone https://github.com/ipxe/ipxe.git /tmp/ipxe

CMD ["/bin/sh", "-c", "cd /tmp/ipxe/src && make bin-x86_64-efi/ipxe.efi EMBED=/data/boot.ipxe && cp /tmp/ipxe/src/bin-x86_64-efi/ipxe.efi /data/ipxe.efi"]

# warning: to load relative tftp paths (like boot/vmlinuz), the dhcp server MUST send "next-server ip" (the ip of the tftp server to use)
