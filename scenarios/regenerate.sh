#!/usr/bin/env bash
# =============================================================================
# Regenerate scenario golden run records + the derived DAG overlay from REAL
# scenario runs.  Run this after changing code or a manifest's fixtures/answers
# so the golden snapshots, the DAG node content and (on next recording) the GIF
# all reflect the new real behaviour.
#
#   scenarios/regenerate.sh                # all scenarios
#   scenarios/regenerate.sh US-2b.1        # one scenario
#
# Requires the runnable stack: the hledger_preprocessor conda env active (or its
# python on PATH), hledger + hledger-flow on PATH, and tui_labeller + pexpect
# installed.  Each scenario spawns the real TUI (~1 min).
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export MPLBACKEND="${MPLBACKEND:-Agg}"
export HLEDGER_PREPROCESSOR_HEADLESS=1
export PATH="$HOME/.local/bin:$PATH"

scenarios=("$@")
if [ ${#scenarios[@]} -eq 0 ]; then
    mapfile -t scenarios < <(
        python3 -c "from scenarios.harness.manifest import all_manifests; \
print('\n'.join(m.id for m in all_manifests()))"
    )
fi

for s in "${scenarios[@]}"; do
    echo ">>> Running scenario $s ..."
    python3 -m scenarios.harness.run_scenario "$s" --update
done

echo ">>> Deriving DAG overlay ..."
python3 -m scenarios.harness.derive_dag

echo "Done. Review + commit scenarios/_runs/*.run.json and"
echo "user_stories/dag/userstory_dag_derived.yaml"
