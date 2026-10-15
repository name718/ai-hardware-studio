import subprocess
from pathlib import Path

import pytest

from hardware_studio.portability import doctor


@pytest.mark.parametrize("machine", ["x86_64", "AMD64"])
def test_doctor_rejects_non_arm64_interpreter(monkeypatch, machine):
    monkeypatch.setattr("hardware_studio.portability.platform.machine", lambda: machine)
    result = doctor()
    assert result.status == "error"
    assert not result.error.details["diagnostics"]["platform_supported"]


def test_doctor_rejects_other_operating_systems(monkeypatch):
    monkeypatch.setattr("hardware_studio.portability.sys.platform", "linux")
    assert doctor().error.code == "ENVIRONMENT_INCOMPLETE"


def test_bootstrap_script_reports_missing_venv_without_installing(tmp_path):
    scripts = tmp_path / "relocated project" / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "check_environment.sh"
    script.write_bytes(
        (Path(__file__).resolve().parents[1] / "scripts/check_environment.sh").read_bytes()
    )
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert ".venv is missing" in result.stdout
    assert "uv sync --locked" in result.stdout
    assert not (scripts.parent / ".venv").exists()


@pytest.mark.integration
def test_doctor_probes_real_cad(tmp_path):
    result = doctor(probe_cad=True, artifact_root=tmp_path)
    assert result.status == "ok", result.model_dump_json()
    assert result.data["cad_kernel_executed"]
    assert all(result.data["cad_probe"]["checks"].values())
    assert result.data["cad_probe"]["dimension_source"] == "fictional_demo"
