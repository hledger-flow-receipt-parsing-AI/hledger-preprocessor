#!/usr/bin/env bash
# =============================================================================
# hledger-preprocessor Demo Recorder → GIF Generator
# Creates a clean asciinema recording and converts it to an optimized GIF
# with beautiful color-coded feedback
# =============================================================================

set -euo pipefail

#!/usr/bin/env bash
# ... (all your existing code up to Configuration Variables) ...

# ------------------------- Configuration Variables ---------------------------
# NEW: Read CONFIG_FILEPATH from the first command-line argument
CONFIG_FILEPATH="${1:?Error: Missing config file path argument.}"
export CONFIG_FILEPATH

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OUTPUT_CAST="${SCRIPT_DIR}/demo.cast"
OUTPUT_GIF="${SCRIPT_DIR}/demo.gif"
HLEDGER_CMD="hledger_preprocessor --config ${CONFIG_FILEPATH} --edit-receipt"


# ----------------------------- Colors ---------------------------------------
RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
PURPLE="$(tput setaf 5)"
ORANGE="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

# ------------------------- Configuration Variables ---------------------------


RECORDER_TITLE="hledger-preprocessor receipt matcher"

ROWS=32
COLS=120
IDLE_TIME_LIMIT=2
FONT_SIZE=18
THEME="solarized-dark"

# Full command (with proper conda activation)
HLEDGER_CMD="hledger_preprocessor --config ${CONFIG_FILEPATH} --edit-receipt"

# Create a Python pexpect script to automate the TUI interaction
AUTOMATION_SCRIPT=$(mktemp --suffix=.py)
cat > "$AUTOMATION_SCRIPT" << 'PYTHON_EOF'
import pexpect
import sys
import os
import time

config_path = os.environ.get("CONFIG_FILEPATH")
conda_base = os.popen("conda info --base").read().strip()

# Build the command
cmd = f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && conda activate hledger_preprocessor && hledger_preprocessor --config {config_path} --edit-receipt'"

# Spawn with a PTY - set dimensions for urwid
child = pexpect.spawn(cmd, encoding='utf-8', timeout=60, dimensions=(32, 120))
child.logfile = sys.stdout

# Hide the terminal cursor so only the TUI selector/highlighting is visible
print('\x1b[?25l', end='', flush=True)

# Wait for the receipt list TUI to render by looking for the header text
try:
    child.expect('Receipts List', timeout=10)
except pexpect.TIMEOUT:
    print("ERROR: TUI did not render in time")
    child.terminate()
    sys.exit(1)

# Give TUI a moment to fully render after header appears
time.sleep(1.5)

# Navigate DOWN to the second receipt to show the selection/highlighting moving
child.send('\x1b[B')  # Down arrow escape sequence
time.sleep(0.5)

# Force read any pending output - this helps flush the PTY buffer
try:
    output = child.read_nonblocking(size=10000, timeout=0.5)
except:
    pass

time.sleep(1.5)  # Pause so user can see the highlight on second receipt

# Now select the second receipt (repairs:bike) with space
child.send(' ')
time.sleep(0.5)

# Wait for the edit receipt TUI to load and show the "Can you see" prompt
try:
    child.expect('Can you see', timeout=30)
    time.sleep(1)
    # Press Enter to confirm we can see the image
    child.send('\r')
except pexpect.TIMEOUT:
    pass  # Continue even if prompt doesn't appear

# Wait for the edit receipt TUI to fully render with all fields
try:
    child.expect('Bookkeeping expense category', timeout=10)
    time.sleep(1.5)  # Let TUI fully render
except pexpect.TIMEOUT:
    pass

# The cursor starts at the date field
# Press Enter to move from date field to bookkeeping expense category field
child.send('\r')
time.sleep(1)

# Now we're in the bookkeeping category field which shows "repairs:bike"
# First, go to the END of the current text using End key
child.send('\x1b[F')  # End key escape sequence
time.sleep(0.5)

# Alternative: use Ctrl+E which often goes to end of line in text fields
child.send('\x05')  # Ctrl+E
time.sleep(0.5)

# Now backspace to delete "repairs:bike" (12 characters)
for i in range(12):
    child.send('\x7f')  # Backspace character
    time.sleep(0.08)  # Small delay between each backspace for visibility

time.sleep(0.5)

# Now type the new category: "groceries:ekoplaza"
for char in "groceries:ekoplaza":
    child.send(char)
    time.sleep(0.1)  # Small delay between each character for visibility

time.sleep(1)

# Press Enter to confirm the category change
child.send('\r')
time.sleep(1)

# Send 'q' to quit the edit TUI
child.send('q')

# Wait for the process to complete
try:
    child.expect(pexpect.EOF, timeout=30)
except pexpect.TIMEOUT:
    child.terminate()

# Restore the terminal cursor
print('\x1b[?25h', end='', flush=True)
PYTHON_EOF

WRAPPED_CMD="python $AUTOMATION_SCRIPT"

# Cleanup function
cleanup() {
    rm -f "$AUTOMATION_SCRIPT" 2>/dev/null || true
}
trap cleanup EXIT

# ----------------------------- Functions ------------------------------------
log()    { echo -e "${BOLD}${GREEN}[+]${RESET} $*" ; }
warn()   { echo -e "${BOLD}${ORANGE}[!]${RESET} $*" ; }
error()  { echo -e "${BOLD}${RED}[✗]${RESET} $*" ; }
header() { echo -e "${PURPLE}${BOLD}=== $1 ===${RESET}" ; }

# ----------------------------- Pre-flight Checks ----------------------------
header "hledger-preprocessor Demo Recorder"

# Check we're in the right conda environment
if [[ "$(python -c 'import sys; print(sys.executable)' 2>/dev/null || echo '')" != */hledger_preprocessor/* ]]; then
    error "Not in the 'hledger_preprocessor' conda environment!"
    warn "Please run: conda activate hledger_preprocessor"
    exit 1
fi

log "Using config: ${CONFIG_FILEPATH}"
log "Command to record:"
log "${HLEDGER_CMD}"

# Remove old files
rm -f "$OUTPUT_CAST" "$OUTPUT_GIF"

# ----------------------------- Recording ------------------------------------
header "Starting 18-second asciinema recording..."

if asciinema rec "$OUTPUT_CAST" \
    --command="$WRAPPED_CMD" \
    --title "$RECORDER_TITLE" \
    --idle-time-limit="$IDLE_TIME_LIMIT" \
    --rows "$ROWS" \
    --cols "$COLS" \
    -y -q; then
    log "Recording completed successfully → ${OUTPUT_CAST}"
else
    error "asciinema recording failed!"
    exit 1
fi

# ----------------------------- Post-process cast file ------------------------
# Remove cursor show sequences (\e[?25h) so only the TUI selector is visible
# Keep cursor hide sequences (\e[?25l)
log "Removing cursor show sequences from recording..."
sed -i 's/\\u001b\[?25h//g; s/\\u001b\[3;3H//g; s/\\u001b\[5;3H//g' "$OUTPUT_CAST"

# ----------------------------- GIF Conversion -------------------------------
header "Converting to GIF using agg..."

# Ensure agg is available (pure Python, reliable in 2025+)
if ! python -c "import agg" &>/dev/null; then
    log "Installing agg (asciinema → GIF converter)..."
    pip install -q agg || { error "Failed to install agg"; exit 1; }
fi

echo
if asciinema-agg "$OUTPUT_CAST" "$OUTPUT_GIF" \
    --theme "$THEME" \
    --font-size "$FONT_SIZE"; then
    log "GIF created successfully: ${BOLD}${OUTPUT_GIF}${RESET}"
    echo
    echo "   Just add this to your README.md:"
    echo
    echo "   ![hledger-preprocessor demo](${OUTPUT_GIF})"
    echo
    echo "   Done! 🎉"
else
    error "GIF conversion failed (asciinema-agg error)"
    error "The command inside may have failed → check output above (look for red/orange lines)"
    exit 1
fi

# Optional: Optimize with gifsicle if available
if command -v gifsicle >/dev/null 2>&1; then
    log "Optimizing GIF with gifsicle..."
    gifsicle -O3 --lossy=80 -o "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF" && mv "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF"
    log "Optimized! Size: $(du -h "$OUTPUT_GIF" | cut -f1)"
fi

exit 0
