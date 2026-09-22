"""
Master Launcher for Project 3: Supply Prescript
Runs the Streamlit Operational UI or FastAPI Backend.
"""

import sys
import subprocess
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 65)
    print(" Supply Prescript - Closed-Loop Prescriptive Analytics System")
    print("=" * 65)
    print(" 1. Launch Simple & Clean Operational UI (Streamlit)")
    print(" 2. Launch Transactional Write-Back REST API (FastAPI)")
    print(" 3. Run Automated End-to-End Pipeline Tests")
    print(" 4. Re-Seed Database from Kaggle DataCo Dataset")
    print("=" * 65)
    
    choice = sys.argv[1] if len(sys.argv) > 1 else "1"
    
    if choice == "1" or choice == "--ui":
        print("\nStarting Streamlit UI on http://localhost:8501 ...")
        cmd = [sys.executable, "-m", "streamlit", "run", os.path.join(PROJECT_ROOT, "ui", "app.py"), "--server.headless", "true"]
        subprocess.run(cmd)
    elif choice == "2" or choice == "--api":
        print("\nStarting FastAPI Write-Back Server on http://127.0.0.1:8000 ...")
        cmd = [sys.executable, "-m", "uvicorn", "api.app:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
        subprocess.run(cmd)
    elif choice == "3" or choice == "--test":
        print("\nRunning test suite...")
        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "tests", "test_pipeline.py")]
        subprocess.run(cmd)
    elif choice == "4" or choice == "--seed":
        print("\nRe-seeding database...")
        cmd = [sys.executable, "database/seed_data.py"]
        subprocess.run(cmd)
    else:
        print(f"Unknown option: {choice}. Use 1 (UI), 2 (API), 3 (Test), or 4 (Seed).")

if __name__ == "__main__":
    main()
