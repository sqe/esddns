# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-13

### Added
- Initial release of ESDDNS Operator Helm chart
- DaemonSet for node IP monitoring
- Deployment for Flask web service
- LoadBalancer Service for external access
- ConfigMap for DNS configuration
- Secret management for Gandi API credentials
- RBAC with minimal permissions
- Prometheus ServiceMonitor for metrics scraping
- PrometheusRules for alerting
- Pod Disruption Budget for high availability
- Health checks (liveness and readiness probes)
- Environment-specific values (production/development)
- Comprehensive documentation and examples
- Support for multiple cloud providers (AWS, GCP, Azure)
- On-premises Kubernetes support

### Features
- Automatic IP monitoring on all cluster nodes
- Seamless DNS updates without manual intervention
- Cloud-agnostic deployment
- Full Prometheus integration
- Pre-configured alert rules
- Security context and RBAC controls
- Pod anti-affinity for better distribution
- Resource limits and requests
- Logging level control
- TTL configuration
- Multiple service types (LoadBalancer, NodePort, ClusterIP)

### Configuration Options
- Global domain and record settings
- Gandi API key management
- Image repository and tag customization
- Resource allocation
- Monitoring enable/disable
- Environment selection (production/development)
- Health check tuning
- Affinity and tolerations
- Pod disruption budgets

## Future Plans

- [ ] Add Helm chart tests
- [ ] Support for multiple DNS providers (Route53, Cloudflare, etc.)
- [ ] Helm chart templating for multiple environments
- [ ] Automatic image build and push to registries
- [ ] Security scanning in CI/CD
- [ ] Performance benchmarking

## Contributing

See the main ESDDNS repository for contribution guidelines.
