"""The `--env` file must be applied before anything reads the environment.

Both `cync_lan` and `cync_lan_mqtt` read their settings once, at import, and
this suite's conftest imports both - so each check runs in a fresh
interpreter, where the import order is the real one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPT = """
import sys
from cync_lan_mqtt import cli
assert not any(m.split(".")[0] in ("cync_lan",) for m in sys.modules), (
    "cli imported cync_lan before --env could be applied"
)
args, records = cli.prepare(["--env", sys.argv[1]])
from cync_lan_mqtt.const import CYNC_MQTT_HOST, CYNC_MQTT_USER
from cync_lan.const import CYNC_DEBUG
print(CYNC_MQTT_HOST, CYNC_MQTT_USER, CYNC_DEBUG, records[0][1].split(" from ")[0])
"""


def _run(env_file: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT, str(env_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_env_file_reaches_settings_read_at_import(tmp_path: Path):
    env_file = tmp_path / "cync.env"
    env_file.write_text(
        "CYNC_MQTT_HOST=broker.example\nCYNC_MQTT_USER=mqtt-user\nCYNC_DEBUG=1\n"
    )

    assert _run(env_file) == (
        "broker.example mqtt-user True Environment variables loaded"
    )


def test_a_missing_env_file_is_reported(tmp_path: Path):
    from cync_lan_mqtt import cli

    _, records = cli.prepare(["--env", str(tmp_path / "absent.env")])

    assert records and "does not exist" in records[0][1]
