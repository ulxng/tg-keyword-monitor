import sys
from dataclasses import dataclass

import yaml


@dataclass
class MonitorConfig:
    api_id: int
    api_secret: str
    destination_chat: str | int
    keywords: list[str]
    session_file: str = "monitor.session"
    db_file: str = "seen.db"
    send_delay_seconds: float = 1.5
    rate_limit_per_minute: int = 20
    log_level: str = "INFO"
    log_to_stdout: bool = True
    log_file: str | None = None


def load_config(path: str = "config.yaml") -> MonitorConfig:
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit(f"Config file not found: {path}\nCopy config.example.yaml to config.yaml and fill in your credentials.")
    except yaml.YAMLError as e:
        sys.exit(f"Failed to parse config file: {e}")

    required = ["api_id", "api_secret", "destination_chat", "keywords"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        sys.exit(f"Missing required config fields: {', '.join(missing)}")

    if not isinstance(data["keywords"], list) or not data["keywords"]:
        sys.exit("'keywords' must be a non-empty list in config.yaml")

    return MonitorConfig(
        api_id=int(data["api_id"]),
        api_secret=str(data["api_secret"]),
        destination_chat=data["destination_chat"],
        keywords=[str(k) for k in data["keywords"]],
        session_file=str(data.get("session_file", "monitor.session")),
        db_file=str(data.get("db_file", "seen.db")),
        send_delay_seconds=float(data.get("send_delay_seconds", 1.5)),
        rate_limit_per_minute=int(data.get("rate_limit_per_minute", 20)),
        log_level=str(data.get("log_level", "INFO")).upper(),
        log_to_stdout=bool(data.get("log_to_stdout", True)),
        log_file=data.get("log_file") or None,
    )
