# GIF Demo Generation

## Overview

This directory contains scripts and automation for generating demonstration GIFs of hledger-preprocessor functionality.

## Directory Structure

- `01_setup_config/` - Config file setup demo
- `02_add_category/` - Adding spending categories
- `02b_crop_receipt/` - **Receipt image cropping TUI** (uses OpenCV)
- `04_label_receipt/` - Receipt labeling TUI
- `04_match_receipt_to_csv/` - Matching receipts to bank transactions
- `05_run_pipeline/` - Full pipeline execution
- `06_show_plots/` - Financial visualization/plots
- `automation/` - Shared automation code and simulated demos
- `scripts/` - Common shell utilities

## Key Files

- `gif_config.yaml` - Configuration for GIF generation
- `scripts/common.sh` - Shared bash utilities for demos

## Cropping TUI Implementation

The actual cropping interface is at:
`src/hledger_preprocessor/receipts_to_objects/edit_images/crop_image.py`

It uses:

- OpenCV (`cv2`) for image display and drawing
- Green rectangle for crop boundaries
- Red crosshair for active corner indicator
- Arrow keys (10% steps), Alt (switch corners), Enter (save)

## Test Environment

Use `run_start_sh_test.py` in the project root to create a test environment at `~/finance_test` with sample data.
Then that script outputs how to run the ./start.sh code like:
NEXT STEP - Run start.sh with the config file:
------------------------------------------------------------
  ./start.sh --config /home/a/finance_test/config.yaml

