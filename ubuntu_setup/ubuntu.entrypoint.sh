#!/bin/bash

# Set the SSH username and password using environment variables
SSH_USERNAME=${SSH_USERNAME:-"ubuntu"}  # Default username is "ubuntu"
SSH_PASSWORD=${SSH_PASSWORD:-""}        # Default password is empty

if [ -n "$SSH_USERNAME" ]; then
    echo "Adding new user $SSH_USERNAME..."
    useradd -m -d /home/$SSH_USERNAME -s /bin/bash $SSH_USERNAME

    if [ -n "$SSH_PASSWORD" ]; then
        echo "Setting SSH password..."
        echo "$SSH_USERNAME:$SSH_PASSWORD" | chpasswd
    fi

    # Add the user to the 'sudo' group to grant root privileges
    echo "Adding sudo privileges"
    usermod -aG sudo $SSH_USERNAME
fi

# Start SSH server
/usr/sbin/sshd -D
