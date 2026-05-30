from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def resolv_nameserver() -> str | None:
    path = Path("/etc/resolv.conf")
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[0] == "nameserver":
            return parts[1]
    return None


def default_gateway() -> str | None:
    try:
        out = subprocess.check_output(["sh", "-lc", "ip route | awk '/default/ {print $3; exit}'"], text=True)
    except Exception:
        return None
    return out.strip() or None


def hosts_names() -> list[str]:
    names: list[str] = []
    path = Path("/etc/hosts")
    if not path.exists():
        return names
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("127.0.1.1"):
            names.extend(parts[1:])
    return names


def can_connect(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "OK"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> None:
    env_uri = os.getenv("NEO4J_URI", "")
    candidates = ["127.0.0.1", "localhost"]
    for item in [resolv_nameserver(), default_gateway(), *hosts_names()]:
        if item and item not in candidates:
            candidates.append(item)
    if "://" in env_uri:
        host_port = env_uri.split("://", 1)[1].split("/", 1)[0]
        host = host_port.rsplit(":", 1)[0]
        if host and host not in candidates:
            candidates.insert(0, host)

    print("=== Neo4j network probe ===")
    print("如果 7474 通但 7687 不通，通常是 Bolt/防火墙问题。")
    print("如果某个 host 的 7687 显示 OK，把 .env 改成：NEO4J_URI=bolt://该host:7687")
    print()
    for host in candidates:
        results = []
        for port in (7474, 7687, 7688):
            ok, reason = can_connect(host, port)
            results.append(f"{port}={'OK' if ok else reason}")
        print(f"{host:24s} " + " | ".join(results))


if __name__ == "__main__":
    main()
