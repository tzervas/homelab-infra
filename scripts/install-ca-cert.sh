#!/bin/bash

# CA Certificate Installation Script
# This script installs the homelab CA certificate into the system trust store.

CA_CERT_PATH="/tmp/homelab-ca.crt"
TRUST_STORE_PATH="/usr/local/share/ca-certificates/homelab-ca.crt"

set -e
echo "🔒 Installing homelab CA certificate into system trust store..."

# Check if the CA certificate exists
if [ ! -f "$CA_CERT_PATH" ]; then
    echo "❌ CA certificate not found at $CA_CERT_PATH. Aborting."
    exit 1
fi

# Copy the CA certificate to the system trust store
sudo cp "$CA_CERT_PATH" "$TRUST_STORE_PATH"
echo "🔄 CA certificate copied to $TRUST_STORE_PATH"

# Update the CA certificates
sudo update-ca-certificates --fresh

# Verify installation
if [ $? -eq 0 ]; then
    echo "✅ CA certificate installed successfully!"
else
    echo "❌ Failed to install CA certificate."
    exit 1
fi

# Output result
echo "🎉 The homelab CA certificate is now trusted by all applications!"
