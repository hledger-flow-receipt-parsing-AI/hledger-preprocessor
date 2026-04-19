# GIF Coverage-Based Pre-commit Hook — Design & Gaps

## Overview

Replace manually maintained `gif_dependencies.yaml` with automatically generated
coverage traces. Each GIF recording produces a `_coverage.json` listing which `.py`
files were actually executed. The pre-commit hook compares `git diff` against these
traces to detect stale GIFs.

## Architecture

```
Record GIF (generate.sh)
  ├── export COVERAGE_PROCESS_START=gifs/.coveragerc
  ├── asciinema rec ... (passes env to subprocess tree)
  │     └── python demo → pexpect.spawn("hledger_preprocessor --tui-label-receipts")
  │           └── (coverage auto-starts via .pth, writes .coverage.<pid>)
  ├── coverage combine → coverage json → _coverage.json
  └── cleanup /tmp/gif_coverage/

Pre-commit (any sub-repo)
  ├── git diff --cached → changed files
  ├── Read hledger-preprocessor/gifs/*/output/*_coverage.json
  ├── Missing _coverage.json → ERROR (force re-record)
  ├── Intersection with changed files → WARN (stale GIF)
  └── Exit 0 (warn) or 1 (block)
```

## Files to create/modify

1. `hledger-preprocessor/gifs/.coveragerc` — coverage config (parallel=true, source=all sub-packages)
1. `hledger-preprocessor/gifs/automation/install_coverage_pth.py` — installs .pth in conda env
1. `hledger-preprocessor/gifs/scripts/common.sh` — add coverage env vars to recording
1. `hledger-preprocessor/gifs/automation/extract_coverage.py` — .coverage → \_coverage.json
1. `hooks/check-gif-staleness.py` — read \_coverage.json instead of gif_dependencies.yaml
1. `gif_dependencies.yaml` — keep but reduce to NON-Python files only

## Known Gaps & Fixes

### Gap 1: .pth file is a global conda env side-effect

Installing `coverage_autostart.pth` into `$CONDA_PREFIX/lib/pythonX.Y/site-packages/`
makes EVERY Python process in the env call `coverage.process_startup()` on startup.
If `COVERAGE_PROCESS_START` is not set, it's a no-op — but the import still runs.

**Fix:** The `install_coverage_pth.py` script has `--install` and `--uninstall` modes.
The `generate.sh` wrapper installs before recording, uninstalls after. No permanent
side-effect on the conda env.

### Gap 2: Standalone GIFs produce empty coverage

`yaml_typing_gif.py` (1a_setup_config, 1b_add_category, 2b_data_files) only imports
PIL/Pillow — no hledger sub-package code. With `omit = */gifs/automation/*`, the
coverage trace will have zero files.

**Fix:** `_coverage.json` includes a `"type"` field: `"standalone"` or `"config-dependent"`.
The pre-commit hook accepts empty `files_touched` for standalone GIFs without erroring.
Standalone GIFs are still tracked for changes to their own scripts via the reduced
`gif_dependencies.yaml`.

### Gap 3: hledger_plot subprocess env propagation

`show_plots_demo.py` runs:

```python
cmd = f"bash -c 'source .../conda.sh && conda activate hledger_preprocessor && hledger_plot ...'"
```

`COVERAGE_PROCESS_START` must survive bash → conda activate → python. The asciinema
`--env=` flag passes it to the top-level shell, but `bash -c` starts a new shell.

**Fix:** Use `export COVERAGE_PROCESS_START=...` before the asciinema call (not just
in the asciinema --env list). Since child processes inherit exported env vars from the
parent shell, and conda activate doesn't clear arbitrary env vars, this propagates
through the full chain.

### Gap 4: Non-Python files are invisible to coverage

Changes to these won't appear in Python coverage traces:

- `generate.sh`, `common.sh` (shell scripts)
- `gif_config.yaml` (rendering config)
- Receipt images (`gifs/assets/receipts/`)
- YAML config fixtures (`test/fixtures/config_fragments/`)
- `userstory_dag_data.yaml` (DAG definition)

**Fix:** Keep a reduced `gif_dependencies.yaml` for non-Python watch patterns only.
The pre-commit hook checks BOTH sources:

- `_coverage.json` for Python file changes
- `gif_dependencies.yaml` for shell scripts, YAML, images, fixtures

### Gap 5: Initial bootstrap — all coverage files missing

Until every GIF is re-recorded with coverage enabled, all `_coverage.json` files
are missing. The hook would error on every commit.

**Fix:** Add `--bootstrap` flag to the hook. In bootstrap mode, missing coverage
files produce warnings instead of errors. Remove the flag once all 15 GIFs have
been re-recorded once.

### Gap 6: Coverage files must be committed

The `_coverage.json` files need to live in `hledger-preprocessor/gifs/*/output/`
and be committed to git. If you re-record a GIF but forget to commit the coverage
file, the hook won't have updated data.

**Fix:** This is actually self-correcting — if you commit GIF artifacts (`.cast`,
`.mp4`) without the `_coverage.json`, the hook will warn next time. The hook already
checks artifact staleness in hledger-preprocessor commits.

## Conda environment concerns

The `.pth` file approach modifies the conda environment's site-packages. Concerns:

1. **Install/uninstall lifecycle:** The .pth is installed before recording and
   uninstalled after. It does NOT persist. No impact on normal development.

1. **`coverage.process_startup()` overhead:** When `COVERAGE_PROCESS_START` is not
   set, the function is a fast no-op (checks env var, returns immediately). The
   import of `coverage` itself adds ~5ms to Python startup. Negligible.

1. **Concurrent processes:** If you run pytest in another terminal while a GIF is
   recording, the .pth file would be present. But `COVERAGE_PROCESS_START` is only
   set in the recording terminal's env, not globally. pytest would not be affected.

1. **conda activate/deactivate:** The .pth file lives in site-packages, not in
   conda's activation scripts. `conda deactivate` doesn't remove it. This is why
   install/uninstall must be explicit, not tied to conda lifecycle.

## Shell script tracing

Python coverage.py cannot trace shell scripts. Options:

### Option A: Keep shell, track via gif_dependencies.yaml (recommended)

The shell scripts (`generate.sh`, `common.sh`) are thin wrappers — they call
asciinema, ffmpeg, agg, and Python modules. The actual logic is in Python.
Tracking shell changes via static patterns in `gif_dependencies.yaml` is
sufficient and simple.

### Option B: Convert shell to Python

The `generate.sh` scripts could be rewritten as Python modules using `subprocess`
for asciinema/ffmpeg/agg calls. This would make them traceable by coverage.

**However:** asciinema recording requires a real PTY. The current flow is:

```
generate.sh → asciinema rec --command="python -m demo_module"
```

asciinema itself is a Go binary — it can't be traced by Python coverage regardless
of whether the wrapper is shell or Python. The Python demo module inside asciinema
IS traced (via the .pth file).

Converting generate.sh to Python would add complexity without meaningful coverage
gain. The shell scripts are stable infrastructure that rarely changes.

### Option C: Use bash -x tracing

`bash -x` logs every command executed. Could capture this to a file alongside
the coverage JSON. But it would trace asciinema/ffmpeg internals which aren't
useful for staleness detection.

**Recommendation:** Option A. Shell scripts change rarely. The few patterns in
`gif_dependencies.yaml` are sufficient. The heavy lifting (staleness of actual
CLI code paths) is handled by Python coverage.
