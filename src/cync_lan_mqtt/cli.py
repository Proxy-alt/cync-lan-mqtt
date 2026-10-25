"""Console entry point (`cync-lan`).

Nothing from `cync_lan` or `cync_lan_mqtt` may be imported at module level
here. Both packages read their settings from the environment once, at
import, so the `--env` file has to be applied before the first such import
or it is silently ignored. It used to be loaded from inside `main.py`, after
`main.py` had already imported everything: an env file's `CYNC_MQTT_HOST`,
`CYNC_MQTT_USER`/`CYNC_MQTT_PASS`, exporter settings and the rest never took
effect, and the add-on fell back to `homeassistant.local` with no
credentials. `GlobalObject.reload_env()` could not rescue it, since it only
refreshes `g.env`, never a module constant.
"""

import argparse
import logging
from importlib.metadata import version
from pathlib import Path
from typing import Optional


def _load_env_file(env_path: Path) -> list[tuple[int, str]]:
    """Apply an env file, returning log records for once logging is set up.

    Logging is configured by `main.py` at import, which cannot happen yet.
    """
    env_path = env_path.expanduser().resolve()
    if not env_path.exists():
        return [(logging.ERROR, f"Environment file {env_path} does not exist")]
    try:
        import dotenv
    except ImportError:
        return [
            (
                logging.ERROR,
                "dotenv module is not installed. Please install it with "
                "'pip install python-dotenv'",
            )
        ]
    try:
        loaded_any = dotenv.load_dotenv(env_path, override=True)
    except Exception as e:
        return [(logging.ERROR, f"Failed to read environment file {env_path}: {e}")]
    if loaded_any:
        return [(logging.INFO, f"Environment variables loaded from {env_path}")]
    return [(logging.WARNING, f"No environment variables were loaded from {env_path}")]


def prepare(argv: Optional[list[str]] = None) -> tuple[argparse.Namespace, list]:
    """Parse the command line and apply `--env`, importing nothing configurable."""
    parser = argparse.ArgumentParser(description="Cync LAN Server")
    # The core library's version, as before - read from package metadata
    # rather than cync_lan.const, which would import it too early.
    parser.add_argument(
        "-V", "--version", action="version", version=version("cync-lan")
    )
    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--env", help="Path to the environment file", default=None, type=Path
    )
    args = parser.parse_args(argv)
    records = _load_env_file(args.env) if args.env else []
    return args, records


def main(argv: Optional[list[str]] = None) -> None:
    args, records = prepare(argv)
    from cync_lan_mqtt import main as app  # noqa: PLC0415 - must follow --env

    app.run(debug=args.debug, env_records=records)
