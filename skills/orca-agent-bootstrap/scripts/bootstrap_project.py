#!/usr/bin/env python3
"""Backward-compatible wrapper for `workspace.py bootstrap`."""

from __future__ import annotations

import sys

from workspace import main


if __name__ == "__main__":
    raise SystemExit(main(["bootstrap", *sys.argv[1:]]))
