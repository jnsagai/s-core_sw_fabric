"""Fixture setup server: the fake context server plus a setup-privileged tool."""

import fake_mcp

fake_mcp.SETUP = True
fake_mcp.main()
