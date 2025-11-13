# Publishing Kubernetes Operators to Artifact Hub

This guide walks you through publishing your Kubernetes Operator Helm chart to Artifact Hub, making it discoverable and installable for the Kubernetes community worldwide.

> **About this guide**: While examples use ESDDNS, this guide applies to any Kubernetes operator. Substitute your operator name where indicated.

## What is Artifact Hub?

Artifact Hub (https://artifacthub.io/) is a web-based application that helps users find, install, and publish Kubernetes packages (Helm charts, operators, etc.).

## Prerequisites

1. **GitHub Account** - Required for publishing to Artifact Hub
2. **GitHub Repository** - Your ESDDNS repository with Helm charts
3. **Helm 3** - For packaging and validating charts
4. **Git CLI** - For version control

## Step 1: Prepare Your Chart

### Validate the Chart

```bash
cd helm/
helm lint esddns-operator/
helm template esddns-operator esddns-operator/ > /tmp/test.yaml
```

Expected output:
```
==> Linting esddns-operator/
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 error(s)
```

### Review Chart Files

Ensure your chart has:
- ✅ `Chart.yaml` - Chart metadata with proper versioning
- ✅ `values.yaml` - All configurable values
- ✅ `README.md` - User-facing documentation
- ✅ `CHANGELOG.md` - Version history
- ✅ `templates/` - All Kubernetes manifests
- ✅ `templates/NOTES.txt` - Post-installation instructions

## Step 2: Create Helm Repository Structure

### Using the Publish Script (Recommended)

```bash
cd helm/
./publish.sh
```

This will:
1. Validate your chart
2. Package the chart as a `.tgz` file
3. Generate `index.yaml` for the repository
4. Display next steps

### Manual Setup

```bash
cd helm/

# Create repository directory
mkdir -p helm-repo

# Package the chart
helm package esddns-operator -d helm-repo

# Generate index
helm repo index helm-repo \
  --url https://sqe.github.io/esddns/helm-repo
```

## Step 3: Push to GitHub

### Option A: Use gh-pages Branch (Recommended)

```bash
# Create a new branch for GitHub Pages
git checkout --orphan gh-pages

# Clear the branch
git reset --hard
git clean -fd

# Create directory structure for multiple documentation paths
mkdir -p helm-repo docs

# Copy helm-repo contents
cp -r helm/helm-repo/* helm-repo/

# If you have Sphinx documentation, copy it too
# cp -r path/to/sphinx/build/html/* docs/

# Commit and push
git add .
git commit -m "Add Helm repository and documentation structure"
git push -u origin gh-pages
```

### Option B: Keep Everything on main Branch

```bash
git add helm/helm-repo/
git commit -m "Release operator Helm chart v1.0.0"
git push origin main
```

## Step 4: Enable GitHub Pages

### Setup for Multi-Path Serving (Recommended)

If serving both Helm charts and Sphinx documentation:

1. Go to your repository settings: `https://github.com/YOUR_ORG/YOUR_REPO`
2. Navigate to **Settings** → **Pages**
3. Under "Build and deployment":
   - **Source**: Select "Deploy from a branch"
   - **Branch**: Select `gh-pages`
   - **Folder**: Select `/` (root)
4. Click **Save**

This configuration serves both paths:
- `https://YOUR_ORG.github.io/YOUR_REPO/helm-repo/` (Helm charts)
- `https://YOUR_ORG.github.io/YOUR_REPO/docs/` (Python/Sphinx documentation)

### Setup for Helm-Only (Simple)

If only serving Helm charts:

1. Go to your repository settings
2. Navigate to **Settings** → **Pages**
3. Under "Build and deployment":
   - **Source**: Select "Deploy from a branch"
   - **Branch**: Select `gh-pages` or `main`
   - **Folder**: Select `/helm-repo` (if on main) or `/` (if on gh-pages)
4. Click **Save**

### Verify GitHub Pages

```bash
# Test your Helm repository
curl https://YOUR_ORG.github.io/YOUR_REPO/helm-repo/index.yaml

# For ESDDNS example:
curl https://sqe.github.io/esddns/helm-repo/index.yaml

# Should return your chart listing
```

## Step 5: Register on Artifact Hub

### Create Artifact Hub Account

1. Visit https://artifacthub.io/
2. Click **Sign in** (top right)
3. Select **Sign in with GitHub**
4. Authorize Artifact Hub

### Register Your Helm Repository

1. Click your username (top right)
2. Select **Control Panel**
3. Click **Repositories** in the sidebar
4. Click **Add repository**
5. Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `your-operator-name` |
| **Kind** | `Helm chart` |
| **Repository URL** | `https://YOUR_ORG.github.io/YOUR_REPO/helm-repo` |
| **Authentication** | `Not required` |
| **Official repository** | Leave unchecked |

**Example for ESDDNS**:
| Field | Value |
|-------|-------|
| **Name** | `esddns-operator` |
| **Repository URL** | `https://sqe.github.io/esddns/helm-repo` |

6. Click **Add**

### Wait for Sync

Artifact Hub will:
1. Fetch your repository
2. Parse all charts
3. Index your chart
4. Make it searchable

This typically takes 5-10 minutes.

## Step 6: Verify Publication

### Check Artifact Hub

1. Visit https://artifacthub.io/
2. Search for your operator name (e.g., `esddns-operator`)
3. You should see your chart listed within 5-10 minutes

### Install from Artifact Hub

Users can now install your operator:

```bash
# Generic example
helm repo add your-operator https://YOUR_ORG.github.io/YOUR_REPO/helm-repo
helm repo update

# Install your operator chart
helm install your-operator your-operator/your-operator-chart \
  --namespace your-namespace \
  --create-namespace
```

**Example for ESDDNS**:
```bash
helm repo add esddns https://sqe.github.io/esddns/helm-repo
helm repo update

helm install esddns-operator esddns/esddns-operator \
  --namespace esddns \
  --create-namespace \
  --set gandi.apiKey=YOUR_KEY \
  --set global.domain=yourdomain.com
```

## Updating Your Chart

### For Version Updates

1. Update `version` in `Chart.yaml`
2. Update `appVersion` if needed
3. Add entry to `CHANGELOG.md`
4. Package and push:

```bash
helm package helm/esddns-operator -d helm/helm-repo
helm repo index helm/helm-repo
git add helm/helm-repo/
git commit -m "Release esddns-operator Helm chart vX.Y.Z"
git push origin main
```

5. Artifact Hub will automatically re-index within 15 minutes

### For Metadata Updates

Edit `Chart.yaml` annotations:

```yaml
annotations:
  artifacthub.io/changes: |
    - kind: added
      description: New feature description
    - kind: fixed
      description: Bug fix description
  artifacthub.io/containsSecurityUpdates: "false"
  artifacthub.io/prerelease: "false"
```

## Troubleshooting

### Chart Not Appearing

**Problem**: Chart doesn't show up after 15 minutes

**Solutions**:
1. Verify GitHub Pages is enabled: Check Settings → Pages
2. Verify repository URL is correct
3. Check Artifact Hub error logs: Go to your Control Panel → Repository
4. Manually trigger sync: In Control Panel, click the sync button

### Repository URL Issues

**Problem**: "Repository URL is invalid"

**Solutions**:
1. Ensure GitHub Pages is properly configured
2. Test URL manually:
   ```bash
   curl https://sqe.github.io/esddns/helm-repo/index.yaml
   ```
3. Verify `index.yaml` exists and is valid

### Chart Installation Issues

**Problem**: `helm install` fails with "chart not found"

**Solutions**:
1. Verify repository is added:
   ```bash
   helm repo list
   helm repo update
   ```
2. Try searching:
   ```bash
   helm search repo esddns
   ```

## Best Practices

### Chart Quality

- ✅ Always include comprehensive README
- ✅ Keep CHANGELOG updated
- ✅ Use semantic versioning
- ✅ Provide example values files
- ✅ Include security context recommendations

### Documentation

- ✅ Document all configuration options
- ✅ Provide troubleshooting guide
- ✅ Include upgrade/downgrade instructions
- ✅ Add examples for common scenarios

### Repository Maintenance

- ✅ Keep chart versions in sync with app versions
- ✅ Test changes before pushing
- ✅ Review Artifact Hub feedback
- ✅ Respond to user issues

## Additional Resources

- **Helm Chart Repository Guide**: https://helm.sh/docs/topics/chart_repository/
- **Helm Best Practices**: https://helm.sh/docs/chart_best_practices/
- **Artifact Hub Documentation**: https://artifacthub.io/docs/
- **Artifact Hub Helm Repository Guide**: https://artifacthub.io/docs/topics/repositories/helm-charts/
- **Kubernetes Operator Pattern**: https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
- **Kubernetes Security**: https://kubernetes.io/docs/concepts/security/

## Support

For issues related to:
- **Helm chart**: Open issue in GitHub repository
- **Artifact Hub publication**: See Artifact Hub docs
- **Kubernetes deployment**: Check cluster logs and events

---

## What's Next?

After publication, your operator becomes discoverable to thousands of Kubernetes users worldwide. They can:

1. **Find your operator** on Artifact Hub's searchable registry
2. **Review your documentation** and security posture
3. **Install with one command** using Helm
4. **Stay updated** as you release new versions

Monitor your operator's adoption through Artifact Hub analytics and engage with your growing community.
