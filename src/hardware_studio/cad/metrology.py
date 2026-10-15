"""Measure actual analytic faces; input values are never copied as measurements."""

import math

TOLERANCE_MM = 1e-5


def measure_features(shape, parameters) -> dict:
    holes, posts = [], []
    total_height = parameters.base_thickness + parameters.standoff_height
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        cylinder = face._geomAdaptor().Cylinder()
        if abs(abs(cylinder.Axis().Direction().Z()) - 1) > 1e-8:
            continue
        box = face.BoundingBox()
        axis = cylinder.Axis().Location()
        measured = {
            "centre_mm": [axis.X(), axis.Y()],
            "diameter_mm": 2 * cylinder.Radius(),
            "z_min_mm": box.zmin,
            "z_max_mm": box.zmax,
            "height_mm": box.zlen,
        }
        if abs(box.zmin) < TOLERANCE_MM and abs(box.zmax - total_height) < TOLERANCE_MM:
            holes.append(measured)
        elif (
            abs(box.zmin - parameters.base_thickness) < TOLERANCE_MM
            and abs(box.zmax - total_height) < TOLERANCE_MM
        ):
            posts.append(measured)
    holes.sort(key=lambda item: item["centre_mm"])
    posts.sort(key=lambda item: item["centre_mm"])

    def matches(features: list, diameter: float) -> bool:
        if len(features) != 4:
            return False
        remaining = list(parameters.centres)
        for feature in features:
            nearest = min(remaining, key=lambda p: math.dist(feature["centre_mm"], p))
            if (
                math.dist(feature["centre_mm"], nearest) >= TOLERANCE_MM
                or abs(feature["diameter_mm"] - diameter) >= TOLERANCE_MM
            ):
                return False
            remaining.remove(nearest)
        return True

    return {
        "measurement_method": "OpenCascade analytic cylindrical faces",
        "comparison_tolerance_mm": TOLERANCE_MM,
        "holes": holes,
        "posts": posts,
        "checks": {
            "hole_axes_and_diameters_match": matches(holes, parameters.hole_diameter),
            "post_axes_and_diameters_match": matches(posts, parameters.standoff_diameter),
        },
    }
