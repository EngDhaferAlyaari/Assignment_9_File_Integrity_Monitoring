"""Windows integration tests for the actual PyInstaller EXE."""

import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    executable = Path("dist/FIM_Monitor.exe").resolve()
    if not executable.is_file():
        raise RuntimeError("EXE not found: " + str(executable))

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        target = root / "sample.txt"
        baseline_dir = root / "baselines"
        target.write_text("original content\n", encoding="utf-8")

        def run(extra=()):
            command = [str(executable), str(target), "--once", "--baseline-dir", str(baseline_dir), *extra]
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
            print("Exit:", result.returncode)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result

        first = run()
        assert first.returncode == 0 and "BASELINE CREATED" in first.stdout
        second = run()
        assert second.returncode == 0 and "[OK]" in second.stdout
        target.write_text("original Content\n", encoding="utf-8")
        changed = run()
        assert changed.returncode == 1 and "CRITICAL ALERT" in changed.stdout
        reset = run(["--reset-baseline"])
        assert reset.returncode == 0 and "BASELINE RESET" in reset.stdout
        target.unlink()
        missing = run()
        assert missing.returncode == 2 and "[MISSING]" in missing.stdout

    print("EXE INTEGRATION TESTS PASSED")


if __name__ == "__main__":
    main()
