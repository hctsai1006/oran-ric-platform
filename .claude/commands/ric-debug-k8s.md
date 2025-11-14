# /ric-debug-k8s

Assist the user in debugging failing Kubernetes components related to the RIC lab.

When invoked:

1. Ask the user which namespace / pod / component they care about, or infer from prior errors.
2. Use Kubernetes MCP tools to:
   - `get pods` and `describe` the failing pods
   - Inspect recent logs
3. Translate technical errors into concise explanations and likely causes.
4. Propose **one or two** next actions (e.g., restart a pod, adjust a config map), but do not perform them automatically.

Always keep the user in control of changes.
