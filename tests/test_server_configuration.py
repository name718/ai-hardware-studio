import pytest

from hardware_studio.cad.server import create_server


@pytest.mark.parametrize("timeout", [0, -1, 601, float("nan"), float("inf")])
def test_server_rejects_unbounded_or_invalid_timeouts(tmp_path, timeout):
    with pytest.raises(ValueError, match="timeout"):
        create_server(tmp_path, timeout=timeout)
