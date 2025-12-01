"""Packaging logic for hledger_preprocessor."""

from __future__ import annotations

from setuptools import find_packages, setup

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
# setuptools.setup()


setup(
    name="hledger_preprocessor",
    version="1.0",
    packages=find_packages(where="src"),
)
