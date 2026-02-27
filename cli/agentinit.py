#!/usr/bin/env python3
"""Backward-compatible shim — delegates to the agentinit package."""

import os
import sys

# Allow running from the repo without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agentinit.cli import main

if __name__ == "__main__":
    main()
