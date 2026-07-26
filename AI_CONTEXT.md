# AI_CONTEXT.md - 2000_rancher

## Doel

Rancher-dashboard als management-tool voor multi-cluster orchestration. Beheerd
door ArgoCD in `6.k8s_platform` op het management-cluster.

## Samenwerkende repositories

- **`6.k8s_platform`** — Deployment via ApplicationSet + ArgoCD
- **`1.server_bootstrap`...`4.server_infra`** — Management-cluster onderliggende infra
- **`5.k8s_bootstrap`** — Cluster opzetting (kubeadm)

## Technische stack

- **Orkestratie**: Kustomize (Helm plugin) + ArgoCD
- **Chart**: Rancher stable v2.10.0
- **TLS**: Self-signed (Rancher genereert automatisch)
- **Storage**: PersistentVolumeClaim (10Gi) — hostPath tot echte storage beschikbaar
- **Ingress**: Nginx via `6.k8s_platform/base/ingress`
- **Namespace**: `cattle-system` (Rancher default)

## Conventies

1. **Geen secrets in de repo** — Rancher genereert admin-password zelf
2. **Helm values centraal** — Alle config via `helm/values.yaml`
3. **Idempotent manifesten** — kubectl apply -f meermaals is veilig
4. **ASCII only** — Geen speciale Unicode-tekens
5. **Kustomize Helm plugin** — Build altijd met `--enable-helm`

## Kustomize build

```bash
kustomize build --enable-helm overlays/production/
```

Dit genereert de volledige manifest:
- Namespace cattle-system
- Service account + RBAC
- Deployment + Pod
- Service (ClusterIP of LoadBalancer naar toekomst)
- PersistentVolumeClaim (storage)
- Ingress regel (via overlays/production/ingress.yaml)
- ConfigMap/Secret voor Rancher-config

## Workflow

1. Clone repo en checkout `develop`
2. Maak feature branch: `git checkout -b feature/mijn-feature origin/main`
3. Bewerk `helm/values.yaml` en/of `overlays/production/*`
4. Test: `kustomize build --enable-helm overlays/production/ | kubectl apply -f - --dry-run=client`
5. Push naar develop: `git push origin feature/mijn-feature`
6. PR develop -> main (gebruiker mergt)
7. ArgoCD sync't automatisch (~ 30 sec)

## Troubleshooting

- **Rancher pod crashed**: Check logs: `kubectl logs -n cattle-system -l app=rancher`
- **PVC pending**: `kubectl describe pvc -n cattle-system`
- **Ingress no IP**: Wacht tot MetalLB buiten IP assigned (1-2 min)
