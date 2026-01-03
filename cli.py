#!/usr/bin/env python3
"""CLI entry point for the Dalvik bytecode emulator.

This is the command-line interface for the emulator.
For library usage, import from the `emulate` module directly.

Usage:
    python cli.py <apk_path> <target_method> [options]
    
Examples:
    python cli.py app.apk "LMyClass;->decrypt"
    python cli.py app.apk "LMyClass;->decrypt" --verbose --limit 10
"""
import sys
import os

# Ensure dalvik_vm is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emulate import main


if __name__ == "__main__":
    main()
