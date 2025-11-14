# ric-init-lab

Use this command to understand the current state of the Near-RT RIC J-release lab and choose the right next steps.

When this command is invoked, you should:

1. Read `README.md`, `CLAUDE.md`, and `docs/near-rt-ric-j-release-quickstart.md` to refresh context.
2. Run a **non-destructive** environment check:

   ```bash
   ./scripts/bootstrap.sh
   ```

3. From the script output, summarise for the user:

   - Host OS / kernel.
   - docker / kubectl / helm versions (or missing tools).
   - Current Kubernetes context and nodes.
   - Whether `work/j_release/ric-dep` already exists.

4. Classify the situation:

   - **Fresh host** – no k8s cluster, no `ric-dep`.
   - **Cluster only** – k8s is present but RIC not installed.
   - **Existing RIC** – pods already running in `ricplt` and related namespaces.

5. Propose a short plan (3–6 steps) for what to do next, e.g.:

   - Install prerequisites → deploy J-release.
   - Just verify and run health checks.
   - Clean up and re-deploy if the user asks.

6. Ask for explicit confirmation before running any script that may install packages or modify the cluster.
