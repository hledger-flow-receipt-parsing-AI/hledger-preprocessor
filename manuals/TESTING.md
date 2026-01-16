# Testing Guide

## Structure

```
test/
├── conftest.py              # Shared pytest fixtures (temp_finance_root)
├── unit/                    # Pure logic tests, no external dependencies
│   └── test_hledger_dict.py
├── integration/             # Multi-component tests with fixtures
│   ├── test_config_loading.py
│   ├── test_hledger_postings.py
│   └── test_new_flow.py
├── e2e/                     # Full workflow tests (GIF generation)
│   └── test_gif_generation.py
├── fixtures/                # Test data files
│   ├── categories/
│   ├── config_templates/
│   ├── journals/
│   ├── postings/
│   ├── receipts/
│   └── transactions/
└── helpers/                 # Shared test utilities
    ├── assertions.py        # assert_hledger_available, etc.
    ├── generators.py        # Random transaction generators
    └── seeders.py           # seed_receipts_into_root
```

## Running Tests

```bash
conda activate hledger_preprocessor
python -m pytest -v              # All tests
python -m pytest test/unit -v    # Unit tests only
python -m pytest test/e2e -v     # E2E tests only
```

## GIF Automation

```
gifs/
├── edit_receipt/            # Each demo type has its own folder
│   ├── generate.sh          # Sources common.sh, runs pipeline
│   ├── output/              # Generated GIFs
│   └── recordings/          # .cast files
├── automation/              # Python modules for TUI automation
│   ├── core/                # Colors, Cursor, Screen, config
│   ├── demos/               # BaseDemo class
│   ├── display/             # Key overlay, status messages
│   ├── themes/              # Theme registry
│   └── receipt_editor.py    # Edit receipt automation
└── scripts/
    └── common.sh            # Shared bash functions
```

## Adding New Demos

1. Create `gifs/<demo_name>/generate.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"
init_demo "<demo_name>" "$@"
run_full_pipeline "gifs.automation.<module>" "<Title>"
```

2. Create Python automation module in `gifs/automation/`
1. Add E2E test in `test/e2e/`
