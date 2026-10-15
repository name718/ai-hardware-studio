import argparse
import json
import sys
from pathlib import Path

from hardware_studio.cad.parameters import BracketParameters
from hardware_studio.cad.service import CadService
from hardware_studio.portability import default_artifact_root, doctor, export_skills, mcp_config
from hardware_studio.shared.contracts import ToolResponse


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Hardware Studio CAD loop")
    parser.add_argument("--artifact-root", type=Path, default=default_artifact_root())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("schema", help="Print parameter schema and fictional demo values")
    health = sub.add_parser("doctor", help="Check macOS arm64 environment; never installs software")
    health.add_argument(
        "--probe-cad",
        action="store_true",
        help="Run real CAD and STEP/STL export; writes a fictional demo to the artifact root",
    )
    sub.add_parser(
        "mcp-config", help="Print client JSON using this machine's interpreter and data root"
    )
    export = sub.add_parser(
        "export-skills", help="Export the six packaged Skills to a new directory"
    )
    export.add_argument("destination", type=Path)
    build = sub.add_parser("build", help="Build a bracket from JSON parameters")
    build.add_argument("parameters", type=Path)
    read = sub.add_parser("inspect", help="Read a build and verify artifact integrity")
    read.add_argument("build_id")
    args = parser.parse_args()
    try:
        if args.command == "mcp-config":
            print(json.dumps(mcp_config(args.artifact_root), indent=2))
            return
        if args.command == "doctor":
            response = doctor(probe_cad=args.probe_cad, artifact_root=args.artifact_root)
        elif args.command == "export-skills":
            response = export_skills(args.destination)
        elif args.command == "schema":
            response = ToolResponse.success(
                parameter_schema=BracketParameters.model_json_schema(),
                demo_parameters=BracketParameters().model_dump(),
            )
        else:
            service = CadService(args.artifact_root)
            if args.command == "build":
                response = service.build(json.loads(args.parameters.read_text(encoding="utf-8")))
            else:
                response = service.get_build(args.build_id)
    except (OSError, ValueError) as exc:
        response = ToolResponse.failure("INPUT_ERROR", str(exc))
    print(response.model_dump_json(indent=2))
    sys.exit(0 if response.status == "ok" else 1)


if __name__ == "__main__":
    main()
