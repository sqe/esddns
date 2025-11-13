#!/bin/bash

# ESDDNS Kubernetes Deployment Script
# Simplifies deployment to dev or production environments

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-development}"
NAMESPACE="esddns${ENVIRONMENT:+-$ENVIRONMENT}"
OVERLAY_DIR="$SCRIPT_DIR/overlays/$ENVIRONMENT"
MANIFEST_FILE="esddns-$ENVIRONMENT.yaml"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    if ! command -v kustomize &> /dev/null; then
        print_error "kustomize not found. Please install kustomize (v5.0+)."
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Check kubeconfig."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Validate configuration
validate_config() {
    print_status "Validating configuration..."
    
    if [[ ! -d "$OVERLAY_DIR" ]]; then
        print_error "Overlay directory not found: $OVERLAY_DIR"
        exit 1
    fi
    
    if [[ ! -f "$OVERLAY_DIR/kustomization.yaml" ]]; then
        print_error "kustomization.yaml not found in $OVERLAY_DIR"
        exit 1
    fi
    
    print_status "Configuration validation passed"
}

# Generate manifests
generate_manifests() {
    print_status "Generating manifests for $ENVIRONMENT environment..."
    
    kustomize build "$OVERLAY_DIR" > "$MANIFEST_FILE"
    print_status "Manifests generated: $MANIFEST_FILE"
}

# Create namespace
create_namespace() {
    print_status "Creating namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_warn "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace "$NAMESPACE"
        print_status "Namespace created"
    fi
}

# Setup secrets
setup_secrets() {
    print_status "Setting up secrets..."
    
    if kubectl get secret esddns-gandi-credentials -n "$NAMESPACE" &> /dev/null; then
        print_warn "Secret already exists. Skipping..."
        return
    fi
    
    if [[ -z "${GANDI_API_KEY:-}" ]]; then
        print_warn "GANDI_API_KEY not set. Using placeholder value."
        read -p "Enter Gandi API key (or press Enter to use placeholder): " api_key
        api_key="${api_key:-PLACEHOLDER_API_KEY}"
    else
        api_key="$GANDI_API_KEY"
    fi
    
    kubectl create secret generic esddns-gandi-credentials \
        --from-literal=api-key="$api_key" \
        -n "$NAMESPACE"
    print_status "Secret created"
}

# Deploy manifests
deploy() {
    print_status "Deploying to namespace: $NAMESPACE"
    
    kubectl apply -f "$MANIFEST_FILE"
    print_status "Manifests applied"
}

# Wait for deployment
wait_for_deployment() {
    print_status "Waiting for deployments to be ready..."
    
    # Wait for DaemonSet
    kubectl rollout status daemonset/esddns-operator-daemon \
        -n "$NAMESPACE" --timeout=300s || true
    
    # Wait for Deployment
    kubectl rollout status deployment/esddns-service \
        -n "$NAMESPACE" --timeout=300s || true
    
    print_status "Deployment ready"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    print_status "Resources in namespace:"
    kubectl get all -n "$NAMESPACE"
    
    print_status "Checking service status:"
    kubectl get svc -n "$NAMESPACE" esddns-service
    
    # Try to get LoadBalancer IP
    ip=$(kubectl get svc -n "$NAMESPACE" esddns-service \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [[ -n "$ip" ]]; then
        print_status "LoadBalancer IP: $ip"
        print_status "Service endpoint: http://$ip/"
    else
        print_warn "LoadBalancer IP not yet assigned (may take a few minutes)"
        print_warn "Run: kubectl get svc -n $NAMESPACE esddns-service"
    fi
    
    print_status "Checking pod status:"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    print_status "Checking operator logs:"
    pod=$(kubectl get pod -n "$NAMESPACE" -l app=esddns-operator \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [[ -n "$pod" ]]; then
        kubectl logs -n "$NAMESPACE" "$pod" --tail=20
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [environment]

Environments:
  development   Deploy to development namespace (default)
  production    Deploy to production namespace

Examples:
  $0                    # Deploy to development
  $0 production         # Deploy to production

Environment variables:
  GANDI_API_KEY        Gandi.net API key (optional, can be provided interactively)

Generated files:
  esddns-development.yaml   Development manifest
  esddns-production.yaml    Production manifest

Post-deployment:
  Check logs:  kubectl logs -n esddns-{dev,system} -l app=esddns-operator -f
  Port forward: kubectl port-forward -n esddns-{dev,system} <pod> 8080:8080
EOF
}

# Main execution
main() {
    case "${ENVIRONMENT}" in
        development|production)
            check_prerequisites
            validate_config
            generate_manifests
            
            echo ""
            print_status "Generated manifests in: $MANIFEST_FILE"
            echo ""
            echo "Next steps:"
            echo "  1. Review manifests: cat $MANIFEST_FILE"
            echo "  2. Deploy: kubectl apply -f $MANIFEST_FILE"
            echo "  3. Monitor: kubectl get pods -n $NAMESPACE -w"
            echo "  4. Check logs: kubectl logs -n $NAMESPACE -l app=esddns-operator -f"
            echo ""
            
            read -p "Deploy now? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                create_namespace
                setup_secrets
                deploy
                wait_for_deployment
                verify_deployment
                print_status "Deployment complete!"
            else
                print_status "Skipped deployment. Run 'kubectl apply -f $MANIFEST_FILE' when ready."
            fi
            ;;
        -h|--help|help)
            show_usage
            ;;
        *)
            print_error "Invalid environment: $ENVIRONMENT"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
