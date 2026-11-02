"""Build Smart_Trim_Fuse_submission.zip from the canonical files only (see PROJECT_MAP.md).

Left out: virtual environments, caches, bytecode, editor settings, the _archive backups, the Power BI dashboard and
the company's problem statement (kept locally, not published), and files the notebooks regenerate
(Colab Notebook/cleaned/, the notebook folder's copies of the .joblib models and evaluation_06.json; the canonical
copies are in Smart Trim Fuse/models/). The same rules are in .gitignore.

Run from this folder:  python make_submission.py
"""

import fnmatch
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Smart_Trim_Fuse_submission.zip"
EXCLUDE_DIRS = {".venv", "venv", "env", ".ruff_cache", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".vscode",
                ".idea", "_archive", ".git", "cleaned"}
EXCLUDE_FILES = ["*.pyc", "*.pyo", "*.zip", "~$*", ".DS_Store", "Thumbs.db", "desktop.ini",
                 "Colab Notebook/*.joblib", "Colab Notebook/evaluation_06.json",
                 "Deliverables/Power BI/*", "AI Trim & Fuse/*.docx", "AI Trim & Fuse/*.pdf",
                 "Smart Trim Fuse/app/views/archive/*"]


def included(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    if any(part in EXCLUDE_DIRS for part in p.relative_to(ROOT).parts[:-1]):
        return False
    return not any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(p.name, pat) for pat in EXCLUDE_FILES)


def main():
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and included(p))
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, Path("Trim Fuse") / p.relative_to(ROOT))
    print(f"{OUT.name}: {len(files)} files, {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
