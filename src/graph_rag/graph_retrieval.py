# 图谱检索：基于实体的子图检索
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SubGraphResult:
    """子图检索结果。"""
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    triples: List[tuple] = field(default_factory=list)


def _node_name(n: Dict[str, Any]) -> str:
    """从节点 dict（含 _type Node 与 properties）取 name。"""
    if not isinstance(n, dict):
        return str(n)
    props = n.get("properties") or n
    return props.get("name") or props.get("id") or str(n)


class GraphRetriever:
    """图谱检索器：根据实体名检索相关子图。"""

    def __init__(self, neo4j_loader: Any, max_hops: int = 2):
        self.neo4j_loader = neo4j_loader
        self.max_hops = max_hops

    def retrieve_subgraph(
        self,
        entities: List[str],
        hops: Optional[int] = None,
        limit: Optional[int] = 50,
    ) -> SubGraphResult:
        """根据实体名检索相关子图。"""
        if not entities:
            return SubGraphResult(nodes=[], relationships=[], triples=[])
        h = hops if hops is not None else self.max_hops
        limit = limit or 50
        try:
            # 兼容 py2neo 返回的序列化结构：nodes(path) 为 list of Node -> dict
            query = """
            MATCH (start)
            WHERE start.name IN $entities
            WITH start
            MATCH path = (start)-[*1..%d]-(related)
            WITH path
            LIMIT $limit
            RETURN nodes(path) AS nodes, relationships(path) AS rels
            """ % h
            rows = self.neo4j_loader.run_cypher(query, {"entities": entities, "limit": limit})
        except Exception:
            return SubGraphResult(nodes=[], relationships=[], triples=[])

        nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        triples: List[tuple] = []
        seen_nodes: set = set()
        seen_rels: set = set()

        for row in rows:
            for n in row.get("nodes") or []:
                if not isinstance(n, dict):
                    continue
                name = _node_name(n)
                if name and name not in seen_nodes:
                    seen_nodes.add(name)
                    nodes.append(n)
            for r in row.get("rels") or []:
                if not isinstance(r, dict):
                    continue
                key = (r.get("type"), r.get("properties", {}))
                if key not in seen_rels:
                    seen_rels.add(key)
                    relationships.append(r)
            # 从 path 构造三元组：需要从 nodes 和 rels 对应
            nlist = row.get("nodes") or []
            rlist = row.get("rels") or []
            for i, rel in enumerate(rlist):
                if not isinstance(rel, dict):
                    continue
                rel_type = rel.get("type") or "RELATED_TO"
                if i + 1 < len(nlist):
                    h_name = _node_name(nlist[i])
                    t_name = _node_name(nlist[i + 1])
                    triples.append((h_name, rel_type, t_name))

        return SubGraphResult(nodes=nodes, relationships=relationships, triples=triples)

    def subgraph_to_text(self, result: SubGraphResult) -> str:
        """将子图序列化为文本，便于填入 Prompt。"""
        if not result.triples:
            lines = []
            for n in result.nodes:
                props = (n.get("properties") or n) if isinstance(n, dict) else {}
                name = props.get("name") or props.get("id")
                if name:
                    labels = (n.get("labels") or []) if isinstance(n, dict) else []
                    lines.append(f"实体: {name} (类型: {', '.join(labels)})")
            if not lines:
                return "（未检索到相关图谱信息，请确保 Neo4j 中已导入数据且问句包含实体名。）"
            return "\n".join(lines)
        lines = ["三元组："]
        for h, r, t in result.triples[:30]:
            lines.append(f"  ({h}) -[{r}]-> ({t})")
        return "\n".join(lines)
