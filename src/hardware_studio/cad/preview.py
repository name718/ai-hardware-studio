"""Offline interactive preview of the actual OCC tessellation."""

import json
from pathlib import Path


def write_preview(shape, target: Path) -> int:
    vertices, triangles = shape.tessellate(0.1, 0.15)
    mesh = {
        "vertices": [[v.x, v.y, v.z] for v in vertices],
        "triangles": triangles,
    }
    template = Path(__file__).with_name("preview.html").read_text(encoding="utf-8")
    target.write_text(template.replace("__MESH_JSON__", json.dumps(mesh)), encoding="utf-8")
    return len(triangles)
