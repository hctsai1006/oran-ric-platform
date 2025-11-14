---
name: near-rt-ric-ops
version: 0.1.0
summary: Operate an OSC Near-RT RIC (J release) lab deployment on Kubernetes.
---

## What this skill is for

This skill teaches you how to:

- Inspect the health of an OSC Near-RT RIC J-release deployment
- Use `mcp-kubernetes-server` to debug RIC pods, services and CRDs
- Suggest concrete next steps when something is wrong

The default RIC namespace is:

- `ricplt` – Near-RT RIC platform components

## Assumed tools

The user has configured the following MCP servers:

- `kubernetes` (mcp-kubernetes-server)
- optionally `docker` and `git`

Prefer MCP tools over raw shell when:

- Listing pods / deployments / statefulsets
- Fetching logs
- Inspecting events

## Core behaviours

When the user asks about “RIC status” or “RIC health”:

1. Use `kubernetes` tools to gather:
   - `k8s_get` for Deployments and StatefulSets in `ricplt`
   - `k8s_top_pods` in `ricplt`
   - `k8s_events` scoped to `ricplt`
2. Use `bash deploy/scripts/check_ric_status.sh` as a quick summary
   if the environment allows shell commands.
3. Present a short structured summary:
   - Healthy components
   - Degraded components
   - Suspicious events (CrashLoopBackOff, ImagePullBackOff, etc.)
4. Propose next debugging actions, for example:
   - “Inspect logs for pod X with k8s_logs”
   - “Describe Deployment Y and check image / resources”.

When the user wants to **compare G vs J release**:

- Ask the user for any G-release notes they have in this repo.
- Highlight differences in:
  - Kubernetes version assumptions
  - Helm chart layouts / namespaces
  - Required CRDs or operators.

## Tone & style

- Be concise and operational.
- Default to bullet lists and numbered steps.
- Call out unsafe or potentially destructive actions clearly.
