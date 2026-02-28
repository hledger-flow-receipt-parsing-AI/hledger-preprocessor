# GIF Demo Generation

## Overview

This directory contains scripts and automation for generating demonstration GIFs of hledger-preprocessor functionality.

## Directory Structure

- `1a_setup_config/` - Config file setup demo
- `1b_add_category/` - Adding spending categories
- `2a_crop_receipt/` - **Receipt image cropping TUI** (uses OpenCV)
- `2b_label_receipt/` - Receipt labeling TUI
- `2b_label_foreign_currency/` - Foreign-currency receipt labelling
- `2b_label_split_payment/` - Split-payment receipt labelling
- `2b_label_returned_items/` - Returned-items receipt labelling
- `3_match_receipt_to_csv/` - Matching receipts to bank transactions
- `3b_foreign_currency_match/` - Foreign-currency matching
- `3c_widen_date_match/` - Widen-date matching
- `3d_disambiguate_match/` - Disambiguation matching
- `4_run_pipeline/` - Full pipeline execution
- `5_show_plots/` - Financial visualization/plots
- `automation/` - Shared automation code and simulated demos
- `scripts/` - Common shell utilities
- `assets/` - Receipt images and other static assets

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
