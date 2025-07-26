#!/bin/bash
# SSH Readiness Test Script
# Standalone script to test SSH readiness logic
# Supports direct connection or via bastion host

set -e

# Configuration
HOST="${1:-192.168.122.241}"  # Default to last known VM IP
USER="${2:-kang}"
BASTION_HOST="${3:-}"  # Optional bastion host
MAX_ATTEMPTS=20
ATTEMPT=0

# SSH configuration
SSH_OPTS="-o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no"
if [[ -n "$BASTION_HOST" ]]; then
    SSH_OPTS="$SSH_OPTS -o ProxyJump=$USER@$BASTION_HOST"
fi

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <host> [user] [bastion_host]"
    echo "Example: $0 192.168.122.241 kang"
    echo "Example: $0 192.168.122.241 kang 192.168.16.26"
    echo ""
    echo "Using default host: $HOST"
    echo "Using default user: $USER"
    if [[ -n "$BASTION_HOST" ]]; then
        echo "Using bastion host: $BASTION_HOST"
    fi
    echo ""
fi

echo "🔍 Testing SSH readiness for $USER@$HOST"
echo "=========================================="

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo ""
    echo "🔄 Attempt $ATTEMPT/$MAX_ATTEMPTS"

    # Determine backoff time based on attempt
    if [ $ATTEMPT -le 5 ]; then
        backoff=5
    elif [ $ATTEMPT -le 10 ]; then
        backoff=8
    else
        backoff=10
    fi

    # Check connectivity (skip port check if using bastion)
    if [[ -n "$BASTION_HOST" ]]; then
        echo "   🔗 Using bastion host for connection"

        # Try SSH connection through bastion
        if timeout 10 ssh $SSH_OPTS $USER@$HOST 'echo "SSH_READY"' 2>/dev/null | grep -q "SSH_READY"; then
            echo "   🎉 SSH connection successful through bastion!"
            echo ""
            echo "✅ SSH readiness confirmed for $USER@$HOST via $BASTION_HOST"

            # Get basic system info
            echo ""
            echo "📋 Basic system information:"
            ssh $SSH_OPTS $USER@$HOST '
                echo "   Hostname: $(hostname)"
                echo "   Uptime: $(uptime | cut -d"," -f1)"
                echo "   Load: $(uptime | grep -o "load.*")"
                echo "   Memory: $(free -m | grep "Mem:" | awk "{print \$2\" MB total, \"\$3\" MB used\"}")"
            ' 2>/dev/null

            exit 0
        else
            echo "   ⏳ SSH not ready through bastion (host may still be booting)"
        fi
    else
        # Direct connection checks
        if nc -z -w3 $HOST 22 2>/dev/null; then
            echo "   ✅ Port 22 is open"

            # Try SSH connection
            if timeout 10 ssh $SSH_OPTS $USER@$HOST 'echo "SSH_READY"' 2>/dev/null | grep -q "SSH_READY"; then
                echo "   🎉 SSH connection successful!"
                echo ""
                echo "✅ SSH readiness confirmed for $USER@$HOST"

                # Get basic system info
                echo ""
                echo "📋 Basic system information:"
                ssh $SSH_OPTS $USER@$HOST '
                    echo "   Hostname: $(hostname)"
                    echo "   Uptime: $(uptime | cut -d"," -f1)"
                    echo "   Load: $(uptime | grep -o "load.*")"
                    echo "   Memory: $(free -m | grep "Mem:" | awk "{print \$2\" MB total, \"\$3\" MB used\"}")"
                ' 2>/dev/null

                exit 0
            else
                echo "   ⏳ Port open but SSH not ready (authentication/service still initializing)"
            fi
        else
            echo "   ⏳ Port 22 not yet available"
        fi

        # Basic diagnostics for direct connection
        if ping -c 1 -W 2 $HOST >/dev/null 2>&1; then
            echo "   📡 Network: Host is reachable"
        else
            echo "   ❌ Network: Host not responding to ping"
        fi
    fi

    echo "   ⏱️  Waiting $backoff seconds before next attempt..."
    sleep $backoff
done

echo ""
echo "❌ SSH readiness timeout after $MAX_ATTEMPTS attempts"
echo ""
echo "🔧 Troubleshooting suggestions:"
echo "   1. Check if host is up: ping $HOST"
echo "   2. Check if SSH service is running on host"
echo "   3. Verify SSH key authentication is properly configured"
echo "   4. Try manual connection: ssh -v $USER@$HOST"
echo ""

exit 1
