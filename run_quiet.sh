#!/bin/bash
# Wrapper script to run hledger_preprocessor with CUDA/TensorFlow warnings suppressed
# Usage: ./run_quiet.sh [arguments...]

exec python -m hledger_preprocessor "$@" 2>&1 | grep -v -E 'cuda_|cuDNN|cuBLAS|cuFFT|absl::|E0000|WARNING.*InitializeLog|frozen runpy'
