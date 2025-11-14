---
name: oran-ric-j-bootstrap
version: 0.1.0
description: >
  Skill for bootstrapping an O-RAN SC Near-RT RIC J-release lab using
  ric-plt-ric-dep on Kubernetes, driven by Claude Code + MCP.
tags:
  - oran
  - ric
  - 5g
  - kubernetes
  - devops
---

# O-RAN RIC J Bootstrap Skill

This Skill teaches you how to stand up an **O-RAN SC Near-RT RIC J-release**
testbed on Kubernetes using the helper repo **oran-ric-j-lab**.

You should use this Skill when the user says things like:

- “幫我快速布建一個 Near-RT RIC J 版本的實驗環境。”
- “Use the RIC J bootstrap Skill to bring up a local RIC cluster.”
- “Fix my broken RIC J deployment and tell me what happened.”

---

## 1. Preconditions and assumptions

Before running any install steps:

1. Confirm you are inside the **oran-ric-j-lab** project directory.
2. Ensure the user understands this is for **lab / experimental** use only.
3. Check (using filesystem + shell tools if available):

   - A reasonably modern Linux host (e.g. Ubuntu 22.04).
   - Sufficient resources for a single-node RIC lab
     (≥8 vCPUs, ≥16 GB RAM, ≥120 GB disk).
   - `git`, `docker` (or compatible container runtime), `kubectl`, and `helm`
     are available in `PATH`.

If any of these are missing, pause and draft exact installation commands, then
ask the user for confirmation before running them.

---

## 2. Files to read first

Whenever this Skill is invoked, you should first skim these files:

- `README.md` — high‑level overview and expected workflow.
- `scripts/bootstrap-ric-j.sh` — main bootstrap script, to understand its steps.
- `docs/j-release-quick-notes.md` — short description of the J‑release flow.
- `docs/g-release-deployment-guide.md` — historic G‑release guide for context.

Use the filesystem MCP server (or equivalent) to open these files instead of
guessing.

---

## 3. Normal bootstrap flow

When the user wants a **fresh RIC J lab**:

1. Summarise the plan in a few bullet points:

   - Clone (or reuse) `ric-plt-ric-dep` with `j-release` branch.
   - Install Kubernetes + Helm if needed (single-node lab).
   - Install common Helm templates.
   - Apply the `example_recipe_oran_j_release.yaml` recipe.
   - Verify pods in RIC namespaces.

2. Inspect `scripts/bootstrap-ric-j.sh` and show its high‑level phases to the
   user, so they understand what will happen.

3. Run the script step‑by‑step, capturing output:

   - Prefer invoking the script via a shell / bash MCP tool, not by rewriting
     it each time.
   - After each major step, summarise success/failure and, if needed, inspect
     cluster state via the Kubernetes MCP server (pods, events, logs).

4. At the end, run:

   - `kubectl get pods -A`
   - `kubectl get pods -n ricplt`
   - `kubectl get pods -n ricxapp` (or other recipe namespaces)

   and summarise whether the RIC is healthy.

---

## 4. Failure handling

If anything fails:

1. Avoid deleting or recreating resources blindly.
2. Use Kubernetes MCP tools to:

   - Inspect failing pods (`kubectl describe pod`, `kubectl logs`).
   - Check events in the RIC namespaces.
   - Confirm image pull success and readiness probes.

3. Propose **minimal, targeted** fixes, for example:

   - Re‑running a failed step of `bootstrap-ric-j.sh`.
   - Editing a values file or recipe YAML (if clearly misconfigured).
   - Adjusting node resources (e.g., memory limits).

Always show the user the concrete changes you plan to make before applying
them.

---

## 5. Advanced usage

When the user is more advanced, this Skill can also help to:

- Compare **G vs J** deployment flows based on the two guides in `docs/`.
- Draft new Helm values or recipes for custom xApps.
- Integrate RIC deployment into CI/CD or GitOps workflows (Nephio, Argo CD,
  etc.) — but only after discussing the desired architecture with the user.

When in doubt, ask short, precise clarifying questions rather than assuming
their environment.

---

## 6. Tone & language

- Default to **English** for code, commands, and identifiers.
- You may answer in **Traditional Chinese** when explaining concepts, if the
  user writes in Chinese.
- Be concise but precise; this Skill is for an expert user who values correctness
  over hand‑waving.
