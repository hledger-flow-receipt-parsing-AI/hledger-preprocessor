# Receipt Rotation & Cropping GIF Demo

## Goal

Create GIFs that demonstrate the receipt image rotation and cropping TUI workflow - showing the actual images with OpenCV overlays (not ASCII simulation), along with terminal output.

## Implementation Status: COMPLETE

The OpenCV-based demo is fully implemented with the complete rotation + cropping workflow.

### Generated GIFs

#### 1. Complete Workflow (Terminal + OpenCV side-by-side)

- **File**: `output/02b_crop_receipt_workflow.gif`
- **Shows**: Terminal output on the left, OpenCV window on the right
- **Content**:
  1. Rotation phase - sideways receipt being rotated with 'r' key
  1. Cropping phase - adjusting crop rectangle with arrow keys and Alt

#### 2. OpenCV Only

- **File**: `output/02b_crop_receipt_opencv_only.gif`
- **Shows**: Just the OpenCV TUI frames (smaller file size)

#### 3. ASCII Simulation (original)

- **File**: `output/02b_crop_receipt.gif`
- **Generator**: `generate.sh`
- Uses terminal-based ASCII art (for asciinema recording)

### Demo Scripts

| Script                                       | Output                                                              | Description                                        |
| -------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------- |
| `gifs/automation/opencv_rotate_crop_demo.py` | `02b_crop_receipt_workflow.gif`, `02b_crop_receipt_opencv_only.gif` | Complete rotation + cropping demo with real images |
| `gifs/automation/opencv_crop_demo.py`        | `02b_crop_receipt_opencv.gif`                                       | Cropping-only demo                                 |
| `gifs/automation/simulated_crop_demo.py`     | `02b_crop_receipt.gif`                                              | ASCII simulation                                   |

### Regenerate the Demo

```bash
# Complete workflow (recommended)
./gifs/02b_crop_receipt/generate_opencv.sh

# Or run Python directly
python -m gifs.automation.opencv_rotate_crop_demo
```

## Workflow Demonstrated

### Phase 1: Rotation TUI

The demo shows a receipt image that appears sideways (rotated 90°):

1. **Initial state**: Receipt appears rotated
1. **Press 'r'**: Rotates image 90° clockwise
1. **Press Enter**: Saves the rotated image

**Terminal output**:

```
rotated_path=receipts_processed/receipt_001_rotated.jpg
Rotated: 90 [degrees], image saved to receipts_processed/receipt_001_rotated.jpg
```

### Phase 2: Cropping TUI

After rotation, the cropping interface appears:

1. **Initial selection**: Wide selection including background
1. **Arrow keys**: Move top-left corner inward
1. **Alt key**: Switch to bottom-right corner
1. **Arrow keys**: Adjust bottom-right corner
1. **Fine-tune**: Align with receipt edges
1. **Press Enter**: Save the cropped image

**Visual elements** (exact same as real implementation):

- Green rectangle: crop boundary (`cv2.rectangle`)
- Red crosshair: active corner marker (`cv2.drawMarker`)
- Green crosshair: inactive corner marker
- Text overlay: coordinates and active corner indicator

**Terminal output**:

```
cropped_path=receipts_processed/receipt_001_cropped.jpg
Adjusted x1 to 0.20 (Right)
Switched to Bottom-Right corner
Cropped image saved to receipts_processed/receipt_001_cropped.jpg
```

## Implementation Details

### Rotation TUI

- **Source**: `src/hledger_preprocessor/receipts_to_objects/edit_images/rotate_all_images.py`
- **Controls**: `r` (CW), `l` (CCW), `Backspace` (undo), `Enter` (save), `q` (quit)
- **No overlays**: Just displays the image in an OpenCV window

### Cropping TUI

- **Source**: `src/hledger_preprocessor/receipts_to_objects/edit_images/crop_image.py`
- **Controls**: Arrow keys (move 10%), Alt (switch corner), 0-9 (numeric input), Enter (save)
- **Coordinate system**: Normalized [x1, y1, x2, y2] from 0.0 to 1.0
- **Default position**: [0.2, 0.2, 0.8, 0.8]

### Demo Generation

- Uses headless rendering (Option 3) - no display required
- Creates synthetic tilted receipt using PIL
- Renders frames using the SAME OpenCV drawing code as the real TUI
- Combines frames into GIF using imageio

## Related Files

- `src/hledger_preprocessor/receipts_to_objects/edit_images/rotate_all_images.py` - Rotation TUI
- `src/hledger_preprocessor/receipts_to_objects/edit_images/crop_image.py` - Cropping TUI
- `gifs/automation/synthetic_receipt.py` - Creates synthetic receipt images
