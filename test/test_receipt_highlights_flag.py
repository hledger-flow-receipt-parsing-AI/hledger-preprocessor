"""``--no-receipt-highlights`` turns off the boxes that mark the evidence of
the AI suggestions on the receipt photo while labelling (they are on by
default; Alt+h toggles them in the TUI)."""

from hledger_config.arg_parser import create_arg_parser


def test_receipt_highlights_are_on_by_default() -> None:
    args = create_arg_parser().parse_args(["--config", "c.yaml"])

    assert args.no_receipt_highlights is False


def test_the_flag_turns_receipt_highlights_off() -> None:
    args = create_arg_parser().parse_args(
        [
            "--config",
            "c.yaml",
            "--tui-label-receipts",
            "--no-receipt-highlights",
        ]
    )

    assert args.no_receipt_highlights is True
