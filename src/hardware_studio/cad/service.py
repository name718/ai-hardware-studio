import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from pydantic import ValidationError

from hardware_studio.cad.parameters import BracketParameters
from hardware_studio.shared.contracts import ToolResponse

BUILD_ID = re.compile(r"[0-9a-f]{32}\Z")
FILES = frozenset(
    {
        "parameters.json",
        "model.py",
        "bracket.step",
        "bracket.stl",
        "preview.html",
        "preview.svg",
        "report.json",
        "IMPORT_SHAPR3D.md",
    }
)


class CadService:
    def __init__(self, root: Path, timeout: float = 300):
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._slots = threading.BoundedSemaphore(2)

    def build(self, raw: dict) -> ToolResponse:
        try:
            parameters = BracketParameters.model_validate(raw)
        except ValidationError as exc:
            return ToolResponse.failure(
                "INVALID_PARAMETERS",
                "Invalid bracket parameters",
                errors=json.loads(exc.json(include_url=False)),
            )
        if not self._slots.acquire(blocking=False):
            return ToolResponse.failure("BUSY", "Two CAD builds are already running; retry later")
        build_id = uuid.uuid4().hex
        target = self.root / build_id
        try:
            target.mkdir(mode=0o700)
            env = os.environ.copy()
            # Use this installed/source package, independent of the client's cwd.
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
            env["XDG_CACHE_HOME"] = str(target / ".cache")
            env["MPLCONFIGDIR"] = str(target / ".cache" / "matplotlib")
            process = subprocess.run(
                [sys.executable, "-m", "hardware_studio.cad.worker", str(target)],
                input=parameters.model_dump_json(),
                capture_output=True,
                text=True,
                cwd=target,
                env=env,
                timeout=self.timeout,
                check=False,
            )
            (target / "worker.log").write_text(
                (process.stdout + process.stderr)[-16000:], encoding="utf-8"
            )
            if process.returncode:
                missing = "No module named 'cadquery'" in process.stderr
                response = ToolResponse.failure(
                    "DEPENDENCY_MISSING" if missing else "BUILD_FAILED",
                    "Install project dependencies"
                    if missing
                    else "CAD worker failed; inspect worker.log",
                    build_id=build_id,
                    exit_code=process.returncode,
                )
                self._save_failure(target, response)
                return response
            return self.get_build(build_id)
        except subprocess.TimeoutExpired:
            response = ToolResponse.failure(
                "BUILD_TIMEOUT", "CAD worker exceeded time limit", build_id=build_id
            )
            self._save_failure(target, response)
            return response
        except OSError as exc:
            return ToolResponse.failure("IO_ERROR", str(exc), build_id=build_id)
        finally:
            self._slots.release()

    @staticmethod
    def _save_failure(target: Path, response: ToolResponse) -> None:
        (target / "failure.json").write_text(response.model_dump_json(indent=2), encoding="utf-8")

    def get_build(self, build_id: str) -> ToolResponse:
        if not BUILD_ID.fullmatch(build_id):
            return ToolResponse.failure(
                "INVALID_BUILD_ID", "Use the 32-character build ID returned by cad_build_bracket"
            )
        root = self.root / build_id
        if root.is_symlink() or root.resolve().parent != self.root:
            return ToolResponse.failure(
                "PATH_FORBIDDEN", "Build path must stay inside the artifact root"
            )
        if not root.is_dir():
            return ToolResponse.failure("NOT_FOUND", "Build does not exist")
        try:
            manifest_path = self._safe_file(root, "manifest.json")
            if not manifest_path.exists():
                failure = self._safe_file(root, "failure.json")
                if failure.is_file():
                    return ToolResponse.model_validate_json(self._read_small(failure))
                return ToolResponse.failure("INCOMPLETE_BUILD", "Build has no completion manifest")
            manifest = json.loads(self._read_small(manifest_path))
            if manifest["build_id"] != build_id or set(manifest["files"]) != FILES:
                raise ValueError("Invalid manifest build ID or file list")
            for name, info in manifest["files"].items():
                file = self._safe_file(root, name)
                if file.stat().st_size > 20_000_000:
                    raise ValueError("Artifact exceeds size limit")
                if (
                    file.stat().st_size != info["bytes"]
                    or hashlib.sha256(file.read_bytes()).hexdigest() != info["sha256"]
                ):
                    raise ValueError(f"Artifact integrity check failed: {name}")
            report = json.loads(self._read_small(root / "report.json"))
            if (
                report.get("status") != "passed"
                or not report.get("checks")
                or not all(report["checks"].values())
            ):
                raise ValueError("Geometry report did not pass")
            return ToolResponse.success(
                build_id=build_id,
                artifact_directory=str(root),
                artifacts={name: str(root / name) for name in sorted(FILES)},
                manifest=manifest,
                report=report,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return ToolResponse.failure("ARTIFACT_INVALID", str(exc), build_id=build_id)

    @staticmethod
    def _safe_file(root: Path, name: str) -> Path:
        file = root / name
        if file.is_symlink() or file.resolve().parent != root:
            raise ValueError("Artifact symlinks and paths outside the build are forbidden")
        return file

    @staticmethod
    def _read_small(path: Path) -> str:
        if path.stat().st_size > 2_000_000:
            raise ValueError("JSON artifact exceeds size limit")
        return path.read_text(encoding="utf-8")
