#!/bin/bash

# Set the SSH username and password using environment variables
SSH_USERNAME=${SSH_USERNAME:-"ubuntu"}  # Default username is "ubuntu"
SSH_PASSWORD=${SSH_PASSWORD:-""}        # Default password is empty

if [ -n "$SSH_USERNAME" ]; then
    # Fresh containers have no such user; containers restored from a snapshot already do
    # (the account is captured in /etc/passwd), so only create it when it's missing.
    #
    # gVisor (the runtime these pods run under) does not implement setuid-on-exec at all -
    # it's a deliberate part of its security model (a child can never gain more privilege
    # than its parent), not a bug. That means classic sudo (which works by transitioning an
    # unprivileged process to uid 0 via the setuid bit) can never work here, regardless of
    # group membership. So instead of relying on privilege *escalation*, the login user IS
    # uid 0 from the start (-u 0 -o: alias this username onto the existing uid 0, rather than
    # a distinct non-zero uid) - real root, personalized username/home dir, no transition
    # needed. Package installs etc. just work directly.
    if id "$SSH_USERNAME" >/dev/null 2>&1; then
        echo "User $SSH_USERNAME already exists (restored container)"
    else
        echo "Adding new user $SSH_USERNAME (uid 0 alias - see gVisor note above)..."
        useradd -m -d /home/$SSH_USERNAME -s /bin/bash -u 0 -o $SSH_USERNAME
    fi

    if [ -n "$SSH_PASSWORD" ]; then
        echo "Setting SSH password..."
        echo "$SSH_USERNAME:$SSH_PASSWORD" | chpasswd
    fi

    # Ensure the user owns their home. Snapshots can flatten file ownership to root, and
    # useradd won't re-chown an existing home, so a restored workspace would otherwise be
    # locked out (permission denied on the user's own files). Idempotent on fresh containers.
    mkdir -p /home/$SSH_USERNAME
    chown -R "$SSH_USERNAME:$SSH_USERNAME" /home/$SSH_USERNAME
fi

# The login user is already uid 0 (see above), so no command ever actually needs sudo's
# privilege escalation here - but real sudo still refuses to run at all under gVisor (it
# fails its own setuid self-check before it would even notice the caller is already root).
# Shim it as a passthrough so muscle-memory `sudo <cmd>` keeps working identically to
# running <cmd> directly. Placed in /usr/local/bin, which precedes /usr/bin in the default
# PATH, so it shadows the real (non-functional) /usr/bin/sudo.
mkdir -p /usr/local/bin
cat > /usr/local/bin/sudo <<'SUDOSHIM'
#!/bin/bash
exec "$@"
SUDOSHIM
chmod +x /usr/local/bin/sudo

# Start SSH server
/usr/sbin/sshd -D
