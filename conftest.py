"""Root conftest: mock heavy ML dependencies that are not needed for tests.

This file is loaded by pytest before any test/conftest.py, ensuring that
torch, tensorflow, and other heavy dependencies are mocked before the
hledger_preprocessor package __init__.py triggers their import.
"""

import sys
from unittest.mock import MagicMock

_MOCK_MODULES = [
    "torch",
    "torch.nn",
    "torch.nn.functional",
    "torch.cuda",
    "torch.utils",
    "torch.utils.data",
    "transformers",
    "transformers.models",
    "donut",
    "gradio",
    "tensorflow",
    "gpt4all",
    "pytesseract",
    "cv2",
    "sklearn",
    "joblib",
]

for mod in _MOCK_MODULES:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
