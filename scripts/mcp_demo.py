"""Exercise a real stdio MCP session and save its structured execution evidence."""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(root: Path, parameter_file: Path, evidence_file: Path) -> None:
    env = os.environ.copy()
    env["HARDWARE_STUDIO_ARTIFACT_ROOT"] = str(root.resolve())
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "hardware_studio.cad.server"], env=env
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            listed = await session.list_tools()
            schema = await session.call_tool("cad_get_bracket_schema", {})
            assessed = await session.call_tool(
                "cad_assess_parameters", {"parameters": json.loads(parameter_file.read_text())}
            )
            if assessed.isError or assessed.structuredContent["status"] != "ok":
                raise RuntimeError(str(assessed))
            result = await session.call_tool(
                "cad_build_bracket", {"parameters": json.loads(parameter_file.read_text())}
            )
            payload = result.structuredContent
            if result.isError or not payload or payload["status"] != "ok":
                raise RuntimeError(str(result))
            retrieved = await session.call_tool(
                "cad_get_build", {"build_id": payload["data"]["build_id"]}
            )
            if retrieved.isError or retrieved.structuredContent["status"] != "ok":
                raise RuntimeError(str(retrieved))
            # Persist logical artifact references so evidence survives moving computers.
            portable_payload = json.loads(json.dumps(payload))
            build_id = payload["data"]["build_id"]
            portable_payload["data"]["artifact_directory"] = build_id
            portable_payload["data"]["artifacts"] = {
                name: f"{build_id}/{name}" for name in payload["data"]["artifacts"]
            }
            try:
                relative_root = Path(
                    os.path.relpath(root.resolve(), evidence_file.resolve().parent)
                ).as_posix()
            except ValueError:
                relative_root = None
            evidence = {
                "schema_version": 2,
                "path_kind": "artifact-root-relative",
                "artifact_root_relative_to_evidence": relative_root,
                "executed_at": datetime.now(UTC).isoformat(),
                "transport": "stdio",
                "initialize": initialized.model_dump(mode="json"),
                "tools": [t.model_dump(mode="json") for t in listed.tools],
                "schema_status": schema.structuredContent["status"],
                "assessment": assessed.structuredContent,
                "build": portable_payload,
                "retrieval_status": retrieved.structuredContent["status"],
            }
            evidence_file.parent.mkdir(parents=True, exist_ok=True)
            evidence_file.write_text(json.dumps(evidence, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "build_id": payload["data"]["build_id"],
                        "artifacts": payload["data"]["artifacts"],
                        "evidence": str(evidence_file.resolve()),
                    },
                    indent=2,
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=Path("artifacts/cad"))
    parser.add_argument(
        "--parameters", type=Path, default=Path("examples/desktop-robot/bracket.parameters.json")
    )
    parser.add_argument("--evidence", type=Path, default=Path("artifacts/mcp-evidence.json"))
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(run(args.artifact_root, args.parameters, args.evidence), 150))
