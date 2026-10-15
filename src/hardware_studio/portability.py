"""Machine-independent paths, client configuration and portable skill export."""

import importlib.metadata
import os
import platform
import shutil
import sys
from pathlib import Path

from hardware_studio import __version__
from hardware_studio.shared.contracts import ToolResponse


def default_artifact_root() -> Path:
    configured = os.environ.get("HARDWARE_STUDIO_ARTIFACT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    data = os.environ.get("HARDWARE_STUDIO_DATA_ROOT")
    if data:
        return Path(data).expanduser().resolve() / "cad"
    if sys.platform == "win32":
        home = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    elif sys.platform == "darwin":
        home = Path.home() / "Library" / "Application Support"
    else:
        home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return home / "ai-hardware-studio" / "cad"


def mcp_config(root: Path) -> dict:
    return {
        "mcpServers": {
            "hardware-studio-cad": {
                "command": sys.executable,
                "args": ["-m", "hardware_studio.cad.server"],
                "env": {"HARDWARE_STUDIO_ARTIFACT_ROOT": str(root.expanduser().resolve())},
            }
        }
    }


def skill_root() -> Path:
    packaged = Path(__file__).resolve().parent / "bundle" / "skills"
    if packaged.is_dir():
        return packaged
    source = Path(__file__).resolve().parents[2] / "skills"
    if source.is_dir():
        return source
    raise FileNotFoundError("Packaged Skills were not found; reinstall the complete wheel")


def export_skills(destination: Path) -> ToolResponse:
    destination = destination.expanduser().resolve()
    if destination.exists():
        return ToolResponse.failure(
            "DESTINATION_EXISTS", "Choose a new directory; existing Skills will not be overwritten"
        )
    source = skill_root()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return ToolResponse.success(
        directory=str(destination),
        skills=sorted(p.name for p in destination.iterdir() if (p / "SKILL.md").is_file()),
    )


def doctor(*, probe_cad: bool = False, artifact_root: Path | None = None) -> ToolResponse:
    packages = {}
    for name in ("cadquery", "cadquery-ocp", "mcp", "pydantic"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    optional = {name: shutil.which(name) for name in ("kicad-cli", "pio")}
    data = {
        "studio_version": __version__,
        "python": sys.version.split()[0],
        "python_supported": sys.version_info[:2] == (3, 12),
        "platform": sys.platform,
        "architecture": platform.machine(),
        "platform_supported": sys.platform == "darwin" and platform.machine() == "arm64",
        "required_packages": packages,
        "optional_executables": optional,
        "docker_required": False,
        "artifact_root": str(artifact_root or default_artifact_root()),
        "cad_kernel_executed": False,
        "cad_probe_requested": probe_cad,
        "note": "Metadata checks only; tool discovery does not execute or install software",
    }
    if not data["platform_supported"] or not data["python_supported"] or not all(packages.values()):
        return ToolResponse.failure(
            "ENVIRONMENT_INCOMPLETE",
            "Requires native macOS arm64, Python 3.12 and the locked project dependencies",
            diagnostics=data,
        )
    if probe_cad:
        from hardware_studio.cad.service import CadService

        result = CadService(artifact_root or default_artifact_root()).build({})
        data["cad_kernel_executed"] = result.status == "ok"
        if result.status != "ok":
            return ToolResponse.failure(
                "CAD_PROBE_FAILED",
                "Real CAD environment check failed",
                diagnostics=data,
                build_error=result.error.model_dump(),
            )
        data["cad_probe"] = {
            "build_id": result.data["build_id"],
            "artifact_directory": result.data["artifact_directory"],
            "checks": result.data["report"]["checks"],
            "dimension_source": "fictional_demo",
        }
        data["note"] = "Real CAD build, STEP roundtrip and artifact integrity checks passed"
    return ToolResponse.success(**data)
