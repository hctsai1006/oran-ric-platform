# /ric-status

Use the Kubernetes MCP server (if available) to summarize cluster and RIC status.

Steps:

1. List nodes and report:
   - Ready / NotReady
   - Kubernetes version
2. List pods in all namespaces and highlight:
   - Pods in CrashLoopBackOff / Error / Pending
   - RIC-related namespaces (`ricinfra`, `ricplt`, etc.) and their pod health
3. Provide a short human-readable summary:
   - "Cluster healthy / partially healthy / unhealthy"
   - Which components look problematic
4. Suggest next debugging steps, optionally chaining into `/ric-debug-k8s`.

Avoid making destructive changes during this command.
