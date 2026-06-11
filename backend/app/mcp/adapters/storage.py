from app.mcp.client.unavailable import UnavailableMCPClient


class StorageMCPAdapter(UnavailableMCPClient):
    """Storage adapter boundary; local file services handle storage outside MCP."""
