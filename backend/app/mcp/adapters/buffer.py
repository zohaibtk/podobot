from app.mcp.client.unavailable import UnavailableMCPClient


class BufferMCPAdapter(UnavailableMCPClient):
    """Buffer adapter boundary; a production client must be configured before execution."""
