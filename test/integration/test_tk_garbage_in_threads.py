"""Closed matplotlib windows must not be garbage-collected in a thread.

The grouping step shows receipts in matplotlib (TkAgg) windows. Closing them
leaves Tk objects as garbage. The labeller then starts background threads
(account loading, TUI import); when the garbage collector ran inside one of
them, every Tk object's __del__ failed with "main thread is not in main
loop" (and Tk can abort with "Tcl_AsyncDelete"). The threads are now started
only after collecting that garbage on the main thread.

Real matplotlib + Tk in an Xvfb display, in a subprocess (the root conftest
mocks heavy modules in-process).
"""

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("xvfb-run") is None, reason="needs xvfb-run"
)

TK_ERROR = "main thread is not in main loop"

DRIVER = textwrap.dedent(
    """
    import gc, sys, threading
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt

    # Like the grouping step: show receipt images, close the windows.
    for _ in range(3):
        fig = plt.figure()
        plt.imshow([[0, 1], [1, 0]])
        plt.pause(0.05)
        plt.close(fig)
    del fig

    def load_accounts():  # allocates enough that the collector runs here
        junk = [[i] for i in range(100000)]
        gc.collect()

    if sys.argv[1] == "plain":
        threads = [threading.Thread(target=load_accounts, daemon=True)]
        for t in threads:
            t.start()
    else:
        from hledger_receipt_processing.receipts_to_objects.preload_threads import (  # noqa: E501
            start_preload_threads,
        )
        threads = start_preload_threads(load_accounts)
    for t in threads:
        t.join()
    print("DONE")
    """
)


def _run(tmp_path: Path, mode: str) -> subprocess.CompletedProcess:
    script = tmp_path / "driver.py"
    script.write_text(DRIVER)
    return subprocess.run(
        ["xvfb-run", "-a", sys.executable, str(script), mode],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.slow  # each failed Tk call stalls ~1 s: about 40 s in total
def test_plain_threads_reproduce_the_tk_error(tmp_path: Path) -> None:
    """Control: without the fix the error really appears here."""
    out = _run(tmp_path, "plain")
    assert "DONE" in out.stdout, out.stderr
    assert TK_ERROR in out.stderr


def test_preload_threads_do_not_collect_tk_garbage(tmp_path: Path) -> None:
    out = _run(tmp_path, "preload")
    assert "DONE" in out.stdout, out.stderr
    assert TK_ERROR not in out.stderr
