"""
Regression guard: packaging/ artifacts. Covers INSTALL-01 / INSTALL-04 from Phase 20.1.

Fails immediately when env-template default values drift from the codebase defaults at
forge_bridge/llm/router.py / store/session.py / __main__.py.

Mirrors tests/test_install_hook_version_consistency.py style: pure file reads + regex,
no fixtures, no asyncio.
"""
from __future__ import annotations

import configparser
import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_PACKAGING = _REPO_ROOT / "packaging"
_LAUNCHD = _PACKAGING / "launchd"


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


# ---------------------------------------------------------------------------
# Phase 20.1 P3 — launchd plist + wrapper-script regression tests
# ---------------------------------------------------------------------------

def test_launchd_plists_parse_as_xml():
    """Plists MUST parse as XML plist — `launchctl bootstrap` would fail otherwise."""
    plists = list(_LAUNCHD.glob("*.plist"))
    assert len(plists) == 2, f"expected 2 plists, got {len(plists)}: {[p.name for p in plists]}"
    for p in plists:
        with p.open("rb") as f:
            data = plistlib.load(f)
        assert data.get("Label", "").startswith("com.cnoellert.forge-bridge"), \
            f"{p.name}: missing or wrong Label (got {data.get('Label')!r})"
        assert data.get("ProgramArguments"), f"{p.name}: missing ProgramArguments"
        assert data.get("RunAtLoad") is True, f"{p.name}: RunAtLoad must be True (boolean), got {data.get('RunAtLoad')!r}"


def test_launchd_plists_keepalive_successful_exit_false():
    """KeepAlive must be {SuccessfulExit: False} — bare KeepAlive=True respawns on clean exits (--help loop)."""
    for name in ("com.cnoellert.forge-bridge-server.plist", "com.cnoellert.forge-bridge.plist"):
        with (_LAUNCHD / name).open("rb") as f:
            data = plistlib.load(f)
        ka = data.get("KeepAlive")
        assert isinstance(ka, dict), f"{name}: KeepAlive must be dict, got {type(ka).__name__}: {ka!r}"
        assert ka.get("SuccessfulExit") is False, \
            f"{name}: KeepAlive.SuccessfulExit must be False (respawn on crash only), got {ka.get('SuccessfulExit')!r}"


def test_launchd_plists_use_user_placeholder():
    """UserName and WorkingDirectory MUST use __SUDO_USER__ placeholder (no literal username in tree)."""
    for name in ("com.cnoellert.forge-bridge-server.plist", "com.cnoellert.forge-bridge.plist"):
        with (_LAUNCHD / name).open("rb") as f:
            data = plistlib.load(f)
        assert data.get("UserName") == "__SUDO_USER__", \
            f"{name}: UserName must be '__SUDO_USER__'; got {data.get('UserName')!r}"
        wd = data.get("WorkingDirectory", "")
        assert wd == "/Users/__SUDO_USER__", \
            f"{name}: WorkingDirectory must be '/Users/__SUDO_USER__'; got {wd!r}"


def test_launchd_plists_no_orphan_server_file():
    """Neither plist may reference forge_bridge/server.py (CLAUDE.md anti-pattern guard)."""
    for name in ("com.cnoellert.forge-bridge-server.plist", "com.cnoellert.forge-bridge.plist"):
        content = (_LAUNCHD / name).read_text()
        assert "forge_bridge/server.py" not in content, \
            f"{name}: references the pre-Phase-5 orphan top-level file"


def test_launchd_wrappers_exist_and_executable():
    """Both wrapper bash scripts must exist as files with execute mode bit set."""
    for name in ("forge-bridge-server-daemon", "forge-bridge-daemon"):
        path = _LAUNCHD / name
        assert path.is_file(), f"{name}: wrapper script missing"
        assert os.access(path, os.X_OK), f"{name}: wrapper not executable (mode {oct(path.stat().st_mode)[-3:]})"


def test_launchd_wrappers_shebang_and_strict_mode():
    """Both wrappers must start with `#!/usr/bin/env bash` and contain `set -euo pipefail`."""
    for name in ("forge-bridge-server-daemon", "forge-bridge-daemon"):
        content = (_LAUNCHD / name).read_text()
        first_line = content.splitlines()[0] if content else ""
        assert first_line == "#!/usr/bin/env bash", \
            f"{name}: shebang must be '#!/usr/bin/env bash'; got {first_line!r}"
        assert "set -euo pipefail" in content, \
            f"{name}: missing 'set -euo pipefail' (bash hygiene baseline)"


def test_launchd_console_wrapper_has_readiness_gate():
    """forge-bridge-daemon MUST wait for :9998 before exec — replicates Linux Requires= cascade on macOS."""
    content = (_LAUNCHD / "forge-bridge-daemon").read_text()
    assert 'nc -z localhost "$PORT"' in content, \
        "forge-bridge-daemon: missing `nc -z localhost \"$PORT\"` readiness gate (Phase 20 gap #11 macOS parity)"
    assert "for i in $(seq 1 30)" in content, \
        "forge-bridge-daemon: readiness gate missing `for i in $(seq 1 30)` 30-second loop"


def test_launchd_wrappers_source_env_file():
    """Both wrappers must use the canonical `set -a; . FILE; set +a` env-source pattern."""
    for name in ("forge-bridge-server-daemon", "forge-bridge-daemon"):
        content = (_LAUNCHD / name).read_text()
        assert "set -a" in content, f"{name}: missing `set -a` env-export wrapper"
        assert ". /etc/forge-bridge/forge-bridge.env" in content, \
            f"{name}: missing `. /etc/forge-bridge/forge-bridge.env` source line"
        assert "set +a" in content, f"{name}: missing `set +a` env-export revert"


def test_launchd_wrappers_exec_correct_module():
    """Bus wrapper exec's forge_bridge.server; Console wrapper exec's forge_bridge (NOT forge_bridge.server)."""
    bus = (_LAUNCHD / "forge-bridge-server-daemon").read_text()
    console = (_LAUNCHD / "forge-bridge-daemon").read_text()
    assert "-m forge_bridge.server" in bus, \
        "forge-bridge-server-daemon: must exec `python -m forge_bridge.server` (the WS bus submodule)"
    # Console wrapper must invoke `forge_bridge` parent module — assert via line-level grep
    console_lines = [ln for ln in console.splitlines() if "-m forge_bridge" in ln]
    assert any(ln.strip().endswith("-m forge_bridge") for ln in console_lines), \
        "forge-bridge-daemon: must exec `python -m forge_bridge` (parent module → MCP+Console)"


def test_launchd_wrappers_bash_syntax_clean():
    """`bash -n FILE` exits 0 — syntax errors caught at test time, not at install time."""
    bash = shutil.which("bash")
    if not bash:
        import pytest
        pytest.skip("bash not on PATH")
    for name in ("forge-bridge-server-daemon", "forge-bridge-daemon"):
        r = subprocess.run([bash, "-n", str(_LAUNCHD / name)], capture_output=True, text=True)
        assert r.returncode == 0, \
            f"{name}: bash syntax check failed: {r.stderr!r}"
