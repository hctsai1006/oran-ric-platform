# ric-deploy-j

Use this command to deploy the OSC Near-RT RIC **release-j** using the helper scripts in this repo.

When this command is invoked, you should:

1. Confirm with the user that:
   - It is okay to install / update Kubernetes, Helm, and Docker on this host using the `ric-dep` scripts.
   - Any important workloads on the current cluster have been saved.

2. Optionally re-run the environment check:

   ```bash
   ./scripts/bootstrap.sh
   ```

3. Deploy the J-release RIC:

   ```bash
   ./scripts/deploy_ric_j.sh
   ```

4. Stream key parts of the output back to the user so they can see progress (k8s/Helm install, chartmuseum/common template setup, RIC install).

5. After the script finishes, verify the deployment with:

   ```bash
   kubectl get pods -n ricplt
   kubectl get pods -n ricinfra || true
   kubectl get pods -n ricxapp || true
   ```

   Summarise:
   - How many pods are Running / Completed / Pending / in ImagePullBackOff.
   - Any obvious issues.

6. If failures occur, prefer targeted debugging:
   - Use `helm list -n ricplt` and `kubectl describe pod` / `kubectl logs` on failing pods.
   - Suggest minimal changes to the recipe or environment instead of reinstalling everything.

7. Clearly mark the final state (success / partial / failed) and propose the next action: health check, xApp onboarding, or cleanup.
