#!/bin/bash

# Set the SSH username and password using environment variables
SSH_USERNAME=${SSH_USERNAME:-"ubuntu"}  # Default username is "ubuntu"
SSH_PASSWORD=${SSH_PASSWORD:-""}        # Default password is empty

if [ -n "$SSH_USERNAME" ]; then
    # Fresh containers have no such user; containers restored from a snapshot already do
    # (the account is captured in /etc/passwd), so only create it when it's missing.
    if id "$SSH_USERNAME" >/dev/null 2>&1; then
        echo "User $SSH_USERNAME already exists (restored container)"
    else
        echo "Adding new user $SSH_USERNAME..."
        useradd -m -d /home/$SSH_USERNAME -s /bin/bash $SSH_USERNAME
    fi

    if [ -n "$SSH_PASSWORD" ]; then
        echo "Setting SSH password..."
        echo "$SSH_USERNAME:$SSH_PASSWORD" | chpasswd
    fi

    # Add the user to the 'sudo' group to grant root privileges
    echo "Adding sudo privileges"
    usermod -aG sudo $SSH_USERNAME

    # Ensure the user owns their home. Snapshots can flatten file ownership to root, and
    # useradd won't re-chown an existing home, so a restored workspace would otherwise be
    # locked out (permission denied on the user's own files). Idempotent on fresh containers.
    mkdir -p /home/$SSH_USERNAME
    chown -R "$SSH_USERNAME:$SSH_USERNAME" /home/$SSH_USERNAME
fi

# Start SSH server
/usr/sbin/sshd -D
