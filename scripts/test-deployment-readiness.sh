#!/bin/bash
# Pre-deployment Validation Script
# Tests connectivity and prerequisites before running the full deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header "🔍 Homelab Deployment Readiness Check"
echo "======================================="
echo ""

# Check local prerequisites
print_header "📋 Checking Local Prerequisites"
echo ""

if command -v ansible-playbook &> /dev/null; then
    ANSIBLE_VERSION=$(ansible-playbook --version | head -1)
    print_success "Ansible: $ANSIBLE_VERSION"
else
    print_error "Ansible not found. Install with: sudo apt install ansible"
    exit 1
fi

if command -v ssh &> /dev/null; then
    print_success "SSH client available"
else
    print_error "SSH client not found"
    exit 1
fi

if [ -f ~/.ssh/id_rsa.pub ] || [ -f ~/.ssh/id_ed25519.pub ]; then
    print_success "SSH public key found"
else
    print_warning "No SSH public key found. Generate with: ssh-keygen -t ed25519"
    echo "You'll need to copy the key to the server: ssh-copy-id kang@SERVER_IP"
fi

echo ""

# Check project structure
print_header "📁 Checking Project Structure"
echo ""

required_files=(
    "ansible/ansible.cfg"
    "ansible/site.yml"
    "ansible/inventory/hosts.yml"
    "ansible/playbooks/create-vm.yml"
    "ansible/playbooks/deploy-k3s.yml"
    "scripts/deploy-homelab.sh"
)

for file in "${required_files[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        print_success "$file"
    else
        print_error "$file missing"
    fi
done

echo ""

# Test Ansible syntax
print_header "🔧 Testing Ansible Configuration"
echo ""

cd "$PROJECT_ROOT/ansible"

if ansible-playbook --syntax-check site.yml > /dev/null 2>&1; then
    print_success "Ansible playbook syntax OK"
else
    print_error "Ansible playbook syntax error"
    ansible-playbook --syntax-check site.yml
    exit 1
fi

if ansible-inventory --list > /dev/null 2>&1; then
    print_success "Ansible inventory OK"
else
    print_error "Ansible inventory error"
    ansible-inventory --list
    exit 1
fi

echo ""

# Network configuration check
print_header "🌐 Network Configuration"
echo ""

# Extract server IP from inventory (if available)
SERVER_IP=$(grep -o 'homelab_server_ip.*default.*' inventory/hosts.yml | grep -o "'[^']*'" | tr -d "'" | head -1 2>/dev/null || echo "")

if [ -n "$SERVER_IP" ] && [ "$SERVER_IP" != "*************" ]; then
    echo "Target server: $SERVER_IP"

    # Test ping
    if ping -c 1 -W 3 "$SERVER_IP" > /dev/null 2>&1; then
        print_success "Server $SERVER_IP is reachable"
    else
        print_warning "Server $SERVER_IP not responding to ping"
    fi

    # Test SSH
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "kang@$SERVER_IP" 'echo "SSH OK"' > /dev/null 2>&1; then
        print_success "SSH connection to server OK"

        # Check server resources
        echo ""
        print_header "💻 Server Resources Check"
        echo ""

        SSH_CMD="ssh -o ConnectTimeout=10 kang@$SERVER_IP"

        # Memory check
        MEMORY_GB=$($SSH_CMD "free -g | awk 'NR==2{printf \"%.0f\", \$2}'")
        if [ "$MEMORY_GB" -ge 16 ]; then
            print_success "Memory: ${MEMORY_GB}GB (sufficient for VM testing)"
        else
            print_warning "Memory: ${MEMORY_GB}GB (recommended: 16GB+ for VM testing)"
        fi

        # Disk space check
        DISK_GB=$($SSH_CMD "df -BG /var/lib/libvirt 2>/dev/null | awk 'NR==2{print \$4}' | tr -d 'G' || df -BG / | awk 'NR==2{print \$4}' | tr -d 'G'")
        if [ "$DISK_GB" -ge 200 ]; then
            print_success "Disk space: ${DISK_GB}GB available (sufficient)"
        else
            print_warning "Disk space: ${DISK_GB}GB available (recommended: 200GB+)"
        fi

        # KVM support check
        if $SSH_CMD "grep -q 'vmx\|svm' /proc/cpuinfo"; then
            print_success "Hardware virtualization support detected"
        else
            print_warning "Hardware virtualization may not be available"
        fi

        # Check if KVM is installed
        if $SSH_CMD "command -v virsh > /dev/null 2>&1"; then
            print_success "KVM/libvirt already installed"
        else
            print_warning "KVM/libvirt not installed (will be installed during deployment)"
        fi

    else
        print_error "SSH connection failed to kang@$SERVER_IP"
        echo ""
        echo "🔑 To fix SSH access:"
        echo "   1. Generate SSH key (if not done): ssh-keygen -t ed25519"
        echo "   2. Copy key to server: ssh-copy-id kang@$SERVER_IP"
        echo "   3. Test connection: ssh kang@$SERVER_IP"
        exit 1
    fi
else
    print_warning "Server IP not configured or redacted in inventory"
    echo "Configure the server IP in ansible/inventory/hosts.yml"
fi

echo ""

# Summary
print_header "📊 Readiness Summary"
echo ""

echo "🎯 Ready for deployment phases:"
echo "   • vm-test: Create VM and test deployment"
echo "   • bare-metal: Deploy directly to server"
echo ""
echo "🚀 To start VM testing:"
echo "   ./scripts/deploy-homelab.sh vm-test"
echo ""
echo "💡 For verbose output:"
echo "   VERBOSE=true ./scripts/deploy-homelab.sh vm-test"
echo ""

print_success "All prerequisites checked! Ready for deployment."
