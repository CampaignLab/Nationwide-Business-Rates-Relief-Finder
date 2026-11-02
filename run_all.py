"""Run the tests and then every pipeline stage in order. Stops at the first failure."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = ["01_ingest", "02_clean", "03_constituency", "04_sector", "05_occupiers", "06_eligibility", "07_publish"]


def main():
    (ROOT / "data" / "work").mkdir(parents=True, exist_ok=True)
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")],
                           cwd=ROOT, capture_output=True, text=True)
    print(tests.stdout)
    summary = (tests.stdout.strip().splitlines() or ["no output"])[-1]
    with open(ROOT / "data" / "work" / "stage_tests.json", "w", encoding="utf-8") as f:
        json.dump({"result": "passed" if tests.returncode == 0 else "FAILED", "summary": summary,
                   "run_at": datetime.now().isoformat(timespec="seconds")}, f, indent=2)
    if tests.returncode != 0:
        print(tests.stderr, file=sys.stderr)
        sys.exit("Tests failed; pipeline not run.")

    for stage in STAGES:
        print(f"=== {stage} ===", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / "src" / f"{stage}.py")], cwd=ROOT)
        if result.returncode != 0:
            sys.exit(f"Stage {stage} failed with exit code {result.returncode}. Later stages not run.")
    print("All stages complete. See out/run_report.md.")


if __name__ == "__main__":
    main()
