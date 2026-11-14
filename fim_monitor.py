"""Assignment 9 - File Integrity Monitoring (SHA-256)."""

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

CHUNK_SIZE = 64 * 1024


def sha256_file(file_path):
    """Hash a file in small chunks, without loading all its data in memory."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def baseline_path(file_path, baseline_dir):
    """Each monitored path has its own saved reference hash."""
    path_id = hashlib.sha256(str(Path(file_path).resolve()).encode("utf-8")).hexdigest()[:24]
    return Path(baseline_dir) / (path_id + ".json")


def load_baseline(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        value = data.get("sha256", "")
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("The saved baseline hash is invalid")
        return value
    except (OSError, ValueError, TypeError, AttributeError) as error:
        raise ValueError("Cannot read the saved baseline: " + str(error)) from error


def save_baseline(path, file_path, file_hash):
    """Write the baseline to disk; keep it between program runs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump({
                "file": str(Path(file_path).resolve()),
                "sha256": file_hash,
                "created_utc": datetime.now(timezone.utc).isoformat(),
            }, file, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def check_file(file_path, baseline_dir, reset=False):
    """Return (status, message, digest). Does not hide errors."""
    file_path = Path(file_path)
    path = baseline_path(file_path, baseline_dir)
    try:
        current_hash = sha256_file(file_path)
    except FileNotFoundError:
        return "MISSING", "File not found: " + str(file_path), None
    except OSError as error:
        return "ERROR", "Cannot read file: " + str(error), None

    if reset or not path.exists():
        try:
            save_baseline(path, file_path, current_hash)
        except OSError as error:
            return "ERROR", "Cannot save baseline: " + str(error), current_hash
        label = "BASELINE RESET" if reset else "BASELINE CREATED"
        return "BASELINE", f"{label}\nSHA-256: {current_hash}", current_hash

    try:
        expected_hash = load_baseline(path)
    except ValueError as error:
        return "ERROR", str(error), current_hash

    if current_hash == expected_hash:
        return "OK", "No changes detected. SHA-256: " + current_hash, current_hash

    return "ALERT", (
        "CRITICAL ALERT! File content has changed!\n"
        + "Original SHA-256: " + expected_hash + "\n"
        + "Current  SHA-256: " + current_hash
    ), current_hash


def write_alert(baseline_dir, file_path, message):
    """Keep a simple text record of detected changes."""
    directory = Path(baseline_dir)
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / "alerts.log", "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().astimezone().isoformat()} | {Path(file_path).resolve()}\n{message}\n\n")


def monitor(file_path, baseline_dir, interval=3.0, once=False, reset=False, max_checks=None):
    if interval <= 0:
        raise ValueError("Interval must be greater than zero")

    print("File Integrity Monitor - SHA-256", flush=True)
    print("Target:", Path(file_path).resolve(), flush=True)
    print("Check interval:", interval, "seconds", flush=True)
    previous = None
    checks = 0

    try:
        while True:
            status, message, digest = check_file(file_path, baseline_dir, reset=reset)
            reset = False  # Never reset the reference again during this session.
            key = (status, digest)
            if key != previous or once:
                now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{now}] [{status}] {message}", flush=True)
                if status == "ALERT":
                    try:
                        write_alert(baseline_dir, file_path, message)
                    except OSError as error:
                        print("[WARNING] Cannot save alert log:", error, flush=True)
            previous = key
            checks += 1
            if once or (max_checks is not None and checks >= max_checks):
                return 1 if status == "ALERT" else 2 if status in ("MISSING", "ERROR") else 0
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.", flush=True)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Monitor a file for content changes with SHA-256.")
    parser.add_argument("file", help="File to monitor")
    parser.add_argument("--interval", type=float, default=3, help="Seconds between checks (default: 3)")
    parser.add_argument("--baseline-dir", default=".fim_baselines", help="Folder that stores reference hashes")
    parser.add_argument("--once", action="store_true", help="Check one time and exit")
    parser.add_argument("--reset-baseline", action="store_true", help="Approve current file as the new reference")
    args = parser.parse_args(argv)
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    return monitor(args.file, args.baseline_dir, interval=args.interval, once=args.once, reset=args.reset_baseline)


if __name__ == "__main__":
    raise SystemExit(main())
