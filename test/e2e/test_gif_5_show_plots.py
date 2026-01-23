"""E2E test for GIF 5: Show Plots demo.

Demonstrates hledger_plot visualizations (Sankey + Treemap).
Shows the interactive Dash dashboard with financial plots.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_5_show_plots(temp_finance_root, monkeypatch):
    """Test GIF 5: show_plots demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="5_show_plots",
        gif_subdir="5_show_plots",
        timeout=90,
    )
