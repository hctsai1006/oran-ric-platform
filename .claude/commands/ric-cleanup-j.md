# ric-cleanup-j

Use this command to safely tear down the Near-RT RIC lab for **release-j**.

When this command is invoked, you should:

1. Confirm with the user that it is safe to remove the Near-RT RIC deployment, including pods and Helm releases in `ricplt`, `ricinfra`, and `ricxapp`.

2. Run the cleanup script from the `ric-dep` checkout (if present):

   ```bash
   ./scripts/cleanup_ric_j.sh
   ```

3. After it finishes, validate that the RIC has been removed:

   ```bash
   kubectl get ns
   kubectl get pods -A
   ```

   Check that:
   - RIC namespaces are gone or empty.
   - No RIC pods are left in `Error` / `Terminating` state.

4. If anything remains, investigate with `kubectl describe` and propose minimal additional cleanup commands (for example, deleting a stuck namespace or Helm release).

5. Summarise what was removed and what the system state looks like now so the user knows it is safe to re-deploy or repurpose the cluster.
