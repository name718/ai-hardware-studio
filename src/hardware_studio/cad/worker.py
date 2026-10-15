"""Fixed subprocess entry point. Reads one validated parameter object from stdin."""

import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from hardware_studio import __version__
from hardware_studio.cad.evidence import assess_accuracy
from hardware_studio.cad.metrology import measure_features
from hardware_studio.cad.parameters import BracketParameters


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_bundle(root: Path, parameters: BracketParameters) -> dict:
    import cadquery as cq

    from hardware_studio.cad import model
    from hardware_studio.cad.preview import write_preview

    p = parameters.model_dump()
    (root / "parameters.json").write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    (root / "model.py").write_text(Path(model.__file__).read_text(), encoding="utf-8")
    workplane = model.build_model(p)
    shape = workplane.val()
    bbox = shape.BoundingBox()
    actual = [bbox.xlen, bbox.ylen, bbox.zlen]
    expected = [p["base_length"], p["base_width"], p["base_thickness"] + p["standoff_height"]]
    volume = shape.Volume()
    base_area = p["base_length"] * p["base_width"] - (4 - math.pi) * p["corner_radius"] ** 2
    analytical_volume = (
        base_area * p["base_thickness"]
        + math.pi * p["standoff_diameter"] ** 2 * p["standoff_height"]
        - math.pi * p["hole_diameter"] ** 2 * expected[2]
    )
    solid_list = shape.Solids()
    features = measure_features(shape, parameters)
    holes = []
    for x, y in parameters.centres:
        probe = cq.Solid.makeCylinder(
            p["hole_diameter"] / 2 - 1e-4, expected[2], cq.Vector(x, y, 0)
        )
        obstruction = shape.intersect(probe).Volume()
        wall_probe = cq.Vector(
            x + (p["hole_diameter"] + p["standoff_diameter"]) / 4,
            y,
            p["base_thickness"] + p["standoff_height"] / 2,
        )
        holes.append(
            {
                "centre_mm": [x, y],
                "obstruction_mm3": obstruction,
                "through": abs(obstruction) < 1e-6,
                "post_wall_present": len(solid_list) == 1 and solid_list[0].isInside(wall_probe),
            }
        )
    checks = {
        "brep_valid": shape.isValid(),
        "single_solid": len(solid_list) == 1,
        "bounding_box_matches": all(
            abs(a - b) < 1e-5 for a, b in zip(actual, expected, strict=True)
        ),
        "volume_matches_analytic": math.isclose(volume, analytical_volume, rel_tol=1e-7),
        "four_through_holes": all(h["through"] for h in holes),
        "four_post_walls": all(h["post_wall_present"] for h in holes),
        **features["checks"],
    }
    if not all(checks.values()):
        raise RuntimeError(f"CAD geometry verification failed: {checks}")

    cq.exporters.export(workplane, str(root / "bracket.step"))
    cq.exporters.export(workplane, str(root / "bracket.stl"), tolerance=0.05, angularTolerance=0.1)
    imported = cq.importers.importStep(str(root / "bracket.step")).val()
    roundtrip_features = measure_features(imported, parameters)
    checks["step_roundtrip_valid"] = (
        imported.isValid()
        and len(imported.Solids()) == 1
        and math.isclose(imported.Volume(), volume, rel_tol=1e-7)
        and all(roundtrip_features["checks"].values())
    )
    if not checks["step_roundtrip_valid"]:
        raise RuntimeError("STEP roundtrip verification failed")
    triangles = write_preview(shape, root / "preview.html")
    cq.exporters.export(workplane, str(root / "preview.svg"))

    report = {
        "schema_version": 2,
        "status": "passed",
        "units": "mm",
        "dimension_source": p["dimension_source"],
        "source_note": p["source_note"],
        "bounding_box_mm": actual,
        "volume_mm3": volume,
        "analytic_volume_mm3": analytical_volume,
        "solid_count": len(solid_list),
        "holes": holes,
        "measured_features": features,
        "step_measured_features": roundtrip_features,
        "dimension_accuracy": assess_accuracy(parameters),
        "checks": checks,
        "preview_triangle_count": triangles,
        "stl_tolerance_mm": 0.05,
        "stl_angular_tolerance_rad": 0.1,
        "not_verified": [
            "Real PCB fit and component/connector clearances",
            "Strength, thermal behaviour and dynamic loads",
            "Printing tolerances, material process and screw fit",
            "Shapr3D desktop import and physical assembly",
        ],
    }
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (root / "IMPORT_SHAPR3D.md").write_text(
        "# Shapr3D 导入\n\n在 Shapr3D 中通过导入功能选择 bracket.step，核对单位为 mm，"
        "测量底座与孔距后再编辑实体。STL 是网格，优先用 STEP 编辑。\n\n"
        f"尺寸来源：{p['dimension_source']}。原始说明见 parameters.json。\n\n"
        "数据来源与误差范围见 report.json 的 dimension_accuracy；来源仅为记录，"
        "未经独立真实性审核。CAD 数值校验精度不等于制造精度。\n\n"
        "尚未实际验证 Shapr3D 桌面导入或真实 PCB 装配。打印前核对所有板孔、接口、"
        "螺钉和元件空间；几何报告不代表强度或制造认证。\n",
        encoding="utf-8",
    )
    filenames = [
        "parameters.json",
        "model.py",
        "bracket.step",
        "bracket.stl",
        "preview.html",
        "preview.svg",
        "report.json",
        "IMPORT_SHAPR3D.md",
    ]
    manifest = {
        "schema_version": 1,
        "build_id": root.name,
        "created_at": datetime.now(UTC).isoformat(),
        "studio_version": __version__,
        "template_version": model.TEMPLATE_VERSION,
        "python_version": platform.python_version(),
        "dependencies": {name: version(name) for name in ("cadquery", "cadquery-ocp", "mcp")},
        "files": {
            name: {"sha256": digest(root / name), "bytes": (root / name).stat().st_size}
            for name in filenames
        },
    }
    # Completion marker is published only after every check and export succeeds.
    pending = root / "manifest.pending"
    pending.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    pending.replace(root / "manifest.json")
    return manifest


def main() -> None:
    root = Path(sys.argv[1]).resolve(strict=True)
    parameters = BracketParameters.model_validate_json(sys.stdin.read(16384))
    build_bundle(root, parameters)


if __name__ == "__main__":
    main()
