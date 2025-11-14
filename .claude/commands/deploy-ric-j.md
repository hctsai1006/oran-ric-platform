# /deploy-ric-j – Install and verify Near-RT RIC J-release

When the user runs `/deploy-ric-j`, do the following:

1. Explain briefly what you are about to do.
2. Run: `bash deploy/scripts/install_osc_ric_j.sh`
   - Stream the output back to the user.
   - If the command fails, stop and summarize the error.
3. After installation, run:
   - `bash deploy/scripts/check_ric_status.sh`
4. Summarize:
   - Which pods are not Ready
   - Any obvious CrashLoopBackOff or Error states
   - Suggestions for next debugging steps using `mcp-kubernetes-server`.
