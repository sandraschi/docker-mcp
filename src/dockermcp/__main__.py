"""
Docker MCP Server - ``python -m dockermcp`` entry point.

Delegates to dockermcp.server.main (stdio transport plus the web bridge), the
same entry the docker-mcp console script uses. The previous body imported the
tools and then idled in a ``while not should_exit: sleep`` loop without ever
starting a transport, so this entry never answered ``initialize``.
"""

import sys

from dockermcp.server import main

if __name__ == "__main__":
    sys.exit(main())
