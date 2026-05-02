"""
Regression guard: packaging/ artifacts. Covers INSTALL-01 / INSTALL-04 from Phase 20.1.

Fails immediately when env-template default values drift from the codebase defaults at
forge_bridge/llm/router.py / store/session.py / __main__.py.

Mirrors tests/test_install_hook_version_consistency.py style: pure file reads + regex,
no fixtures, no asyncio.
"""
from __future__ import annotations

import configparser
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


def test_systemd_units_parse_as_ini():
    """Systemd unit files MUST parse as INI — `systemctl daemon-reload` would fail otherwise."""
    units = list((_PACKAGING / "systemd").glob("*.service"))
    assert len(units) == 2, f"expected 2 systemd units, got {len(units)}: {[u.name for u in units]}"
    for unit in units:
        cfg = configparser.RawConfigParser()
        cfg.read(unit)
        assert "Unit" in cfg.sections(), f"{unit.name}: missing [Unit] section"
        assert "Service" in cfg.sections(), f"{unit.name}: missing [Service] section"
        assert "Install" in cfg.sections(), f"{unit.name}: missing [Install] section"
        service_type = cfg.get("Service", "Type", fallback="simple")
        assert service_type in ("simple", "exec", "forking"), \
            f"{unit.name}: unsupported Type={service_type}"


def test_systemd_console_unit_requires_bus_unit():
    """Phase 20 gap #11 regression guard: forge-bridge.service MUST Requires=+After= the bus unit."""
    cfg = configparser.RawConfigParser()
    cfg.read(_PACKAGING / "systemd" / "forge-bridge.service")
    requires = cfg.get("Unit", "Requires", fallback="")
    after = cfg.get("Unit", "After", fallback="")
    assert "forge-bridge-server.service" in requires, \
        f"forge-bridge.service must Requires=forge-bridge-server.service (Phase 20 gap #11); got Requires={requires!r}"
    assert "forge-bridge-server.service" in after, \
        f"forge-bridge.service must After=forge-bridge-server.service (boot ordering); got After={after!r}"


def test_systemd_units_environment_file_path():
    """Both units must read /etc/forge-bridge/forge-bridge.env (matches P4 install target)."""
    for name in ("forge-bridge-server.service", "forge-bridge.service"):
        cfg = configparser.RawConfigParser()
        cfg.read(_PACKAGING / "systemd" / name)
        env_file = cfg.get("Service", "EnvironmentFile", fallback="")
        assert env_file == "/etc/forge-bridge/forge-bridge.env", \
            f"{name}: EnvironmentFile must point at /etc/forge-bridge/forge-bridge.env; got {env_file!r}"


def test_systemd_units_use_user_placeholder():
    """Both units MUST use __SUDO_USER__ placeholder, not a literal username."""
    for name in ("forge-bridge-server.service", "forge-bridge.service"):
        cfg = configparser.RawConfigParser()
        cfg.read(_PACKAGING / "systemd" / name)
        user = cfg.get("Service", "User", fallback="")
        group = cfg.get("Service", "Group", fallback="")
        assert user == "__SUDO_USER__", f"{name}: User must be __SUDO_USER__ placeholder; got {user!r}"
        assert group == "__SUDO_USER__", f"{name}: Group must be __SUDO_USER__ placeholder; got {group!r}"


def test_systemd_units_no_orphan_server_file():
    """Neither unit may reference forge_bridge/server.py — use the `forge_bridge.server` submodule."""
    for name in ("forge-bridge-server.service", "forge-bridge.service"):
        content = (_PACKAGING / "systemd" / name).read_text()
        assert "forge_bridge/server.py" not in content, \
            f"{name}: references the pre-Phase-5 orphan top-level file (CLAUDE.md anti-pattern)"


def test_systemd_units_standardinput_null():
    """Phase 20 gap #10 regression guard: StandardInput=null prevents stdio-handshake-exit on systemd."""
    for name in ("forge-bridge-server.service", "forge-bridge.service"):
        cfg = configparser.RawConfigParser()
        cfg.read(_PACKAGING / "systemd" / name)
        stdin = cfg.get("Service", "StandardInput", fallback="")
        assert stdin == "null", \
            f"{name}: StandardInput must be 'null' (Phase 20 gap #10); got {stdin!r}"


def test_systemd_postgres_is_soft_dep():
    """Phase 8 STORE-06: Postgres dep is Wants= (soft), NOT Requires= (would cascade-fail on DB maintenance)."""
    for name in ("forge-bridge-server.service", "forge-bridge.service"):
        cfg = configparser.RawConfigParser()
        cfg.read(_PACKAGING / "systemd" / name)
        requires = cfg.get("Unit", "Requires", fallback="")
        wants = cfg.get("Unit", "Wants", fallback="")
        assert "postgresql.service" not in requires, \
            f"{name}: postgresql.service in Requires= would cascade-fail on DB restart (Phase 8 STORE-06)"
        assert "postgresql.service" in wants, \
            f"{name}: postgresql.service must be in Wants= for ordering hint without cascade"
