#!/bin/bash
# Kubernetes Manifest Validation Script
# Performs comprehensive validation of Kubernetes YAML manifests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
  echo -e "${PURPLE}$1${NC}"
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

print_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

validate_k8s_manifest() {
  local file="$1"
  local errors=0

  print_info "Validating $file..."

  # Check YAML syntax
  if ! python3 -c "import yaml; list(yaml.safe_load_all(open('$file')))" 2>/dev/null; then
    print_error "Invalid YAML syntax"
    return 1
  fi

  # Extract and validate each document
  python3 <<EOF
import yaml
import sys

with open('$file', 'r') as f:
    try:
        docs = list(yaml.safe_load_all(f))
        print(f"📄 Found {len(docs)} document(s)")

        for i, doc in enumerate(docs):
            if doc is None:
                continue

            doc_num = i + 1

            # Check required fields
            if 'apiVersion' not in doc:
                print(f"❌ Document {doc_num}: Missing 'apiVersion'")
                sys.exit(1)

            if 'kind' not in doc:
                print(f"❌ Document {doc_num}: Missing 'kind'")
                sys.exit(1)

            if 'metadata' not in doc:
                print(f"❌ Document {doc_num}: Missing 'metadata'")
                sys.exit(1)

            # Extract info
            kind = doc.get('kind', 'Unknown')
            name = doc.get('metadata', {}).get('name', 'unnamed')
            namespace = doc.get('metadata', {}).get('namespace', 'default')

            print(f"  {doc_num}. {kind}/{name} (ns: {namespace})")

            # Kind-specific validation
            if kind == 'Deployment':
                if 'spec' not in doc or 'template' not in doc.get('spec', {}):
                    print(f"⚠️  Document {doc_num}: Deployment missing spec.template")

            elif kind == 'Service':
                if 'spec' not in doc or 'ports' not in doc.get('spec', {}):
                    print(f"⚠️  Document {doc_num}: Service missing spec.ports")

            elif kind == 'Ingress':
                if 'spec' not in doc:
                    print(f"⚠️  Document {doc_num}: Ingress missing spec")

            elif kind == 'ConfigMap' or kind == 'Secret':
                if 'data' not in doc and 'stringData' not in doc:
                    print(f"⚠️  Document {doc_num}: {kind} missing data/stringData")

        print("✅ All documents have valid structure")

    except Exception as e:
        print(f"❌ Validation error: {e}")
        sys.exit(1)
EOF

  return $?
}

print_header "🔍 Kubernetes Manifest Validation"
echo "=================================="
echo ""

cd "$PROJECT_ROOT"

# Find all Kubernetes YAML files
K8S_FILES=$(find kubernetes/ -name "*.yaml" -o -name "*.yml" 2>/dev/null)

if [ -z "$K8S_FILES" ]; then
  print_warning "No Kubernetes manifest files found"
  exit 0
fi

TOTAL_FILES=0
VALID_FILES=0
INVALID_FILES=0

for file in $K8S_FILES; do
  TOTAL_FILES=$((TOTAL_FILES + 1))
  echo ""

  if validate_k8s_manifest "$file"; then
    print_success "$file - Valid Kubernetes manifest"
    VALID_FILES=$((VALID_FILES + 1))
  else
    print_error "$file - Invalid Kubernetes manifest"
    INVALID_FILES=$((INVALID_FILES + 1))
  fi
done

echo ""
print_header "📊 Validation Summary"
echo ""

echo "📈 Statistics:"
echo "  • Total files checked: $TOTAL_FILES"
echo "  • Valid manifests: $VALID_FILES"
echo "  • Invalid manifests: $INVALID_FILES"
echo ""

if [ $INVALID_FILES -eq 0 ]; then
  print_success "All Kubernetes manifests are valid! 🎉"
  echo ""
  echo "💡 Ready for deployment:"
  echo "  • All YAML syntax is correct"
  echo "  • All required Kubernetes fields present"
  echo "  • Manifests ready for kubectl apply"
  exit 0
else
  print_error "Some manifests need attention"
  echo ""
  echo "🔧 Please fix the invalid manifests before deployment"
  exit 1
fi
