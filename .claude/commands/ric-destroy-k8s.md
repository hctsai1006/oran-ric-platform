# /ric-destroy

Help the user safely run `bin/destroy_ric.sh` to tear down the Near-RT RIC lab.

Steps:

1. Confirm the user really wants to remove the lab and understands the impact.
2. Summarize what `bin/destroy_ric.sh` does (calls upstream `uninstall` in `ric-plt-ric-dep/bin`).
3. Provide the exact shell command for the user to run.
4. After teardown, suggest checking:
   - RIC-related namespaces
   - Remaining pods
5. If desired, help clean up the working directory (`$HOME/ric-j-lab`) — only after explicit confirmation.
