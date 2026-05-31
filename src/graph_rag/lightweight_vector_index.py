import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from src.utils.config_loader import get_project_root


@dataclass
class EvidenceChunk:
    id: str
    label: str
    name: str
    text: str
    source_type: str
    score: float
    node_ref: str = ""
    graph_score: float = 0.0
    vector_score: float = 0.0
    rule_score: float = 0.0
    hybrid_score: float = 0.0

    def to_source(self) -> Dict[str, object]:
        data = asdict(self)
        data["type"] = self.source_type
        data["snippet"] = self.text[:180]
        return data


class LightweightVectorIndex:
    """CPU-only character n-gram semantic recall for demo-scale HybridRAG."""

    def __init__(self, max_records: int = 6000):
        self.max_records = max_records
        self.records: List[Dict[str, str]] = []
        self._vectors: List[Dict[str, float]] = []
        self._loaded = False

    def _char_grams(self, text: str) -> Dict[str, float]:
        text = "".join(str(text or "").split())
        grams: Dict[str, float] = {}
        for n in (2, 3):
            for i in range(max(0, len(text) - n + 1)):
                gram = text[i : i + n]
                grams[gram] = grams.get(gram, 0.0) + 1.0
        norm = math.sqrt(sum(v * v for v in grams.values())) or 1.0
        return {k: v / norm for k, v in grams.items()}

    def _score(self, qv: Dict[str, float], dv: Dict[str, float]) -> float:
        if len(qv) > len(dv):
            qv, dv = dv, qv
        return sum(weight * dv.get(gram, 0.0) for gram, weight in qv.items())

    def _add_record(self, label: str, name: str, text: str) -> None:
        if not name or len(self.records) >= self.max_records:
            return
        self.records.append({"label": label, "name": name, "text": text or "", "id": f"{label}:{name}"})

    def load(self) -> None:
        if self._loaded:
            return
        root = get_project_root()

        insurance_path = root / "DataCleaned" / "Insurance" / "insurance_info.json"
        if insurance_path.exists():
            for item in json.load(open(insurance_path, encoding="utf-8")):
                self._add_record(
                    "Insurance",
                    item.get("产品名称"),
                    " ".join(str(item.get(k, "")) for k in ("险种分类", "承保年龄", "产品描述", "价格")),
                )

        disease_path = root / "DataCleaned" / "Diseases" / "diseases.json"
        if disease_path.exists():
            for item in json.load(open(disease_path, encoding="utf-8")):
                self._add_record(
                    "Disease",
                    item.get("name"),
                    " ".join(str(item.get(k, "")) for k in ("intro", "easy_get", "cause", "prevent", "treat_detail")),
                )

        nursing_path = root / "DataCleaned" / "NursingHomes" / "nursing_homes.csv"
        if nursing_path.exists():
            with open(nursing_path, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    self._add_record(
                        "NursingHome",
                        row.get("名称"),
                        " ".join(str(row.get(k, "")) for k in ("城市", "性质", "床位", "价格(元/月)", "特色服务", "地址")),
                    )

        self._vectors = [self._char_grams(f"{r['name']} {r['text']}") for r in self.records]
        self._loaded = True

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, object]]:
        self.load()
        qv = self._char_grams(query)
        scored = []
        for record, vector in zip(self.records, self._vectors):
            score = self._score(qv, vector)
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            EvidenceChunk(
                id=record["id"],
                label=record["label"],
                name=record["name"],
                text=record["text"],
                source_type="hybrid_vector",
                score=round(float(score), 4),
                node_ref=record["id"],
                vector_score=round(float(score), 4),
                hybrid_score=round(0.35 * float(score), 4),
            ).to_source()
            for score, record in scored[:top_k]
        ]
