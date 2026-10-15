import json
import os
import subprocess
import sys
from pathlib import Path

from hardware_studio.portability import default_artifact_root, export_skills, mcp_config


def test_default_root_does_not_depend_on_client_working_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("HARDWARE_STUDIO_ARTIFACT_ROOT", raising=False)
    monkeypatch.delenv("HARDWARE_STUDIO_DATA_ROOT", raising=False)
    before = default_artifact_root()
    monkeypatch.chdir(tmp_path)
    assert default_artifact_root() == before
    assert before.is_absolute()


def test_explicit_data_and_artifact_roots(tmp_path, monkeypatch):
    monkeypatch.delenv("HARDWARE_STUDIO_ARTIFACT_ROOT", raising=False)
    monkeypatch.setenv("HARDWARE_STUDIO_DATA_ROOT", str(tmp_path))
    assert default_artifact_root() == tmp_path / "cad"
    monkeypatch.setenv("HARDWARE_STUDIO_ARTIFACT_ROOT", str(tmp_path / "custom"))
    assert default_artifact_root() == tmp_path / "custom"


def test_config_is_generated_for_the_target_environment(tmp_path):
    config = mcp_config(tmp_path / "path with spaces")
    server = config["mcpServers"]["hardware-studio-cad"]
    assert server["command"] == sys.executable
    assert server["args"] == ["-m", "hardware_studio.cad.server"]
    assert server["env"]["HARDWARE_STUDIO_ARTIFACT_ROOT"] == str(tmp_path / "path with spaces")


def test_export_all_skills_without_overwriting_user_files(tmp_path):
    destination = tmp_path / "portable skills"
    result = export_skills(destination)
    assert result.status == "ok"
    assert len(result.data["skills"]) == 6
    for name in result.data["skills"]:
        assert (destination / name / "SKILL.md").is_file()
    original = destination / "custom.txt"
    original.write_text("keep user content")
    assert export_skills(destination).error.code == "DESTINATION_EXISTS"
    assert original.read_text() == "keep user content"


def test_cli_config_and_diagnostics_work_outside_checkout(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["HARDWARE_STUDIO_DATA_ROOT"] = str(tmp_path / "data")
    result = subprocess.run(
        [sys.executable, "-m", "hardware_studio.cli", "mcp-config"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert (
        json.loads(result.stdout)["mcpServers"]["hardware-studio-cad"]["command"] == sys.executable
    )
    result = subprocess.run(
        [sys.executable, "-m", "hardware_studio.cli", "doctor"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert not data["docker_required"]
    assert not data["cad_kernel_executed"]
    assert not (tmp_path / "data").exists()
