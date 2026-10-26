#!/usr/bin/env python
"""
Global CLI entrypoint for Kairo - Autonomous AI Code Editor Agent.

Usage:
    kairo "Create a file named utils.py"
    kairo --dir /path/to/my-project "Refactor index.js"
    kairo
"""
import os
import sys

# Set default workspace to the current working directory from which kairo was called
workspace = os.environ.get("KAIRO_WORKSPACE") or os.environ.get("CODEAGENT_WORKSPACE")
if not workspace:
    workspace = os.getcwd()
os.environ["KAIRO_WORKSPACE"] = workspace
os.environ["CODEAGENT_WORKSPACE"] = workspace

# Ensure package directory is in sys.path
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")

import django
django.setup()

from django.core.management import call_command


def main():
    """Main CLI entrypoint registered in pyproject.toml as `kairo` and `codeagent`."""
    args = sys.argv[1:]
    try:
        call_command("orchestrate", *args)
    except KeyboardInterrupt:
        print("\n[Kairo] Operation cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
