"""forge-bridge CLI package — sync Typer subcommands consuming /api/v1/*.

P-01 stdout-purity guard: FastMCP's `configure_logging()` (invoked at import
time when `forge_bridge.mcp.server` is loaded) installs a RichHandler at INFO
on the root logger. That handler renders every httpx INFO log into stdout via
Rich, which would corrupt `--json` output. The CLI never needs httpx INFO
chatter — silence it at WARNING so `--json` stays parseable. (Rule 2: critical
correctness requirement for the locked P-01 contract.)
"""
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
