# CLAUDE.md - 2000_rancher

## Plek in de repositoryhiërarchie

Dit is een appcluster repo (`2000_*`): Rancher dashboard voor multi-cluster management.

| # | Repo | Wat het doet |
|---|---|---|
| Laag 1 | `1.server_bootstrap` ... `4.server_infra` | Management-cluster infra (vaste 6 fases) |
| Laag 2 | `5.k8s_bootstrap` + `6.k8s_platform` | Management-cluster opzetten (fase 5-6) |
| Laag 2 | `2000_rancher` | **Deze repo**: Rancher management dashboard (appcluster) |
| Laag 3 | `3000_*` | Applicaties met eigendomslogica |

Rancher draait in het management-cluster (`master1` + `worker1`) en beheerd
TOEKOMSTIGE clusters. Dit is geen production-applicatie, maar management-tooling
die via `6.k8s_platform` wordt uitgerold.

## Doel

Rancher-dashboard deployen voor multi-cluster management via Helm. Self-signed
TLS, persistent storage (10Gi), 1 replica voor nu. Beheerd door ArgoCD in
`6.k8s_platform`.

## Deployment

Rancher wordt via **ArgoCD** uit `6.k8s_platform` automatisch gesynchroniseerd:

1. `6.k8s_platform` bevat `base/argocd` met een ApplicationSet
2. De ApplicationSet detecteert deze repo in GitHub
3. Kustomize bouwt de manifest
4. ArgoCD past toe op het cluster

### Handmatige deployment (vóór ArgoCD)

```bash
# Build and apply
kustomize build --enable-helm overlays/production/ | kubectl apply -f -

# Verify
kubectl get deployment -n cattle-system
kubectl get service -n cattle-system
```

### Helm Chart
- Chart: `rancher` (Rancher Helm repository)
- Version: `v2.10.0` (stabiel)
- Namespace: `cattle-system`
- TLS: Self-signed (zelf gerenderd door Helm)
- Storage: 10Gi PersistentVolumeClaim
- Replicas: 1

### Staging vs Production
- `overlays/production/`: Replicas=1, hostname=rancher.internal
- Per overlays kunnen replica's en hostname naar smaak worden aangepast

## Structuur

```
2000_rancher/
  helm/
    Chart.yaml         # Helm chart metadata
    values.yaml        # Helm values (image, replicas, storage, TLS)
  namespace.yaml       # cattle-system namespace
  kustomization.yaml   # Root kustomization (Helm plugin)
  overlays/
    production/
      kustomization.yaml
      ingress.yaml     # Ingress rule voor rancher.internal
  .claude/settings.json # Auto-push hook
```

## Git workflow

- NOOIT direct naar `main` pushen
- Altijd een feature branch aanmaken en daarop pushen
- Mergen naar main doet de gebruiker zelf via een PR
- Voer ALTIJD eerst `git fetch origin` uit voordat je een branch aanmaakt
- Maak branches aan vanaf `origin/main`: `git fetch origin && git checkout -b naam-branch origin/main`
- Controleer ALTIJD eerst met `git branch -a` of er al een open branch bestaat

## Technische eisen

- Tool: Kustomize met Helm support (`kustomize build --enable-helm`)
- Helm Chart: Rancher stable repository
- TLS: Self-signed (standaard Rancher setup)
- Storage: Persistent 10Gi (hostPath in dev, echte storage in prod)
- Namespace: `cattle-system` (Rancher default)
- Bereikbaarheid: Intern via WireGuard op rancher.internal

## Richtlijnen

- Alle manifesten zijn idempotent
- Gebruik ASCII in alle bestanden
- Geen secrets in de repo (Rancher genereert ze zelf)
- Helm values altijd via `values.yaml`, geen hardcodes in kustomization
