#!/usr/bin/env python
"""
Global CLI entrypoint for the Code Editor Agent.

Usage:
    codeagent "Create a file named utils.py"
    codeagent --dir /path/to/my-project "Refactor index.js"
    codeagent
"""
import os
import sys

# Set default workspace to the current working directory from which codeagent was called
if "CODEAGENT_WORKSPACE" not in os.environ:
    os.environ["CODEAGENT_WORKSPACE"] = os.getcwd()

# Ensure package directory is in sys.path
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")

import django
django.setup()

from django.core.management import call_command


def main():
    """Main CLI entrypoint registered in pyproject.toml as `codeagent`."""
    args = sys.argv[1:]
    try:
        call_command("orchestrate", *args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
