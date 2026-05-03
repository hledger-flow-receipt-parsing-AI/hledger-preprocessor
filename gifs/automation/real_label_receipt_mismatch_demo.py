#!/usr/bin/env python3
"""Real inline-matching-CLI demo for US-2b.10.

Demonstrates: receipt dated Jan 15, CSV posted Jan 18 (3-day delay),
default +/-2 day window misses, user launches matching CLI inline from
TUI, widens to +/-5 days, match found, TUI resumes with green fields.

Creates its own isolated test environment (does not depend on
setup_test_environment.py) so it can use a bespoke CSV with the delayed
posting date.
"""

import glob
import hashlib
import json
import os
import shutil
import signal
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any, Dict

import yaml

from .core import (
    Colors,
    Cursor,
    Screen,
    StoryMarkerEmitter,
    get_conda_base,
)
from .display import show_after_state, show_before_state, show_command
from .key_display import show_key
from .receipt_editor import (
    ReceiptDemoValues,
    _fill_datetime,
    _fill_float,
    _fill_text,
    _precreate_rotation_and_crop_metadata,
    _select_horizontal_first,
    _select_vertical,
    _tui_markers,
    _write_tui_markers_json,
)
from .tui_navigator import Keys, TuiNavigator

# Pause durations (seconds) — tuned for GIF readability
_BETWEEN = 0.3
_AFTER_TYPE = 0.5
_AFTER_SELECT = 0.3


# ---------------------------------------------------------------------------
# Mismatch-specific receipt values — same as CARD_RECEIPT (US-2b.1)
# ---------------------------------------------------------------------------
MISMATCH_RECEIPT = ReceiptDemoValues(
    # Same receipt as US-2b.1: ekoplaza Jan 15, 42.17 EUR
    date_digits="202501151030",
    is_withdrawal=False,
    category="groceries:ekoplaza",
    account_index="0",  # Triodos checking
    currency_index="9",  # EUR
    amount="42.17",
    change="0",
    add_another_account=False,
    shop_index="0",
    shop_name="Ekoplaza",
    shop_street="Groenerstraat",
    shop_house_nr="89",
    shop_zipcode="7898BA",
    shop_city="Timboektoe",
    shop_country="Belgie",
    subtotal="",
    total_tax="7.35",
)


# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------


def _get_image_content_hash(image_path: str) -> str:
    """Calculate SHA256 hash of image file content."""
    hasher = hashlib.sha256()
    with open(image_path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def create_mismatch_environment() -> Dict[str, Any]:
    """Create a self-contained test environment with a delayed-posting CSV.

    The CSV has the Ekoplaza 42.17 EUR transaction dated **Jan 18** while
    the receipt is dated Jan 15 — 3 days apart, outside the default +/-2
    day matching window.  A second small bakery row is included so
    ``csv.Sniffer().has_header()`` works correctly with multiple rows.
    """
    root = Path(tempfile.mkdtemp(prefix="mismatch_demo_"))
    project_root = Path(__file__).parent.parent.parent

    # Directory structure
    dirs = [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "receipt_labels",
        "asset_transaction_csvs",
        "hledger_plots",
        "start_pos",
        "test_working_dir/import/at/triodos/checking/1-in",
        "test_working_dir/import/at/triodos/checking/2-csv",
        "test_working_dir/import/at/triodos/checking/3-journal",
        "test_working_dir/import/at/wallet/physical/1-in",
        "test_working_dir/import/at/wallet/physical/2-csv",
        "test_working_dir/import/at/wallet/physical/3-journal",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Config from template
    template_path = (
        project_root
        / "test"
        / "fixtures"
        / "config_templates"
        / "1_bank_1_wallet.yaml"
    )
    config_dict = yaml.safe_load(template_path.read_text())
    config_dict["dir_paths"]["root_finance_path"] = str(root)
    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_dict, default_flow_style=False)
    )

    # Categories
    categories = {"groceries": {"ekoplaza": {}, "supermarket": {}}}
    (root / "categories.yaml").write_text(yaml.safe_dump(categories))

    # Bank CSV — Ekoplaza 42.17 EUR posted Jan 18 (3 days late)
    # Two rows so csv.Sniffer correctly identifies the lack of a header.
    csv_content = (
        "02-01-2025,NL79 TRIO 0379 2834 09,-5.00,debit,Bakkerij,NL789,"
        "IC,bread,995.00\n"
        "18-01-2025,NL79 TRIO 0379 2834 09,-42.17,debit,Ekoplaza,NL456,"
        "IC,groceries:ekoplaza,957.83\n"
    )
    csv_path = root / "triodos_2025.csv"
    csv_path.write_text(csv_content)

    # Start journal
    journal_path = root / "start_pos" / "2024_complete.journal"
    journal_path.write_text(
        textwrap.dedent(
            """\
        2024/01/01 Opening Balances
            Assets:Checking:Triodos          EUR 1000.00
            Equity:Opening Balances
    """
        )
    )

    # hledger import rules (Triodos)
    triodos_rules = root / "test_working_dir/import/at/triodos/checking"
    (triodos_rules / "triodos.rules").write_text(
        textwrap.dedent(
            """\
        skip 0
        fields date, _, amount, _, payee, _, _, description, _
        date-format %d-%m-%Y
        currency EUR
        account1 Assets:Checking:Triodos
    """
        )
    )

    # hledger import rules (wallet)
    wallet_rules = root / "test_working_dir/import/at/wallet/physical"
    (wallet_rules / "eur.rules").write_text(
        textwrap.dedent(
            """\
        skip 0
        fields date, amount, description
        date-format %Y-%m-%d
        currency EUR
        account1 Assets:Wallet:Physical:EUR
    """
        )
    )

    # Wallet asset CSV (required by get_all_accounts)
    wallet_asset_csv = (
        root
        / "test_working_dir"
        / "asset_transaction_csvs"
        / "at"
        / "wallet"
        / "physical"
        / "Currency.EUR.csv"
    )
    wallet_asset_csv.parent.mkdir(parents=True, exist_ok=True)
    wallet_asset_csv.write_text(
        '"currency","account_holder","bank","account_type",'
        '"date","amount","tendered_amount_out","change_returned"\n'
    )

    # Seed receipt image — use the ekoplaza card image from fixtures
    from test.helpers import seed_receipt_images_only

    from hledger_preprocessor.config.Config import Config
    from hledger_preprocessor.config.load_config import load_config

    config: Config = load_config(
        config_path=str(config_path),
        pre_processed_output_dir=None,
    )

    fixtures_dir = project_root / "test" / "fixtures" / "receipts"
    source_files = [fixtures_dir / "groceries_ekoplaza_card.json"]
    seed_receipt_images_only(config=config, source_json_paths=source_files)

    return {
        "root": root,
        "config_path": config_path,
        "csv_path": csv_path,
        "config_dict": config_dict,
    }


# ---------------------------------------------------------------------------
# TUI field-filling with mismatch handling
# ---------------------------------------------------------------------------


def _fill_receipt_fields_with_mismatch(
    nav: TuiNavigator,
    vals: ReceiptDemoValues,
    marker_prefix: str = "",
) -> None:
    """Drive the receipt TUI fields, then handle the mismatch interaction.

    Fills all fields up to and including "Add another account? = n", then
    waits for the mismatch choice widget.  Selects "Enter matching CLI",
    interacts with the matching CLI to widen the date range, then continues
    filling the remaining fields (shop, tax, done) after the TUI resumes.
    """

    def _mark(field: str) -> None:
        if marker_prefix:
            key = f"{marker_prefix}__{field}"
            _tui_markers[key] = time.time()

    nav.flush_output()

    # ── Fields 1–7: same as normal receipt filling ────────────────────
    _mark("date")
    _fill_datetime(nav, vals.date_digits)

    nav.wait_for("withdrawal", timeout=10, silent=True)
    _mark("is_withdrawal")
    time.sleep(0.5)
    _select_horizontal_first(nav)  # "n" (first option) — not a withdrawal
    nav.flush_output()
    time.sleep(0.8)
    nav.flush_output()

    _mark("category")
    _fill_text(nav, vals.category)
    nav.flush_output()

    _mark("bank_account")
    _select_vertical(nav, vals.account_index)
    nav.flush_output()

    _mark("currency")
    _select_vertical(nav, vals.currency_index)
    nav.flush_output()

    _mark("amount")
    _fill_float(nav, vals.amount)
    nav.flush_output()

    _mark("change")
    _fill_float(nav, vals.change)
    nav.flush_output()

    # ── "Add another account? = n" ────────────────────────────────────
    nav.wait_for("another account", timeout=5, silent=True)
    time.sleep(0.3)
    _select_horizontal_first(nav)  # "n" (first option)
    nav.flush_output()

    # ── Wait for the mismatch choice widget ───────────────────────────
    # After "Add another account = n", the reconfiguration runs amount
    # matching.  With the Jan 15 receipt vs Jan 18 CSV (3-day gap,
    # +/-2 day default window), there are 0 matches.  The TUI injects
    # a horizontal choice: "Correct amounts/dates" | "Enter matching CLI"
    _mark("mismatch_choice")
    time.sleep(2.0)
    nav.flush_output()

    # The choice widget appears with focus on first option.
    # Move RIGHT to "Enter matching CLI", then press Enter.
    time.sleep(1.0)
    nav.send(Keys.RIGHT, pause=0.8)
    nav.flush_output()
    time.sleep(0.8)
    nav.press_enter(pause=0.5)
    # Do NOT flush here — the matching CLI prompt will be printed to the
    # pty right after urwid exits, and flush_output() would discard it.

    # ── Matching CLI interaction ──────────────────────────────────────
    # urwid suspends → matching CLI takes over stdout/stdin.
    # Wait for the action prompt.
    _mark("matching_cli")

    # The CLI shows the action menu ending with "5. Widen the amount margin".
    # Wait for the last menu item to ensure the full prompt is consumed.
    nav.child.expect("Widen the amount margin", timeout=30)
    time.sleep(1.0)

    # Option 4 is "Widen the date margin".
    # Use sendline() for raw input() interaction (not TUI).
    nav.child.sendline("4")

    # Wait for the widen-date prompt: "Enter a positive number of days
    # to widen the date range: "
    nav.child.expect("widen the date range", timeout=15)
    time.sleep(0.5)

    # Enter 3 additional days (2 + 3 = 5 day window, covers the 3-day gap)
    nav.child.sendline("3")

    # Wait for "Found unique match! Returning to TUI."
    nav.child.expect("unique match|Found.*match|Returning", timeout=30)
    time.sleep(2.0)

    # ── TUI resumes ───────────────────────────────────────────────────
    # urwid resumes, reconfiguration runs with widened config (+/-5 days),
    # amount fields turn green, choice widget is removed.
    # Wait for the TUI to fully re-render — the next question should be
    # "Select Shop Address".
    _mark("tui_resumed")
    time.sleep(3.0)
    nav.flush_output()

    # ── Remaining fields: shop address, subtotal, tax ─────────────────
    _select_vertical(nav, vals.shop_index)
    nav.flush_output()

    if vals.shop_index == "0":
        _mark("shop_name")
        _fill_text(nav, vals.shop_name)
        nav.flush_output()

        _mark("shop_street")
        _fill_text(nav, vals.shop_street)
        nav.flush_output()

        _mark("shop_house_nr")
        _fill_text(nav, vals.shop_house_nr)
        nav.flush_output()

        _mark("shop_zipcode")
        _fill_text(nav, vals.shop_zipcode)
        nav.flush_output()

        _mark("shop_city")
        _fill_text(nav, vals.shop_city)
        nav.flush_output()

        _mark("shop_country")
        _fill_text(nav, vals.shop_country)
        nav.flush_output()

    _fill_float(nav, vals.subtotal)
    nav.flush_output()

    _mark("tax")
    _fill_float(nav, vals.total_tax)
    nav.flush_output()

    # ── Done with this receipt? ───────────────────────────────────────
    _select_horizontal_first(nav)
    nav.flush_output()


# ---------------------------------------------------------------------------
# Main demo runner
# ---------------------------------------------------------------------------


def run_mismatch_demo() -> None:
    """Run the complete mismatch → inline matching CLI → resume demo."""
    Screen.clear()
    time.sleep(0.3)

    env = create_mismatch_environment()
    config_path = str(env["config_path"])
    config_dict = env["config_dict"]
    root = env["root"]

    labels_dir = os.path.join(
        str(root),
        config_dict.get("dir_paths", {}).get(
            "receipt_labels_dir", "receipt_labels"
        ),
    )

    # Remove existing labels so the TUI finds unlabelled receipts
    if os.path.isdir(labels_dir):
        for label_json in glob.glob(
            os.path.join(labels_dir, "**", "*.json"), recursive=True
        ):
            os.remove(label_json)

    # Keep only the ekoplaza receipt image
    input_dir = os.path.join(
        str(root),
        config_dict.get("dir_paths", {}).get(
            "receipt_images_input_dir", "receipt_images_input"
        ),
    )
    if os.path.isdir(input_dir):
        images = sorted(
            f
            for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        )
        for extra in images[1:]:
            os.remove(os.path.join(input_dir, extra))

    # Pre-create rotation/crop metadata
    _precreate_rotation_and_crop_metadata(config_dict)

    conda_base = get_conda_base()

    # ── Emit structural markers: before state ─────────────────────────
    emitter = StoryMarkerEmitter("US-2b.10")

    temp_dir = tempfile.mkdtemp()
    before_file = os.path.join(temp_dir, "before_edit_receipt.json")
    after_file = os.path.join(temp_dir, "after_edit_receipt.json")
    with open(before_file, "w") as f:
        json.dump({}, f)

    # Emit all markers up to and including img_ekoplaza_card
    emitter.emit_until("img_ekoplaza_card")
    show_before_state(before_file, after_file)

    emitter.emit_until("nolbl_ekoplaza_card_eur")
    _tui_markers["_calibration_nolbl"] = time.time()

    # ── Show command ──────────────────────────────────────────────────
    Screen.clear()
    time.sleep(0.2)
    command_display = (
        f"hledger_preprocessor --config {config_path} --tui-label-receipts"
    )
    show_command(command_display, conda_env="hledger_preprocessor")
    show_key("\r", rows=50, cols=120)
    time.sleep(0.5)

    # ── Spawn the real TUI ────────────────────────────────────────────
    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_preprocessor --config {config_path} --tui-label-receipts'"
    )
    nav = TuiNavigator(cmd, dimensions=(50, 120), timeout=60)

    try:
        nav.spawn()
        Cursor.hide()

        # Wait for "Can you see" prompt (skipped rotation/crop)
        if not nav.wait_for("Can you see", timeout=30, silent=True):
            print(
                f"{Colors.BOLD_RED}Error: TUI did not render in"
                f" time{Colors.RESET}"
            )
            return

        time.sleep(0.5)
        nav.press_enter()

        Cursor.show()
        Cursor.set_style(Cursor.BLINKING_BLOCK)

        # Wait for the urwid TUI to fully render
        if nav.wait_for("Select Shop Address", timeout=15, silent=True):
            time.sleep(0.5)

        nav.flush_output()
        time.sleep(0.8)

        _tui_markers["tui_ekoplaza_card_eur"] = time.time()

        # ── Fill fields + handle mismatch ─────────────────────────────
        _fill_receipt_fields_with_mismatch(
            nav, MISMATCH_RECEIPT, marker_prefix="tui_ekoplaza_card_eur"
        )

        # Wait for process exit after TUI saves
        time.sleep(0.5)
        if not nav.wait_for_exit(timeout=15):
            nav.terminate()

    finally:
        Cursor.show()
        nav.clear_key_display()
        if nav.child is not None:
            try:
                child_pid = nav.child.pid
                os.killpg(os.getpgid(child_pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            try:
                nav.child.close(force=True)
            except Exception:
                pass

    # ── After state ───────────────────────────────────────────────────
    time.sleep(0.3)

    # Find the newly created label
    new_label_path = None
    pattern = os.path.join(labels_dir, "**", "*.json")
    json_files = glob.glob(pattern, recursive=True)
    if json_files:
        new_label_path = max(json_files, key=os.path.getmtime)
        shutil.copy(new_label_path, after_file)

    emitter.emit_until("lbl_ekoplaza_card_eur")
    Screen.clear()
    time.sleep(0.2)
    show_after_state(before_file, after_file)

    emitter.emit_remaining()

    # Cleanup temp dir (keep demo root for inspection if needed)
    shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    """Main entry point when run as a script."""
    run_mismatch_demo()
    _write_tui_markers_json()


if __name__ == "__main__":
    main()
    os._exit(0)
