#!/bin/bash

# Script to set up SSH access to the remote k3s server
# Usage: ./setup_ssh.sh <remote_ip>

set -euo pipefail

# Check if IP address is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <remote_ip>"
    exit 1
fi

REMOTE_IP="$1"
REMOTE_USER="kang"
KEY_TYPE="ed25519"
KEY_FILE="$HOME/.ssh/id_${KEY_TYPE}"
KEY_COMMENT="k3s-homelab-$(date +%Y%m%d)"

# Check if key already exists
if [ -f "${KEY_FILE}" ]; then
    echo "SSH key already exists at ${KEY_FILE}"
    echo "Skipping key generation..."
else
    # Generate SSH key
    echo "Generating new SSH key..."
    ssh-keygen -t ${KEY_TYPE} -f "${KEY_FILE}" -C "${KEY_COMMENT}" -N ""
fi

# Ensure .ssh directory exists with correct permissions
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add host key checking settings
cat >> ~/.ssh/config << EOF
Host ${REMOTE_IP}
    HostName ${REMOTE_IP}
    User ${REMOTE_USER}
    IdentityFile ${KEY_FILE}
    StrictHostKeyChecking yes
    UserKnownHostsFile ~/.ssh/known_hosts
EOF

chmod 600 ~/.ssh/config

echo "SSH key and config created successfully!"
echo
echo "Next steps:"
echo "1. Copy the public key to the remote server:"
echo "   ssh-copy-id -i ${KEY_FILE} ${REMOTE_USER}@${REMOTE_IP}"
echo
echo "2. Test the connection:"
echo "   ssh ${REMOTE_USER}@${REMOTE_IP} echo 'Connection successful'"
echo
echo "3. Update your .env file with:"
echo "   REMOTE_HOST_IP=${REMOTE_IP}"
echo "   REMOTE_USER=${REMOTE_USER}"
echo "   REMOTE_SSH_KEY_PATH=${KEY_FILE}"
