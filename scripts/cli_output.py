"""Keep JSON CLI output UTF-8 for consoles, agent pipes and Windows locales."""
import sys


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
