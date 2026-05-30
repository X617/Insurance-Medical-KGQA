from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def mask(value: str | None) -> str:
    if not value:
        return "未配置"
    if value in {"your_neo4j_password", "sk-your-key"}:
        return f"{value}（模板占位值）"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def get_wsl_windows_host_ip() -> str | None:
    resolv_conf = Path("/etc/resolv.conf")
    if not resolv_conf.exists():
        return None
    for line in resolv_conf.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[0] == "nameserver":
            return parts[1]
    return None


def main() -> None:
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE")
    llm_key = (
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    llm_base = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL")

    print("=== 配置检查 ===")
    print(f"NEO4J_URI      = {neo4j_uri}")
    print(f"NEO4J_USERNAME = {neo4j_user}")
    print(f"NEO4J_PASSWORD = {mask(neo4j_password)}")
    print(f"NEO4J_DATABASE = {neo4j_database or '<default>'}")
    print(f"LLM_BASE_URL   = {llm_base or '使用 config.yaml 中的 llm.api_base'}")
    print(f"LLM_API_KEY    = {mask(llm_key)}")

    print("\n=== Neo4j 连接与数据量检查 ===")
    if not neo4j_password or neo4j_password == "your_neo4j_password":
        print("跳过 Neo4j：NEO4J_PASSWORD 仍是空值或模板占位值。")
        return
    if neo4j_uri.startswith("neo4j://127.0.0.1") or neo4j_uri.startswith("neo4j://localhost"):
        print("提示：本地 Neo4j Desktop 单机实例建议使用 bolt://127.0.0.1:7687，neo4j:// 可能触发 routing 错误。")

    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session(database=neo4j_database) as session:
            session.run("RETURN 1").consume()
            rows = session.run(
                """
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS cnt
                ORDER BY cnt DESC
                """
            )
            counts = list(rows)
        driver.close()
    except Exception as exc:
        print(f"Neo4j 连接失败：{exc}")
        if "127.0.0.1" in neo4j_uri or "localhost" in neo4j_uri:
            host_ip = get_wsl_windows_host_ip()
            if host_ip:
                print(
                    "你正在 WSL 中访问 127.0.0.1；如果 Neo4j Desktop 跑在 Windows，"
                    f"请尝试把 .env 改为：NEO4J_URI=bolt://{host_ip}:7687"
                )
        print("也可以运行 python scripts/probe_neo4j_network.py 自动探测哪个地址可连。")
        return

    if not counts:
        print("Neo4j 已连接，但当前数据库没有节点。请运行：RUN_IMPORT=1 bash scripts/run_demo.sh")
        return

    for row in counts:
        print(f"{row['label'] or 'Unknown':16s} {row['cnt']}")


if __name__ == "__main__":
    main()
