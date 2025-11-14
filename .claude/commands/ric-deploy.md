# /ric-deploy

Goal: help the user safely run `bin/bootstrap_ric_j.sh` to deploy the OSC Near-RT RIC J-release.

When invoked:

1. Re-state what `bin/bootstrap_ric_j.sh` will do at a high level.
2. Confirm the user is on the correct host/VM and understands that:
   - Kubernetes, Docker and Helm will be installed or modified.
   - New namespaces and pods will be created.
3. Walk through the script in phases:
   - Clone/checkout `ric-plt-ric-dep` (branch `j-release`).
   - Run `install_k8s_and_helm.sh`.
   - Run `install_common_templates_to_helm.sh`.
   - Run `install -f RECIPE_EXAMPLE/example_recipe_oran_j_release.yaml`.
4. After each phase, suggest validation commands the user can run (e.g., `kubectl get nodes`, `kubectl get pods -A`).

Prefer giving shell snippets for the user to execute instead of executing them directly via tools.
