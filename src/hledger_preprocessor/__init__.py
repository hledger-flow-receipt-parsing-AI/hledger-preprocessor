"""Contains the project versioning."""

import os
import warnings

# Suppress TensorFlow/CUDA/transformers warnings early
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

__version__ = "0.0.1"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())


from hledger_preprocessor.__main__ import main

_ = main  # Prevents linter warnings without executing `main`.
