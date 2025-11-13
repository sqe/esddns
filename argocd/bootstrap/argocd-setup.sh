#!/bin/bash
# Bootstrap script to setup ArgoCD and deploy ESDDNS applications
# Usage: ./argocd-setup.sh [dev|prod|both]

set -e

NAMESPACE="argocd"
REPO_URL="https://github.com/sqe/esddns"
ENVIRONMENT="${1:-dev}"

echo "=========================================="
echo "ArgoCD ESDDNS Bootstrap Setup"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

# Check cluster connectivity
echo "[1/5] Checking cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Cannot connect to Kubernetes cluster"
    exit 1
fi
echo "✓ Cluster connected"

# Create ArgoCD namespace if needed
echo "[2/5] Creating ArgoCD namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
echo "✓ Namespace ready"

# Verify ArgoCD installation
echo "[3/5] Verifying ArgoCD installation..."
if ! kubectl get deployment argocd-server -n $NAMESPACE &> /dev/null; then
    echo "⚠ ArgoCD not found. Install with:"
    echo ""
    echo "  helm repo add argo https://argoproj.github.io/argo-helm"
    echo "  helm repo update"
    echo "  helm install argocd argo/argo-cd -n $NAMESPACE"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ ArgoCD is installed"
fi

# Deploy applications based on environment
echo "[4/5] Deploying ESDDNS Applications..."

case "$ENVIRONMENT" in
    dev)
        echo "  Deploying development environment..."
        kubectl apply -k ../dev/
        echo "✓ Development applications deployed"
        ;;
    prod)
        echo "  Deploying production environment..."
        kubectl apply -k ../prod/
        echo "✓ Production applications deployed"
        ;;
    both)
        echo "  Deploying development environment..."
        kubectl apply -k ../dev/
        echo "✓ Development applications deployed"
        echo "  Deploying production environment..."
        kubectl apply -k ../prod/
        echo "✓ Production applications deployed"
        ;;
    *)
        echo "Error: Invalid environment '$ENVIRONMENT'. Use: dev, prod, or both"
        exit 1
        ;;
esac

echo ""
echo "[5/5] Verifying deployment..."
sleep 2
kubectl get applications -n $NAMESPACE
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Wait for applications to sync:"
echo "   kubectl get applications -n $NAMESPACE"
echo ""
echo "2. Access ArgoCD UI:"
echo "   kubectl port-forward svc/argocd-server -n $NAMESPACE 8080:443"
echo "   Open: https://localhost:8080"
echo ""
echo "3. Get ArgoCD admin password:"
echo "   kubectl -n $NAMESPACE get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
echo ""
echo "Deployed Applications:"

case "$ENVIRONMENT" in
    dev)
        echo "  - esddns-operator-helm-dev"
        echo "  - esddns-operator-kustomize-dev"
        ;;
    prod)
        echo "  - esddns-operator-helm-prod"
        echo "  - esddns-operator-kustomize-prod"
        ;;
    both)
        echo "  - esddns-operator-helm-dev"
        echo "  - esddns-operator-kustomize-dev"
        echo "  - esddns-operator-helm-prod"
        echo "  - esddns-operator-kustomize-prod"
        ;;
esac
echo ""
echo "View logs:"
echo "  argocd app logs esddns-operator-helm-$ENVIRONMENT"
