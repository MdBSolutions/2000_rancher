"""Validate real Helm output and the contracts across provisioning repositories."""
import os
import re
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def docs(path):
    return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]


class VaultBootstrap(unittest.TestCase):
    def test_render_requires_vso_secret_without_plaintext_or_helm_secret(self):
        command = [os.environ.get("HELM", "helm"), "template", "rancher"]
        chart = os.environ.get("RANCHER_CHART")
        command += [chart] if chart else ["rancher", "--repo", "https://releases.rancher.com/server-charts/stable", "--version", "2.11.3"]
        command += ["--namespace", "cattle-system", "--kube-version", "1.32.0", "-f", str(ROOT / "helm/values.yaml")]
        rendered = list(yaml.safe_load_all(subprocess.check_output(command, text=True)))
        deployment = next(d for d in rendered if d and d["kind"] == "Deployment")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        password = [e for e in container["env"] if e["name"] == "CATTLE_BOOTSTRAP_PASSWORD"]
        self.assertEqual(len(password), 1)
        self.assertNotIn("value", password[0])
        ref = password[0]["valueFrom"]["secretKeyRef"]
        self.assertFalse(ref["optional"])
        secret = next(d for d in docs(ROOT / "k8s/vault-bootstrap.yaml") if d["kind"] == "VaultStaticSecret")
        self.assertEqual(ref["name"], secret["spec"]["destination"]["name"])
        self.assertEqual(ref["key"], "password")
        self.assertFalse(any(d and d["kind"] == "Secret" for d in rendered))
        self.assertFalse(any(d and d["kind"] in ("Ingress", "Issuer", "Certificate") for d in rendered))

    def test_vso_identity_and_permissions(self):
        resources = docs(ROOT / "k8s/vault-bootstrap.yaml")
        auth = next(d for d in resources if d["kind"] == "VaultAuth")
        sa = next(d for d in resources if d["kind"] == "ServiceAccount")
        binding = next(d for d in resources if d["kind"] == "ClusterRoleBinding")
        self.assertEqual(auth["spec"]["kubernetes"]["serviceAccount"], sa["metadata"]["name"])
        self.assertEqual(binding["subjects"], [{"kind": "ServiceAccount", "name": sa["metadata"]["name"], "namespace": "cattle-system"}])
        self.assertEqual(binding["roleRef"]["name"], "system:auth-delegator")
        self.assertEqual(set(auth["spec"]["kubernetes"]["audiences"]), {"vault", "https://kubernetes.default.svc.cluster.local"})
        self.assertEqual(auth["spec"]["vaultConnectionRef"], "argocd/vault-argocd")
        k = docs(ROOT / "k8s/kustomization.yaml")[0]
        self.assertIn("vault-bootstrap.yaml", k["resources"])

    def test_producer_consumer_and_cold_start_permissions(self):
        if not os.environ.get("MANAGEMENT_WORKSPACE"):
            self.skipTest("Set MANAGEMENT_WORKSPACE for companion repository checks")
        workspace = Path(os.environ["MANAGEMENT_WORKSPACE"])
        seed = docs(workspace / "3.vault_cluster/roles/vault_policies/vars/main.yml")[0]
        secret = next(d for d in docs(ROOT / "k8s/vault-bootstrap.yaml") if d["kind"] == "VaultStaticSecret")["spec"]
        path = secret["mount"] + "/" + secret["path"]
        generated = next(d for d in seed["vault_generated_password_catalog"] if d["path"] == path)
        fields = next(d["fields"] for d in seed["vault_seed_catalog"] if d["path"] == path)
        self.assertEqual(fields["username"], "admin")
        self.assertEqual(generated["key"], "password")
        self.assertIn(generated["var"], fields["password"])
        policy = (workspace / "2000_vault_config/management/policies/rancher-vso-read.hcl").read_text()
        self.assertEqual(re.findall(r'path "([^"]+)"', policy), ["secret/data/" + secret["path"]])
        self.assertEqual(re.findall(r'capabilities = \[([^]]+)\]', policy), ['"read"'])
        cold = (workspace / "5.k8s_bootstrap/roles/vault_kubernetes_auth/files/tofu-vault-config.hcl").read_text()
        recovery = (workspace / "2000_vault_config/management/bootstrap/tofu-vault-config.hcl").read_text()
        self.assertEqual(cold, recovery)
        for endpoint in ("sys/policies/acl/rancher-vso-read", "auth/kubernetes/role/rancher-vso-read"):
            self.assertIn('path "' + endpoint + '"', cold)
        app = docs(workspace / "7.environment-config/argocd/application-rancher.yaml")[0]
        source = next(s for s in app["spec"]["sources"] if s.get("ref") == "values")
        self.assertEqual(source["path"], "k8s")


if __name__ == "__main__":
    unittest.main()
