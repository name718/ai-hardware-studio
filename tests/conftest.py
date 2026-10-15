from pathlib import Path

import pytest

from hardware_studio.cad.service import CadService


@pytest.fixture(scope="session")
def built_bundle(tmp_path_factory):
    root: Path = tmp_path_factory.mktemp("cad-builds")
    service = CadService(root)
    result = service.build({})
    assert result.status == "ok", result.model_dump_json()
    return service, result.data
