#!/bin/bash
# ESDDNS Operator - Quick Install Script
# This script makes it easy to install the ESDDNS operator to your Kubernetes cluster

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
NAMESPACE="esddns-system"
RELEASE_NAME="esddns-operator"
ENVIRONMENT="production"
SERVICE_TYPE="LoadBalancer"

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  ESDDNS Operator - Quick Install       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo
    echo -e "${BLUE}>>> $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    if ! command -v helm &> /dev/null; then
        print_error "helm not found. Please install Helm 3."
        exit 1
    fi
    
    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    print_info "kubectl: $(kubectl version --short | grep 'Client' | awk '{print $3}')"
    print_info "helm: $(helm version --short | grep 'v')"
    print_info "Cluster: $(kubectl cluster-info | head -1 | awk '{print $NF}' | tr -d '()')"
}

# Get configuration from user
get_configuration() {
    print_step "Configuration"
    
    # Gandi API Key
    read -p "Enter your Gandi.net API key: " GANDI_API_KEY
    if [ -z "$GANDI_API_KEY" ]; then
        print_error "API key is required"
        exit 1
    fi
    
    # Domain
    read -p "Enter your target domain (e.g., example.com): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        print_error "Domain is required"
        exit 1
    fi
    
    # Record name
    read -p "Enter DNS record name [default: @]: " RECORD_NAME
    RECORD_NAME=${RECORD_NAME:-"@"}
    
    # TTL
    read -p "Enter DNS TTL in seconds [default: 300]: " TTL
    TTL=${TTL:-"300"}
    
    # Service type
    echo
    echo "Select service type:"
    echo "  1) LoadBalancer (default - for cloud: AWS, GCP, Azure)"
    echo "  2) NodePort (for on-premises)"
    echo "  3) ClusterIP (for internal-only access)"
    read -p "Choice [1-3, default: 1]: " SERVICE_CHOICE
    case $SERVICE_CHOICE in
        2) SERVICE_TYPE="NodePort" ;;
        3) SERVICE_TYPE="ClusterIP" ;;
        *) SERVICE_TYPE="LoadBalancer" ;;
    esac
    
    # Environment
    echo
    echo "Select environment:"
    echo "  1) Production (default - optimized, INFO logging)"
    echo "  2) Development (debug logging, lower resources)"
    read -p "Choice [1-2, default: 1]: " ENV_CHOICE
    case $ENV_CHOICE in
        2) ENVIRONMENT="development" ;;
        *) ENVIRONMENT="production" ;;
    esac
    
    print_info "Configuration:"
    echo "  Domain: $DOMAIN"
    echo "  Record: $RECORD_NAME"
    echo "  TTL: $TTL"
    echo "  Service: $SERVICE_TYPE"
    echo "  Environment: $ENVIRONMENT"
}

# Create namespace
create_namespace() {
    print_step "Creating namespace..."
    
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        print_info "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace $NAMESPACE
        print_info "Namespace $NAMESPACE created"
    fi
}

# Install chart
install_chart() {
    print_step "Installing Helm chart..."
    
    # Check if release exists
    if helm list -n $NAMESPACE | grep -q $RELEASE_NAME; then
        print_warn "Release $RELEASE_NAME already exists in namespace $NAMESPACE"
        read -p "Do you want to upgrade it? [y/N]: " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            helm upgrade $RELEASE_NAME esddns-operator/ \
                --namespace $NAMESPACE \
                --set gandi.apiKey="$GANDI_API_KEY" \
                --set global.domain="$DOMAIN" \
                --set global.recordName="$RECORD_NAME" \
                --set global.recordTTL="$TTL" \
                --set service.type="$SERVICE_TYPE" \
                --set environment="$ENVIRONMENT"
        fi
    else
        helm install $RELEASE_NAME esddns-operator/ \
            --namespace $NAMESPACE \
            --set gandi.apiKey="$GANDI_API_KEY" \
            --set global.domain="$DOMAIN" \
            --set global.recordName="$RECORD_NAME" \
            --set global.recordTTL="$TTL" \
            --set service.type="$SERVICE_TYPE" \
            --set environment="$ENVIRONMENT"
        
        print_info "Helm chart installed successfully!"
    fi
}

# Wait for deployment
wait_for_deployment() {
    print_step "Waiting for pods to be ready..."
    
    # Check DaemonSet
    print_info "Checking operator DaemonSet..."
    timeout 300 kubectl rollout status daemonset/esddns-operator-daemon \
        -n $NAMESPACE || print_warn "DaemonSet rollout timeout"
    
    # Check Deployment
    print_info "Checking service Deployment..."
    timeout 300 kubectl rollout status deployment/esddns-service \
        -n $NAMESPACE || print_warn "Deployment rollout timeout"
}

# Display status
show_status() {
    print_step "Installation Status"
    
    echo
    print_info "Pods:"
    kubectl get pods -n $NAMESPACE
    
    echo
    print_info "Services:"
    kubectl get svc -n $NAMESPACE
}

# Show next steps
show_next_steps() {
    print_step "Next Steps"
    
    if [ "$SERVICE_TYPE" = "LoadBalancer" ]; then
        echo
        echo "1. Get the external IP:"
        echo "   kubectl get svc -n $NAMESPACE $RELEASE_NAME"
        echo
        echo "2. Wait for EXTERNAL-IP to be assigned (may take a few minutes)"
        echo
        echo "3. Test the service:"
        echo "   EXTERNAL_IP=\$(kubectl get svc -n $NAMESPACE esddns-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
        echo "   curl http://\$EXTERNAL_IP/"
    elif [ "$SERVICE_TYPE" = "NodePort" ]; then
        echo
        echo "1. Get the node port:"
        echo "   NODE_PORT=\$(kubectl get svc -n $NAMESPACE esddns-service -o jsonpath='{.spec.ports[0].nodePort}')"
        echo
        echo "2. Get a node IP:"
        echo "   NODE_IP=\$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type==\"ExternalIP\")].address}')"
        echo
        echo "3. Test the service:"
        echo "   curl http://\$NODE_IP:\$NODE_PORT/"
    else
        echo
        echo "1. Port-forward to the service:"
        echo "   kubectl port-forward -n $NAMESPACE svc/esddns-service 8080:80"
        echo
        echo "2. Test the service:"
        echo "   curl http://localhost:8080/"
    fi
    
    echo
    echo "4. Check operator logs:"
    echo "   kubectl logs -n $NAMESPACE -l app=esddns-operator -f"
    
    echo
    echo "5. View Prometheus metrics:"
    echo "   kubectl port-forward -n $NAMESPACE daemonset/esddns-operator-daemon 8080:8080"
    echo "   curl http://localhost:8080/metrics"
    
    echo
    echo "📚 Documentation:"
    echo "   - README: helm/esddns-operator/README.md"
    echo "   - Chart Values: helm/esddns-operator/values.yaml"
    echo
}

# Main execution
main() {
    print_header
    
    check_prerequisites
    get_configuration
    
    print_step "Review Configuration"
    echo "Domain: $DOMAIN"
    echo "API Key: ${GANDI_API_KEY:0:8}****"
    read -p "Proceed with installation? [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warn "Installation cancelled"
        exit 0
    fi
    
    create_namespace
    install_chart
    wait_for_deployment
    show_status
    show_next_steps
    
    echo
    print_info "Installation complete!"
    echo
}

# Run main function
main "$@"
