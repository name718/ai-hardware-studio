import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import cadquery as cq
import pytest
import trimesh

from hardware_studio.cad.parameters import BracketParameters
from hardware_studio.cad.service import CadService

pytestmark = pytest.mark.integration


def test_real_step_geometry_has_four_open_holes_and_four_walls(built_bundle):
    _, data = built_bundle
    shape = cq.importers.importStep(data["artifacts"]["bracket.step"]).val()
    assert shape.isValid()
    assert len(shape.Solids()) == 1
    solid = shape.Solids()[0]
    box = solid.BoundingBox()
    assert (box.xlen, box.ylen, box.zlen) == pytest.approx((74, 54, 11))
    for x, y in BracketParameters().centres:
        # Independently sample the STEP roundtrip, not the report booleans.
        for z in (0.1, 2.9, 3.1, 10.9):
            assert not solid.isInside(cq.Vector(x, y, z))
            assert solid.isInside(cq.Vector(x + 2.5, y, z))
    assert solid.Volume() > 0


def test_stl_is_watertight_and_matches_step(built_bundle):
    _, data = built_bundle
    mesh = trimesh.load_mesh(data["artifacts"]["bracket.stl"])
    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    # Face adjacency traversal avoids an optional SciPy/networkx test dependency.
    neighbours = [set() for _ in mesh.faces]
    for a, b in mesh.face_adjacency:
        neighbours[a].add(b)
        neighbours[b].add(a)
    visited, pending = set(), [0]
    while pending:
        face = pending.pop()
        if face not in visited:
            visited.add(face)
            pending.extend(neighbours[face] - visited)
    assert len(visited) == len(mesh.faces)
    assert mesh.extents == pytest.approx([74, 54, 11], abs=1e-4)
    assert math.isclose(mesh.volume, data["report"]["volume_mm3"], rel_tol=0.005)


def test_bundle_contains_real_preview_source_and_versions(built_bundle):
    service, data = built_bundle
    assert service.get_build(data["build_id"]).status == "ok"
    html = Path(data["artifacts"]["preview.html"]).read_text()
    mesh = json.loads(html.split("const mesh=", 1)[1].split(";", 1)[0])
    assert len(mesh["vertices"]) > 100
    assert len(mesh["triangles"]) > 100
    assert all(max(t) < len(mesh["vertices"]) for t in mesh["triangles"])
    assert "__MESH_JSON__" not in html
    assert data["manifest"]["dependencies"]["cadquery"]
    assert data["manifest"]["template_version"] == "bracket-v1"


def test_preview_javascript_projection_and_interactions(built_bundle):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed; preview JavaScript runtime not tested")
    _, data = built_bundle
    result = subprocess.run(
        [
            node,
            str(Path(__file__).with_name("preview_runtime.cjs")),
            data["artifacts"]["preview.html"],
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_saved_source_replays_without_studio_imports(built_bundle, tmp_path):
    _, data = built_bundle
    for name in ("model.py", "parameters.json"):
        (tmp_path / name).write_bytes(Path(data["artifacts"][name]).read_bytes())
    process = subprocess.run(
        [sys.executable, str(tmp_path / "model.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert process.returncode == 0, process.stderr
    replayed = cq.importers.importStep(str(tmp_path / "replayed.step")).val()
    assert replayed.Volume() == pytest.approx(data["report"]["volume_mm3"], rel=1e-7)


def test_changed_parameters_change_real_geometry(tmp_path):
    result = CadService(tmp_path).build(
        {
            "base_length": 90.0,
            "base_width": 70.0,
            "hole_pitch_x": 60.0,
            "hole_pitch_y": 40.0,
            "standoff_height": 12.0,
            "corner_radius": 0.0,
        }
    )
    assert result.status == "ok", result.model_dump_json()
    mesh = trimesh.load_mesh(result.data["artifacts"]["bracket.stl"])
    assert mesh.is_watertight
    assert mesh.extents == pytest.approx([90, 70, 15], abs=1e-4)
    solid = cq.importers.importStep(result.data["artifacts"]["bracket.step"]).val().Solids()[0]
    for x in (-30, 30):
        for y in (-20, 20):
            assert not solid.isInside(cq.Vector(x, y, 14))
            assert solid.isInside(cq.Vector(x + 2.5, y, 14))
