"""Fail if a retired part name has crept back into the docs or scripts.

    python scripts/check_terminology.py

Every part in this project has exactly one name. The names drifted once --
the same bracket was an "ear" in the README and a "bracket" in the print
plate filenames, and the same slab was a "fan bar" in the prose and a "fan
plate" in the CAD -- so this pins them down. Standard library only, no
install needed, runs in well under a second.

Add a case to RULES when you retire a name. Add a case to ALLOWED when a
retired word is genuinely the right one in some specific spot, and say why
in the note -- an unexplained exemption is how the drift started.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEARCH = ("*.md", "*.html", "*.py")
SKIP_DIRS = {".git", "exports", "cad", "docs/images", "docs/models"}

# (retired pattern, the term to use instead, why)
RULES = [
    (r"\bbrackets?\b", "ear / front ear / rear ear",
     "the printed parts that bolt to the rack rails are ears"),
    (r"\bfan bars?\b", "fan plate",
     "the Fusion body is named Rear Fan Plate and it is a flat 4 mm slab"),
    (r"\bfan bores?\b", "fan opening",
     "bore is reserved for the rod, screw, and insert holes"),
    (r"\bcapture rails?\b", "duct rail",
     "matches the Fusion feature already named Duct rail"),
    (r"\bear rails?\b", "duct rail",
     "matches the Fusion feature already named Duct rail"),
    (r"rear_fan_bar", "rear_fan_plate",
     "renamed in the ear/fan plate cleanup"),
    (r"print_plate_brackets", "print_plate_ears",
     "renamed in the ear/fan plate cleanup"),
]

# (path, substring that must be on the line, why it is allowed to stay)
ALLOWED = [
    ("docs/index.html", "which is what I call the brackets",
     "a gloss that introduces the term 'ear' to a reader who expects "
     "'bracket'. It defines the vocabulary rather than drifting from it."),
    ("scripts/build_rack_mockup.py", "Brackets for Speaker Stand v2",
     "the exact name of a legacy Fusion document that grab_bodies() opens. "
     "Renaming the file would not rename the document inside Fusion."),
    ("scripts/check_terminology.py", "",
     "this file names every retired term on purpose."),
    ("CLAUDE.md", "",
     "the conventions file names every retired term on purpose."),
]


def allowed(rel_path, line):
    for path, needle, _ in ALLOWED:
        if rel_path == path and needle in line:
            return True
    return False


def files():
    for pattern in SEARCH:
        for path in sorted(ROOT.rglob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            if any(rel == d or rel.startswith(d + "/") for d in SKIP_DIRS):
                continue
            yield path, rel


def main():
    hits = []
    for path, rel in files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            if allowed(rel, line):
                continue
            for pattern, replacement, why in RULES:
                if re.search(pattern, line, re.IGNORECASE):
                    hits.append((rel, number, line.strip(), replacement, why))

    if not hits:
        checked = sum(1 for _ in files())
        print(f"terminology ok -- {checked} files, no retired terms")
        return 0

    print(f"{len(hits)} retired term(s) found:\n")
    for rel, number, line, replacement, why in hits:
        excerpt = line if len(line) <= 96 else line[:93] + "..."
        print(f"  {rel}:{number}")
        print(f"    {excerpt}")
        print(f"    use '{replacement}' -- {why}\n")
    print("If one of these is genuinely correct where it sits, add it to "
          "ALLOWED in this script with a note saying why.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
