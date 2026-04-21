#!/usr/bin/env python3
"""
Script to convert PlantUML (.puml) diagrams to PNG format.

Finds all .puml files in docs/diagrams/plantuml and converts them to PNG
using the system plantuml command, saving images in the same directory.

Requirements:
    - plantuml installed and available on PATH

Usage:
    # Convert all diagrams
    python3 docs/diagrams/generate_plantuml_pngs.py

    # Convert a single diagram
    python3 docs/diagrams/generate_plantuml_pngs.py architecture
    python3 docs/diagrams/generate_plantuml_pngs.py architecture.puml
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
PLANTUML_DIR = BASE_DIR / "plantuml"
OUTPUT_DIR = BASE_DIR / "images"
DPI = 200


def check_plantuml():
    """Check that plantuml is available on PATH."""
    try:
        result = subprocess.run(
            ["plantuml", "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            version_line = (
                result.stdout.splitlines()[0] if result.stdout else ""
            )
            print(f"✓ {version_line}")
            return True
        return False
    except FileNotFoundError:
        return False


def convert(puml_file: Path) -> bool:
    """Convert a single .puml file to PNG next to the source file."""
    print(f"  Converting {puml_file.name} ...", end=" ", flush=True)
    try:
        subprocess.run(
            [
                "plantuml",
                f"-Sdpi={DPI}",
                "-tpng",
                str(puml_file),
                "-o",
                str(OUTPUT_DIR),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓  ->  {puml_file.stem}.png")
        return True
    except subprocess.CalledProcessError as e:
        print("✗")
        if e.stdout:
            print(f"    {e.stdout.strip()}")
        if e.stderr:
            print(f"    {e.stderr.strip()}")
        return False


def resolve_target(name: str) -> Path:
    """Resolve a name or path argument to an absolute .puml path."""
    p = Path(name)
    # If it's an absolute or relative path that exists, use it directly
    if p.exists():
        return p.resolve()
    # Strip extension if provided, look inside the plantuml dir
    stem = p.stem if p.suffix == ".puml" else p.name
    candidate = PLANTUML_DIR / f"{stem}.puml"
    if candidate.exists():
        return candidate
    print(f"✗ File not found: {name}")
    sys.exit(1)


def main():
    if not check_plantuml():
        print("plantuml not found.")
        sys.exit(1)

    if len(sys.argv) > 1:
        # Single file mode
        target = resolve_target(sys.argv[1])
        print(f"\nTarget: {target}\n")
        ok = convert(target)
        sys.exit(0 if ok else 1)

    # Batch mode — all .puml files in the plantuml directory
    puml_files = sorted(PLANTUML_DIR.glob("*.puml"))
    if not puml_files:
        print(f"✗ No .puml files found in {PLANTUML_DIR}")
        sys.exit(1)

    print(f"\nFound {len(puml_files)} diagram(s) in {PLANTUML_DIR}\n")

    successful, failed = 0, 0
    for f in puml_files:
        if convert(f):
            successful += 1
        else:
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  ✓ Successful : {successful}")
    if failed:
        print(f"  ✗ Failed     : {failed}")
    print(f"{'=' * 50}")

    if failed:
        sys.exit(1)
    print("\n✓ All diagrams converted successfully!")


if __name__ == "__main__":
    main()
