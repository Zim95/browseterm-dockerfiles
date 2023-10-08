#!/bin/bash

# Set the SSH password using an environment variable
if [ -n "$SSH_PASSWORD" ]; then
    echo "Adding new user ubuntu..."
    useradd -m -d /home/ubuntu -s /bin/bash ubuntu

    echo "Setting SSH password..."
    echo "ubuntu:$SSH_PASSWORD" | chpasswd

    # Add 'ubuntu' to the 'sudo' group to grant root privileges
    echo "Adding sudo privileges"
    usermod -aG sudo ubuntu
fi

# Start SSH server
/usr/sbin/sshd -D