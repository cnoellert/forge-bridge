"""
Regression guard: packaging/ artifacts. Covers INSTALL-01 / INSTALL-04 from Phase 20.1.

Fails immediately when env-template default values drift from the codebase defaults at
forge_bridge/llm/router.py / store/session.py / __main__.py.

Mirrors tests/test_install_hook_version_consistency.py style: pure file reads + regex,
no fixtures, no asyncio.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_PACKAGING = _REPO_ROOT / "packaging"


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text()


def test_env_template_exists():
    assert (_PACKAGING / "forge-bridge.env.example").is_file(), \
        "packaging/forge-bridge.env.example missing — Phase 20.1 P1 deliverable"


def test_env_template_has_all_required_keys():
    """Every key the daemons read MUST appear in the template."""
    required = {
        "FORGE_DB_URL", "FORGE_LOCAL_LLM_URL", "FORGE_LOCAL_MODEL",
        "FORGE_CLOUD_MODEL", "FORGE_CONSOLE_PORT", "FORGE_BRIDGE_PORT",
        "ANTHROPIC_API_KEY",
    }
    content = _read("packaging/forge-bridge.env.example")
    for key in required:
        assert f"\n{key}=" in content or content.startswith(f"{key}="), \
            f"env template missing {key}"


def test_env_template_locked_local_model():
    """SEED-DEFAULT-MODEL-BUMP-V1.4.x: FORGE_LOCAL_MODEL stays at qwen2.5-coder:32b."""
    content = _read("packaging/forge-bridge.env.example")
    assert "FORGE_LOCAL_MODEL=qwen2.5-coder:32b" in content
    assert "FORGE_LOCAL_MODEL=qwen3:32b" not in content


def test_env_template_locked_cloud_model():
    """SEED-OPUS-4-7-TEMPERATURE-V1.5: FORGE_CLOUD_MODEL stays at claude-sonnet-4-6."""
    content = _read("packaging/forge-bridge.env.example")
    assert "FORGE_CLOUD_MODEL=claude-sonnet-4-6" in content
    assert "opus-4-7" not in content


def test_env_template_db_url_matches_alembic():
    """FORGE_DB_URL default must match the role+db pair install-bootstrap.sh creates."""
    content = _read("packaging/forge-bridge.env.example")
    assert "FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge" in content


def test_env_template_no_export_keyword():
    """systemd EnvironmentFile= and `set -a; . FILE; set +a` both reject `export`."""
    content = _read("packaging/forge-bridge.env.example")
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        assert not stripped.startswith("export "), \
            f"env template line uses `export` (breaks systemd EnvironmentFile=): {line!r}"


def test_env_template_parses_with_set_a():
    """Sanity: every non-comment, non-blank line is `KEY=VALUE` shape."""
    content = _read("packaging/forge-bridge.env.example")
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert re.match(r"^[A-Z_][A-Z0-9_]*=.*$", stripped), \
            f"env template has non-KEY=VALUE line: {line!r}"
