#!/bin/bash
# Helm Chart Publishing Script for Artifact Hub
# This script packages and prepares charts for Artifact Hub distribution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CHART_DIR="esddns-operator"
REPO_DIR="helm-repo"
GITHUB_REPO="${GITHUB_REPO:-sqe/esddns}"
GITHUB_BRANCH="${GITHUB_BRANCH:-gh-pages}"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    
    print_info "Prerequisites check passed ✓"
}

# Validate chart
validate_chart() {
    print_info "Validating Helm chart..."
    
    if [ ! -d "$CHART_DIR" ]; then
        print_error "Chart directory not found: $CHART_DIR"
        exit 1
    fi
    
    if ! helm lint "$CHART_DIR"; then
        print_error "Helm lint failed"
        exit 1
    fi
    
    print_info "Chart validation passed ✓"
}

# Template test
template_test() {
    print_info "Testing template rendering..."
    
    if ! helm template esddns-operator "$CHART_DIR" > /tmp/esddns-template.yaml 2>&1; then
        print_error "Template rendering failed"
        exit 1
    fi
    
    print_info "Template rendering passed ✓"
}

# Package chart
package_chart() {
    print_info "Packaging chart..."
    
    mkdir -p "$REPO_DIR"
    
    if helm package "$CHART_DIR" -d "$REPO_DIR"; then
        print_info "Chart packaged successfully ✓"
    else
        print_error "Chart packaging failed"
        exit 1
    fi
}

# Generate repository index
generate_index() {
    print_info "Generating repository index..."
    
    if helm repo index "$REPO_DIR" --url "https://$(echo $GITHUB_REPO | cut -d'/' -f1).github.io/$(echo $GITHUB_REPO | cut -d'/' -f2)/helm-repo"; then
        print_info "Repository index generated ✓"
    else
        print_error "Index generation failed"
        exit 1
    fi
}

# Show instructions
show_instructions() {
    cat << EOF

${GREEN}=== Chart Publishing Instructions ===${NC}

Your chart has been packaged and is ready for Artifact Hub.

${YELLOW}Next Steps:${NC}

1. Review the packaged chart:
   ls -la $REPO_DIR/

2. Stage and commit changes:
   git add $REPO_DIR/
   git commit -m "Release esddns-operator Helm chart v1.0.0"

3. Push to GitHub:
   git push origin main

4. Set up GitHub Pages (if not already done):
   a. Go to https://github.com/$GITHUB_REPO/settings/pages
   b. Set source to "Deploy from a branch"
   c. Select "gh-pages" branch (or create it from main)

5. Register on Artifact Hub:
   a. Visit https://artifacthub.io
   b. Sign in with GitHub
   c. Click "Control Panel" → "Repositories"
   d. Click "Add" and select "GitHub"
   e. Choose your repository: $GITHUB_REPO
   f. Set Chart Repository URL to:
      https://${GITHUB_REPO%/*}.github.io/${GITHUB_REPO#*/}/helm-repo

6. Wait for Artifact Hub to sync:
   The chart will appear at:
   https://artifacthub.io/packages/helm/...

${YELLOW}Verification:${NC}

Test the chart locally:
  helm install esddns-operator $CHART_DIR \\
    --set gandi.apiKey=test-key \\
    --dry-run --debug

${YELLOW}Documentation:${NC}
- Chart README: $CHART_DIR/README.md
- Values: $CHART_DIR/values.yaml
- Changelog: $CHART_DIR/CHANGELOG.md

EOF
}

# Main execution
main() {
    print_info "ESDDNS Helm Chart Publisher"
    print_info "=============================="
    echo
    
    check_prerequisites
    validate_chart
    template_test
    package_chart
    generate_index
    
    echo
    print_info "Chart preparation complete!"
    echo
    
    show_instructions
}

# Run main function
main "$@"
