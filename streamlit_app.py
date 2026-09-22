"""
Streamlit Cloud Entrypoint for Supply Prescript
Delegates execution to ui/app.py
"""

import os
import sys
import runpy

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Execute the main Streamlit application
ui_path = os.path.join(PROJECT_ROOT, "ui", "app.py")
runpy.run_path(ui_path, run_name="__main__")
