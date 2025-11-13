# Publishing ESDDNS Operator to Artifact Hub

This guide walks you through publishing the ESDDNS Operator Helm chart to Artifact Hub, making it discoverable and installable for the Kubernetes community.

## What is Artifact Hub?

Artifact Hub (https://artifacthub.io) is a web-based application that helps users find, install, and publish Kubernetes packages (Helm charts, operators, etc.).

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

### Create Helm Repository Branch

```bash
cd helm/

# Create a new branch for Helm repository (optional)
git checkout --orphan gh-pages

# Clear the branch
git reset --hard
git clean -fd

# Copy helm-repo contents
cp -r helm-repo/* .

# Commit and push
git add .
git commit -m "Initial Helm repository structure"
git push -u origin gh-pages
```

Or keep it on main branch:

```bash
git add helm/helm-repo/
git commit -m "Release esddns-operator Helm chart v1.0.0"
git push origin main
```

## Step 4: Enable GitHub Pages

1. Go to your repository: https://github.com/sqe/esddns
2. Navigate to **Settings** → **Pages**
3. Under "Build and deployment":
   - **Source**: Select "Deploy from a branch"
   - **Branch**: Select `gh-pages` (or `main`)
   - **Folder**: Select `/helm-repo` (if on main) or `/` (if on gh-pages)
4. Click **Save**

Wait for GitHub Actions to complete. Your Helm repository is now available at:
```
https://sqe.github.io/esddns/helm-repo
```

### Verify GitHub Pages

```bash
curl https://sqe.github.io/esddns/helm-repo/index.yaml

# Should show your chart listing
```

## Step 5: Register on Artifact Hub

### Create Artifact Hub Account

1. Visit https://artifacthub.io
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
| **Name** | `esddns-operator` |
| **Kind** | `Helm chart` |
| **Repository URL** | `https://sqe.github.io/esddns/helm-repo` |
| **Authentication** | `Not required` |
| **Official repository** | Leave unchecked |

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

1. Visit https://artifacthub.io
2. Search for: `esddns-operator`
3. You should see your chart listed

### Install from Artifact Hub

Users can now install your chart:

```bash
# Add repository
helm repo add esddns https://sqe.github.io/esddns/helm-repo
helm repo update

# Install chart
helm install esddns-operator esddns/esddns-operator \
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

- **Helm Documentation**: https://helm.sh/docs/
- **Artifact Hub Documentation**: https://artifacthub.io/docs/
- **Chart Best Practices**: https://helm.sh/docs/chart_best_practices/
- **Kubernetes Security**: https://kubernetes.io/docs/concepts/security/

## Support

For issues related to:
- **Helm chart**: Open issue in GitHub repository
- **Artifact Hub publication**: See Artifact Hub docs
- **Kubernetes deployment**: Check cluster logs and events

---

**Next**: After publication, users can discover and install your chart from Artifact Hub!
