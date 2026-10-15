"""Build a relocatable source archive; never copies virtualenvs or host caches."""

import hashlib
import json
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "src",
    "skills",
    "agents",
    "mcp",
    "packages",
    "docs",
    "scripts",
    "tests",
    "examples",
    ".github",
)
FILES = ("AGENTS.md", "README.md", "pyproject.toml", "uv.lock", ".python-version", ".gitignore")
IGNORED = {"__pycache__", ".cache", ".DS_Store", ".venv", ".pytest_cache", ".ruff_cache"}


def build_archive(output: Path) -> Path:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    prefix = f"ai-hardware-studio-{version}"
    candidates = [ROOT / name for name in FILES]
    for name in DIRECTORIES:
        candidates.extend((ROOT / name).rglob("*"))
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"{prefix}-portable.zip"
    hashes = {}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(candidates):
            relative = file.relative_to(ROOT)
            if not file.is_file() or file.is_symlink() or any(p in IGNORED for p in relative.parts):
                continue
            if (
                file.suffix in (".pyc", ".pyo")
                or file.name == "worker.log"
                or file.name.startswith(".env")
            ):
                continue
            content = file.read_bytes()
            hashes[relative.as_posix()] = hashlib.sha256(content).hexdigest()
            archive.writestr(f"{prefix}/{relative.as_posix()}", content)
        archive.writestr(
            f"{prefix}/SOURCE_MANIFEST.json",
            json.dumps(
                {
                    "version": version,
                    "files": hashes,
                },
                indent=2,
            )
            + "\n",
        )
    destination.with_suffix(".zip.sha256").write_text(
        hashlib.sha256(destination.read_bytes()).hexdigest() + "  " + destination.name + "\n"
    )
    return destination


if __name__ == "__main__":
    print(build_archive(ROOT / "dist"))
