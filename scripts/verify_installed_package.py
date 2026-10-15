"""Run with a fresh wheel-installed interpreter, outside the source checkout."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import hardware_studio


async def verify(work: Path) -> dict:
    origin = Path(hardware_studio.__file__).resolve()
    assert origin.is_relative_to(Path(sys.prefix).resolve()), (
        "Package is not from this installation"
    )
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    cwd = work / "different working directory"
    cwd.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    artifact_root = work / "generated parts"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "hardware_studio.cli",
            "--artifact-root",
            str(artifact_root),
            "mcp-config",
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    config = json.loads(process.stdout)["mcpServers"]["hardware-studio-cad"]
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "hardware_studio.cli",
            "export-skills",
            str(work / "exported skills"),
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    exported = json.loads(process.stdout)
    assert exported["status"] == "ok" and len(exported["data"]["skills"]) == 6
    env.update(config["env"])
    server = StdioServerParameters(
        command=config["command"], args=config["args"], env=env, cwd=str(cwd)
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert len(listed.tools) == 4
            built = await session.call_tool("cad_build_bracket", {"parameters": {}})
            assert not built.isError and built.structuredContent["status"] == "ok", built
            data = built.structuredContent["data"]
            assert Path(data["artifact_directory"]).parent == artifact_root
            assert all(data["report"]["checks"].values())
            retrieved = await session.call_tool("cad_get_build", {"build_id": data["build_id"]})
            assert retrieved.structuredContent["status"] == "ok"
    result = {
        "studio_version": hardware_studio.__version__,
        "isolated_wheel_install": True,
        "source_checkout_on_pythonpath": False,
        "working_directory_contains_spaces": True,
        "exported_skill_count": 6,
        "mcp_tool_count": 4,
        "mcp_build_and_integrity_readback": "passed",
        "geometry_checks": data["report"]["checks"],
        "platform": sys.platform,
        "other_operating_systems_executed": False,
    }
    (work / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(asyncio.wait_for(verify(args.work_directory), 420)), indent=2))
