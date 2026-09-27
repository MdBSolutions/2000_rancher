# Rancher management access

Argo CD deploys Rancher chart 2.11.3 using helm/values.yaml, through the Application in 7.environment-config.

The platform has no ingress controller. Rancher therefore exposes only HTTPS through the chart's NodePort Service (service port 443 to container port 444). Kubernetes allocates the NodePort; it is stable while the Service exists.

Prerequisite: phase 6 must apply kube-proxy nodePortAddresses: [10.0.0.0/24], restricting NodePorts to management WireGuard addresses. Do not use public node addresses.

After merge and Argo CD sync, pruning removes the unused Ingress. On master1, run:

```bash
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf -n cattle-system rollout status deployment/rancher --timeout=300s
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf -n cattle-system get service rancher
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf -n cattle-system get service rancher -o jsonpath='{.spec.ports[?(@.port==443)].nodePort}{"\n"}'
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf -n cattle-system get ingress
```

Resolve rancher.internal to 10.0.0.1 on the management client using internal DNS or hosts. Connect over WireGuard to https://rancher.internal:<allocated-nodeport>. Verify the presented certificate and establish trust in the appropriate CA before login. This change does not provision public certificates or DNS. The ingress.tls.source: secret setting prevents the chart from creating a cert-manager Issuer, even though ingress.enabled is false. No ingress TLS secret is mounted by this configuration. The direct HTTPS listener's certificate and client trust must be checked after deployment; no public certificate or CA provisioning is supplied here.

Use the complete reachable URL including NodePort during initial setup. For an existing installation, review the configured server URL and agent reachability before changing that setting.

Validation: Helm 3.17.3 rendered chart 2.11.3 for Kubernetes 1.32.0 successfully. The output has an HTTPS-only NodePort Service and no Ingress, Issuer, ClusterIssuer, Certificate or CertificateRequest. Live TLS, browser login and agent connectivity require post-deployment validation.

```bash
helm template rancher rancher --repo https://releases.rancher.com/server-charts/stable --version 2.11.3 --namespace cattle-system --kube-version 1.32.0 -f helm/values.yaml
```
