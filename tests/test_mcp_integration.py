import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.integration
def test_real_mcp_client_discovers_builds_reads_and_rejects_bad_input(tmp_path):
    async def scenario():
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        env["HARDWARE_STUDIO_ARTIFACT_ROOT"] = str(tmp_path)
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "hardware_studio.cad.server"],
            env=env,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = {tool.name: tool for tool in listed.tools}
                assert set(tools) == {
                    "cad_get_bracket_schema",
                    "cad_assess_parameters",
                    "cad_build_bracket",
                    "cad_get_build",
                }
                assert tools["cad_build_bracket"].inputSchema["properties"]["parameters"]
                assert tools["cad_build_bracket"].outputSchema
                schema = await session.call_tool("cad_get_bracket_schema", {})
                defaults = schema.structuredContent["data"]["demo_parameters"]
                result = await session.call_tool("cad_build_bracket", {"parameters": defaults})
                assert not result.isError
                assert result.structuredContent["status"] == "ok", result
                data = result.structuredContent["data"]
                assert Path(data["artifacts"]["bracket.step"]).stat().st_size > 1000
                read_back = await session.call_tool("cad_get_build", {"build_id": data["build_id"]})
                assert read_back.structuredContent["status"] == "ok"
                invalid = await session.call_tool(
                    "cad_build_bracket", {"parameters": {"hole_diameter": 20.0}}
                )
                assert invalid.isError
                escape = await session.call_tool("cad_get_build", {"build_id": "../outside"})
                assert escape.structuredContent["status"] == "error"
                assert escape.structuredContent["error"]["code"] == "INVALID_BUILD_ID"

    asyncio.run(asyncio.wait_for(scenario(), timeout=120))
