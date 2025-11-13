#!/bin/bash

# ESDDNS On-Premises Deployment with MetalLB
# Deploys MetalLB and ESDDNS operator for bare-metal Kubernetes clusters

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
METALLB_VERSION="${METALLB_VERSION:-v0.14.5}"
METALLB_NAMESPACE="metallb-system"
ESDDNS_ENVIRONMENT="${1:-production}"
IP_RANGE="${2:-}"

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

print_header() {
    echo -e "${BLUE}===${NC} $1 ${BLUE}===${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    if ! command -v helm &> /dev/null; then
        print_warn "helm not found. Will use kubectl for MetalLB installation."
        USE_KUBECTL=1
    else
        USE_KUBECTL=0
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Check kubeconfig."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Get IP range from user if not provided
get_ip_range() {
    if [[ -z "$IP_RANGE" ]]; then
        echo ""
        print_header "IP Address Pool Configuration"
        echo "MetalLB needs an IP range to allocate LoadBalancer IPs."
        echo "This should be a range of IPs on your local network that are not used by DHCP."
        echo ""
        echo "Examples:"
        echo "  Single IP:    192.168.1.100/32"
        echo "  Range:        192.168.1.100-192.168.1.110"
        echo "  CIDR:         192.168.1.100/28"
        echo ""
        read -p "Enter IP range: " IP_RANGE
        
        if [[ -z "$IP_RANGE" ]]; then
            print_error "IP range is required"
            exit 1
        fi
    fi
}

# Install MetalLB
install_metallb() {
    print_header "Installing MetalLB $METALLB_VERSION"
    
    if kubectl get namespace "$METALLB_NAMESPACE" &> /dev/null; then
        print_warn "MetalLB namespace already exists. Skipping installation."
        return
    fi
    
    if [[ $USE_KUBECTL -eq 1 ]]; then
        # Install via kubectl
        print_status "Installing MetalLB via kubectl..."
        kubectl apply -f "https://raw.githubusercontent.com/metallb/metallb/$METALLB_VERSION/config/manifests/metallb-native.yaml"
    else
        # Install via Helm
        print_status "Installing MetalLB via Helm..."
        helm repo add metallb https://metallb.github.io/metallb
        helm repo update
        helm install metallb metallb/metallb \
            --namespace "$METALLB_NAMESPACE" \
            --create-namespace \
            --version "$METALLB_VERSION"
    fi
    
    print_status "Waiting for MetalLB controller to be ready..."
    kubectl wait --namespace "$METALLB_NAMESPACE" \
        --for=condition=ready pod \
        --selector=app=metallb \
        --timeout=90s || print_warn "Timeout waiting for MetalLB pods"
    
    # Wait a bit for webhook to be ready
    sleep 5
    
    print_status "MetalLB installed successfully"
}

# Configure MetalLB with IP address pool
configure_metallb() {
    print_header "Configuring MetalLB IP Address Pool"
    
    print_status "Creating IPAddressPool: esddns-pool"
    
    # Determine if range or CIDR format
    if [[ "$IP_RANGE" =~ - ]]; then
        # Range format: 192.168.1.100-192.168.1.110
        ADDRESS_LINE="  - $IP_RANGE"
    else
        # CIDR format: 192.168.1.100/32 or 192.168.1.100/28
        ADDRESS_LINE="  - $IP_RANGE"
    fi
    
    cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: esddns-pool
  namespace: $METALLB_NAMESPACE
spec:
  addresses:
$ADDRESS_LINE
  autoAssign: true
EOF
    
    print_status "IP Address Pool created"
    
    # Create L2Advertisement for Layer 2 mode (default, simplest)
    print_status "Creating L2Advertisement..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: esddns-l2-advertisement
  namespace: $METALLB_NAMESPACE
spec:
  ipAddressPools:
  - esddns-pool
EOF
    
    print_status "L2Advertisement created (Layer 2 mode)"
    print_warn "Note: For BGP mode, manually create BGPPeer and BGPAdvertisement resources"
}

# Deploy ESDDNS
deploy_esddns() {
    print_header "Deploying ESDDNS Operator"
    
    print_status "Running ESDDNS deployment script for $ESDDNS_ENVIRONMENT..."
    
    cd "$SCRIPT_DIR"
    ./deploy.sh "$ESDDNS_ENVIRONMENT"
}

# Verify deployment
verify_deployment() {
    print_header "Verifying Deployment"
    
    # Check MetalLB
    print_status "MetalLB Status:"
    kubectl get all -n "$METALLB_NAMESPACE"
    
    echo ""
    print_status "MetalLB IP Address Pools:"
    kubectl get ipaddresspool -n "$METALLB_NAMESPACE"
    
    # Check ESDDNS
    local namespace="esddns-$ESDDNS_ENVIRONMENT"
    echo ""
    print_status "ESDDNS Status:"
    kubectl get all -n "$namespace"
    
    echo ""
    print_status "ESDDNS LoadBalancer Service:"
    kubectl get svc -n "$namespace" esddns-service
    
    # Try to get LoadBalancer IP
    local lb_ip=$(kubectl get svc -n "$namespace" esddns-service \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    echo ""
    if [[ -n "$lb_ip" ]]; then
        print_status "✅ LoadBalancer IP assigned: $lb_ip"
        print_status "✅ Service endpoint: http://$lb_ip/"
        echo ""
        print_status "Testing endpoint..."
        if curl -s --connect-timeout 5 "http://$lb_ip/" > /dev/null 2>&1; then
            print_status "✅ Service is responding!"
        else
            print_warn "Service not yet responding (may take a minute to start)"
        fi
    else
        print_warn "⏳ LoadBalancer IP not yet assigned"
        print_warn "This should appear within 30 seconds for MetalLB"
        print_warn "Check status: kubectl get svc -n $namespace esddns-service -w"
    fi
}

# Show post-installation info
show_info() {
    print_header "Post-Installation Information"
    
    local namespace="esddns-$ESDDNS_ENVIRONMENT"
    
    cat <<EOF

${GREEN}MetalLB Configuration:${NC}
  Mode:           Layer 2 (ARP-based)
  IP Pool:        $IP_RANGE
  Namespace:      $METALLB_NAMESPACE

${GREEN}ESDDNS Deployment:${NC}
  Environment:    $ESDDNS_ENVIRONMENT
  Namespace:      $namespace

${GREEN}Useful Commands:${NC}
  # Get LoadBalancer IP
  kubectl get svc -n $namespace esddns-service

  # Watch for IP assignment
  kubectl get svc -n $namespace esddns-service -w

  # View ESDDNS logs
  kubectl logs -n $namespace -l app=esddns-operator -f

  # View service logs
  kubectl logs -n $namespace -l app=esddns-service -f

  # Test endpoint (once IP is assigned)
  EXTERNAL_IP=\$(kubectl get svc -n $namespace esddns-service \\
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  curl http://\$EXTERNAL_IP/

${GREEN}MetalLB Advanced Configuration:${NC}
  # For BGP mode instead of Layer 2, create BGPPeer resources:
  # See: https://metallb.universe.tf/configuration/#bgp-configuration

  # View MetalLB speaker logs (troubleshooting)
  kubectl logs -n $METALLB_NAMESPACE -l component=speaker -f

${GREEN}STUN-based WAN IP Detection:${NC}
  ESDDNS uses STUN protocol to detect your public WAN IP behind NAT.
  MetalLB provides the LoadBalancer capability, while STUN discovers
  the actual public IP address for DNS updates.

  This combination works perfectly for on-premises deployments!

${GREEN}Documentation:${NC}
  Main README:     README.md
  Quick Start:     QUICKSTART.md
  Architecture:    k8s/README.md
  Operator Guide:  README_OPERATOR.md

EOF
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [environment] [ip-range]

This script installs MetalLB and deploys ESDDNS for on-premises Kubernetes.

Arguments:
  environment   ESDDNS environment: development or production (default: production)
  ip-range      IP range for MetalLB LoadBalancer allocation (interactive if not provided)

Examples:
  $0                                    # Interactive: asks for IP range
  $0 production 192.168.1.100/32        # Single IP
  $0 production 192.168.1.100-192.168.1.110  # IP range
  $0 development 10.0.0.100/28          # Dev environment with CIDR

Environment variables:
  METALLB_VERSION    MetalLB version to install (default: v0.14.5)
  GANDI_API_KEY      Gandi.net API key (for ESDDNS deployment)

IP Range Formats:
  Single IP:    192.168.1.100/32
  Range:        192.168.1.100-192.168.1.110
  CIDR:         192.168.1.0/24

What this script does:
  1. Checks prerequisites (kubectl, helm)
  2. Installs MetalLB (via Helm or kubectl)
  3. Configures MetalLB IP address pool (Layer 2 mode)
  4. Deploys ESDDNS operator with LoadBalancer service
  5. Verifies deployment and shows status

Notes:
  - MetalLB uses Layer 2 mode by default (ARP-based, same-subnet only)
  - For BGP mode, manually create BGPPeer resources after installation
  - Ensure the IP range is available on your network (not used by DHCP)
  - ESDDNS uses STUN protocol for WAN IP detection (works with MetalLB)

EOF
}

# Main execution
main() {
    case "${ESDDNS_ENVIRONMENT}" in
        development|production)
            print_header "ESDDNS On-Premises Deployment with MetalLB"
            echo ""
            
            check_prerequisites
            get_ip_range
            
            echo ""
            print_status "Configuration:"
            echo "  MetalLB Version:    $METALLB_VERSION"
            echo "  IP Range:           $IP_RANGE"
            echo "  ESDDNS Environment: $ESDDNS_ENVIRONMENT"
            echo ""
            
            read -p "Proceed with installation? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_status "Installation cancelled"
                exit 0
            fi
            
            echo ""
            install_metallb
            echo ""
            configure_metallb
            echo ""
            deploy_esddns
            echo ""
            verify_deployment
            echo ""
            show_info
            
            print_status "✅ Installation complete!"
            ;;
        -h|--help|help)
            show_usage
            ;;
        *)
            print_error "Invalid environment: $ESDDNS_ENVIRONMENT"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
