import math
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from hardware_studio.cad.evidence import assess_accuracy
from hardware_studio.cad.parameters import BracketParameters
from hardware_studio.cad.service import CadService
from hardware_studio.portability import default_artifact_root
from hardware_studio.shared.contracts import ToolResponse


def create_server(root: Path, timeout: float = 300) -> FastMCP:
    if not math.isfinite(timeout) or not 1 <= timeout <= 600:
        raise ValueError("CAD timeout must be between 1 and 600 seconds")
    service = CadService(root, timeout=timeout)
    server = FastMCP("AI Hardware Studio CAD")

    @server.tool()
    def cad_get_bracket_schema() -> ToolResponse:
        """Return millimetre parameter schema and explicitly fictional demo defaults."""
        return ToolResponse.success(
            parameter_schema=BracketParameters.model_json_schema(),
            demo_parameters=BracketParameters().model_dump(),
        )

    @server.tool()
    def cad_assess_parameters(parameters: BracketParameters) -> ToolResponse:
        """Validate source records, nominal values and worst-case uncertainty before CAD."""
        return ToolResponse.success(
            parameters=parameters.model_dump(), accuracy=assess_accuracy(parameters)
        )

    @server.tool()
    def cad_build_bracket(parameters: BracketParameters) -> ToolResponse:
        """Build four-post bracket using real OCC; check status before consuming files.

        Only validated parameters are accepted. This tool does not execute user code.
        Success includes STEP/STL, offline 3D preview, source and hashed evidence.
        """
        return service.build(parameters.model_dump())

    @server.tool()
    def cad_get_build(build_id: str) -> ToolResponse:
        """Read a saved build and recheck all artifact SHA256 hashes."""
        return service.get_build(build_id)

    return server


def main() -> None:
    timeout = float(os.environ.get("HARDWARE_STUDIO_CAD_TIMEOUT_SECONDS", "300"))
    create_server(default_artifact_root(), timeout=timeout).run(transport="stdio")


if __name__ == "__main__":
    main()
