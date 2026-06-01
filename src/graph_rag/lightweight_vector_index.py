import csv
import json
import math
import os
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from src.utils.config_loader import get_project_root
from src.utils.logger import logger


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
    """Hybrid semantic recall with optional sentence-transformers embeddings.

    Default mode stays CPU-only character n-gram for demo stability. Set
    KGQA_USE_EMBEDDINGS=1 to enable BGE embeddings if sentence-transformers
    is installed and the model has been downloaded.
    """

    def __init__(self, max_records: int = 6000):
        self.max_records = max_records
        self.records: List[Dict[str, str]] = []
        self._vectors: List[Dict[str, float]] = []
        self._semantic_vectors = None
        self._semantic_model = None
        self._loaded = False
        self.use_embeddings = os.getenv("KGQA_USE_EMBEDDINGS", "0") == "1"
        self.embedding_model_name = os.getenv("KGQA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        self.embedding_device = os.getenv("KGQA_EMBEDDING_DEVICE", "cpu")
        cache_name = os.getenv("KGQA_EMBEDDING_CACHE", ".cache/kgqa_bge_small_zh_v15.pkl")
        self.embedding_cache = get_project_root() / cache_name

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
        if self.use_embeddings:
            self._load_semantic_vectors()
        self._loaded = True

    def _record_texts(self) -> List[str]:
        return [f"{r['label']} {r['name']} {r['text']}" for r in self.records]

    def _load_semantic_model(self):
        if self._semantic_model is not None:
            return self._semantic_model
        try:
            from sentence_transformers import SentenceTransformer

            self._semantic_model = SentenceTransformer(self.embedding_model_name, device=self.embedding_device)
            return self._semantic_model
        except Exception as exc:
            logger.warning(f"Embedding model unavailable, fallback to char n-gram recall: {exc}")
            self.use_embeddings = False
            return None

    def _load_semantic_vectors(self) -> None:
        if not self.records:
            return
        cache_payload = {
            "model": self.embedding_model_name,
            "records": [(r["id"], r["name"]) for r in self.records],
        }
        if self.embedding_cache.exists():
            try:
                with open(self.embedding_cache, "rb") as f:
                    cached = pickle.load(f)
                if cached.get("meta") == cache_payload:
                    self._semantic_vectors = cached.get("vectors")
                    logger.info(f"Loaded embedding cache: {self.embedding_cache}")
                    return
            except Exception as exc:
                logger.warning(f"Embedding cache invalid, rebuilding: {exc}")

        model = self._load_semantic_model()
        if model is None:
            return
        logger.info(f"Building embedding index with {self.embedding_model_name} on {self.embedding_device}...")
        self.embedding_cache.parent.mkdir(parents=True, exist_ok=True)
        self._semantic_vectors = model.encode(
            self._record_texts(),
            batch_size=64,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        with open(self.embedding_cache, "wb") as f:
            pickle.dump({"meta": cache_payload, "vectors": self._semantic_vectors}, f)
        logger.info(f"Saved embedding cache: {self.embedding_cache}")

    def _semantic_search(self, query: str, top_k: int) -> List[Dict[str, object]]:
        model = self._load_semantic_model()
        if model is None or self._semantic_vectors is None:
            return []
        query_vec = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        scores = self._semantic_vectors @ query_vec
        indexed = [(float(score), idx) for idx, score in enumerate(scores)]
        indexed.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, idx in indexed[:top_k]:
            record = self.records[idx]
            results.append(
                EvidenceChunk(
                    id=record["id"],
                    label=record["label"],
                    name=record["name"],
                    text=record["text"],
                    source_type="bge_embedding",
                    score=round(score, 4),
                    node_ref=record["id"],
                    vector_score=round(score, 4),
                    hybrid_score=round(0.35 * score, 4),
                ).to_source()
            )
        return results

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, object]]:
        self.load()
        if self.use_embeddings and self._semantic_vectors is not None:
            try:
                return self._semantic_search(query, top_k)
            except Exception as exc:
                logger.warning(f"Semantic embedding search failed, fallback to char n-gram: {exc}")
                self.use_embeddings = False

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
