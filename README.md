# Rancher management access

Argo CD deploys Rancher chart 2.11.3 using helm/values.yaml, through the Application in 7.environment-config.

## First login from Vault

Phase 3 generates a 12-character alphanumeric password in
`secret/management/rancher/admin` using Vault's existing `alnum12_ui` policy.
The username is `admin`. A non-empty password is preserved on repeated seed runs.
No password value is stored in Git or OpenTofu state.

The Rancher Application must load both `helm/values.yaml` and `k8s/` from this
repository. VSO authenticates as `rancher-vault-auth` in `cattle-system`, using
the read-only Vault role `rancher-vso-read`. It reuses the platform's
`argocd/vault-argocd` connection and its rotated CA bundle; this shares TLS trust,
not the Argo CD authentication identity or its secret permissions.

VSO creates `cattle-system/rancher-bootstrap-password`. The Deployment reads its
mandatory `password` key as `CATTLE_BOOTSTRAP_PASSWORD`. If synchronization is
delayed, Kubernetes holds the container until the key exists, preventing a
different randomly generated Rancher password. Helm's `bootstrapPassword` stays
empty to avoid two owners of the Secret. No rollout restart is requested when
the Vault value changes: this is initial provisioning, not password rotation.

For a clean rebuild, merge the companion changes in `3.vault_cluster`,
`5.k8s_bootstrap`, `2000_vault_config`, and `7.environment-config` before running
the normal installation phases. Phase 5 grants OpenTofu permission to create
the Rancher reader role/policy; the Vault configuration Job creates them before
VSO can read the password. No manual password input is required.

Find the password in the Vault UI under `secret > management > rancher > admin`,
key `password`. Use it on Rancher's welcome screen, or log in as `admin` if the
username field is shown. Complete Rancher's first-login setup. If you choose a
different password during setup or later, update your stored credential too;
editing Vault alone does not change an existing Rancher account.

After installation, verify on master1 without displaying credentials:

```bash
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf -n cattle-system wait --for=condition=SecretSynced=True vaultstaticsecret/rancher-bootstrap --timeout=600s
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf -n cattle-system rollout status deployment/rancher --timeout=900s
```

Tests: `python -m unittest discover -s tests -v` (PyYAML and Helm required).
Set `RANCHER_CHART` to an unpacked chart 2.11.3 for offline rendering and
`MANAGEMENT_WORKSPACE` to sibling repositories for the cross-repository checks.

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
