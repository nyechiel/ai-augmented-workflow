"""
Minimal MCP time server with native streamable-http transport.
Single process, no subprocess, no memory leak.
"""
import os
from datetime import datetime
import pytz
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings

app = FastMCP("time-server")

DEFAULT_TZ = os.environ.get("TZ", "UTC")


@app.tool()
def get_current_time(timezone: str = DEFAULT_TZ) -> str:
    """Get the current time in the specified timezone."""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return f"Current time in {timezone}: {now.strftime('%Y-%m-%dT%H:%M:%S%z')} ({now.strftime('%A, %B %d %Y %H:%M %Z')})"


if __name__ == "__main__":
    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

    session_manager = StreamableHTTPSessionManager(
        app=app._mcp_server,
        event_store=None,
        json_response=False,
        stateless=True,
        security_settings=security,
    )

    from contextlib import asynccontextmanager
    from starlette.applications import Starlette
    from starlette.routing import Mount

    async def handle_mcp(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    @asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    starlette_app = Starlette(
        routes=[Mount("/mcp", app=handle_mcp)],
        lifespan=lifespan,
    )

    uvicorn.run(
        starlette_app,
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8086")),
    )
