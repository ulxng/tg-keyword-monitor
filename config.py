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
    proxy_type: str | None = None
    proxy_host: str | None = None
    proxy_port: int | None = None
    proxy_secret: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None


def _parse_proxy(proxy: dict) -> dict:
    if not proxy.get("type"):
        return {}
    ptype = str(proxy["type"]).lower()
    if ptype not in ("socks4", "socks5", "mtproto"):
        sys.exit(f"Unknown proxy type '{proxy['type']}'. Supported: socks4, socks5, mtproto")
    if not proxy.get("host") or not proxy.get("port"):
        sys.exit("proxy.host and proxy.port are required when proxy is configured")
    return {
        "proxy_type": ptype,
        "proxy_host": str(proxy["host"]),
        "proxy_port": int(proxy["port"]),
        "proxy_secret": str(proxy["secret"]) if proxy.get("secret") else None,
        "proxy_username": str(proxy["username"]) if proxy.get("username") else None,
        "proxy_password": str(proxy["password"]) if proxy.get("password") else None,
    }


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
        **_parse_proxy(data.get("proxy") or {}),
    )
