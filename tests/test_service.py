import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from hardware_studio.cad.service import CadService


def test_invalid_input_creates_no_artifact(tmp_path):
    service = CadService(tmp_path)
    result = service.build({"hole_diameter": 99.0})
    assert result.error.code == "INVALID_PARAMETERS"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("build_id", ["../outside", "/etc/passwd", "A" * 32, "a" * 31])
def test_build_id_cannot_escape_root(tmp_path, build_id):
    assert CadService(tmp_path).get_build(build_id).error.code == "INVALID_BUILD_ID"


def test_symlinked_build_is_rejected(tmp_path):
    root = tmp_path / "builds"
    service = CadService(root)
    (root / ("a" * 32)).symlink_to(tmp_path, target_is_directory=True)
    assert service.get_build("a" * 32).error.code == "PATH_FORBIDDEN"


def test_symlinked_manifest_is_rejected(tmp_path):
    service = CadService(tmp_path)
    build = tmp_path / ("b" * 32)
    build.mkdir()
    (build / "manifest.json").symlink_to(tmp_path / "outside.json")
    assert service.get_build(build.name).error.code == "ARTIFACT_INVALID"


def test_incomplete_build_never_claims_success(tmp_path):
    service = CadService(tmp_path)
    (tmp_path / ("c" * 32)).mkdir()
    assert service.get_build("c" * 32).error.code == "INCOMPLETE_BUILD"


def test_timeout_is_structured_and_persistent(tmp_path):
    service = CadService(tmp_path, timeout=0.1)
    with patch(
        "hardware_studio.cad.service.subprocess.run",
        side_effect=subprocess.TimeoutExpired("worker", 0.1),
    ):
        result = service.build({})
    assert result.error.code == "BUILD_TIMEOUT"
    assert service.get_build(result.error.details["build_id"]).error.code == "BUILD_TIMEOUT"
    assert not list(tmp_path.glob("*/manifest.json"))


def test_worker_failure_never_claims_success(tmp_path):
    service = CadService(tmp_path)
    with patch(
        "hardware_studio.cad.service.subprocess.run",
        return_value=subprocess.CompletedProcess([], 1, "", "Geometry failed"),
    ):
        result = service.build({})
    assert result.error.code == "BUILD_FAILED"
    assert not list(tmp_path.glob("*/manifest.json"))


def test_concurrency_is_bounded(tmp_path):
    service = CadService(tmp_path)
    service._slots.acquire()
    service._slots.acquire()
    try:
        assert service.build({}).error.code == "BUSY"
        assert not list(tmp_path.iterdir())
    finally:
        service._slots.release()
        service._slots.release()


@pytest.mark.integration
def test_artifact_tampering_is_detected(built_bundle):
    service, data = built_bundle
    file = Path(data["artifacts"]["parameters.json"])
    original = file.read_bytes()
    try:
        file.write_text(json.dumps({"base_length": 999}))
        assert service.get_build(data["build_id"]).error.code == "ARTIFACT_INVALID"
    finally:
        file.write_bytes(original)
