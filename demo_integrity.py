"""Short real demo: baseline -> unchanged -> modified -> restored."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fim_monitor import check_file


def main():
    print("Assignment 9 - File Integrity Monitoring")
    print("Local demonstration (no external files are modified)")
    with TemporaryDirectory() as temporary:
        demo_dir = Path(temporary)
        target = demo_dir / "example.txt"
        baselines = demo_dir / "baselines"
        original = b"Security log - original data\n"
        target.write_bytes(original)

        for title, contents in (
            ("1. First check", original),
            ("2. No change", original),
            ("3. Change one character", b"Security log - originAl data\n"),
            ("4. Restore original file", original),
        ):
            target.write_bytes(contents)
            status, message, _ = check_file(target, baselines)
            print("\n" + title)
            print("Status:", status)
            print(message)

    print("\nDemo completed.")


if __name__ == "__main__":
    main()
