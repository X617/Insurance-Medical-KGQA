import base64
import io
import json
import os
import re
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
import uvicorn
from contextlib import asynccontextmanager

from src.graph_rag.rag_engine import RAGEngine
from src.utils.logger import logger

# === 修改点 1：定义请求模型，增加 history 字段 ===
class ChatRequest(BaseModel):
    query: str
    # history 是一个列表，列表里是字典，默认为空
    # 结构示例: [{"role": "user", "content": "北京养老院"}, {"role": "assistant", "content": "..."}]
    history: List[Dict[str, str]] = Field(default_factory=list)

# === 修改点 2：定义响应模型，增加 rewritten_query 方便调试 ===
class ChatResponse(BaseModel):
    answer: str
    context: str
    intent: Optional[dict] = None
    rewritten_query: Optional[str] = None  # 返回重写后的问题
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    graph: Dict[str, Any] = Field(default_factory=lambda: {"nodes": [], "edges": [], "paths": []})
    recommendations: Dict[str, Any] = Field(default_factory=lambda: {"insurance": [], "nursing_homes": []})
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_paths: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentUploadRequest(BaseModel):
    filename: str
    content_base64: Optional[str] = None
    text: Optional[str] = None
    mime_type: Optional[str] = None


class DocumentAskRequest(BaseModel):
    query: str


class TripleIngestRequest(BaseModel):
    triples: List[Dict[str, str]]


class ExtractTriplesResponse(BaseModel):
    triples: List[Dict[str, str]] = Field(default_factory=list)
    method: str = "rule"

# 全局 RAG 引擎实例
rag_engine = None
DOCUMENT_STORE: Dict[str, Dict[str, Any]] = {}

ALLOWED_LABELS = {
    "Disease", "Drug", "Symptom", "NursingHome", "Insurance",
    "Department", "Population", "AgeRange", "Exclusion", "Service", "City"
}
ALLOWED_RELATIONSHIPS = {
    "COVERS", "EXCLUDES", "ALLOWS_AGE", "REFUSES_DISEASE",
    "TARGETS_POPULATION", "COVERS_DISEASE", "RELATED_TO_DISEASE",
    "HAS_SYMPTOM", "TREATED_BY", "PROVIDES", "LOCATED_IN"
}


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _validate_triples(triples: List[Dict[str, str]]) -> tuple[List[Dict[str, str]], List[str]]:
    valid = []
    errors = []
    for idx, item in enumerate(triples):
        head = (item.get("head") or "").strip()
        tail = (item.get("tail") or "").strip()
        head_label = (item.get("head_label") or item.get("type") or "Insurance").strip()
        tail_label = (item.get("tail_label") or item.get("tail_type") or "Disease").strip()
        rel = (item.get("relation") or "RELATED_TO_DISEASE").strip()
        evidence = (item.get("evidence") or "").strip()
        if not head or not tail:
            errors.append(f"第 {idx + 1} 条缺少 head/tail")
            continue
        if head_label not in ALLOWED_LABELS:
            errors.append(f"第 {idx + 1} 条非法 head_label：{head_label}")
            continue
        if tail_label not in ALLOWED_LABELS:
            errors.append(f"第 {idx + 1} 条非法 tail_label：{tail_label}")
            continue
        if rel not in ALLOWED_RELATIONSHIPS:
            errors.append(f"第 {idx + 1} 条非法 relation：{rel}")
            continue
        valid.append({
            "head": head,
            "head_label": head_label,
            "relation": rel,
            "tail": tail,
            "tail_label": tail_label,
            "evidence": evidence,
        })
    return valid, errors


def _rule_extract_triples(text: str, filename: str = "") -> List[Dict[str, str]]:
    """Deterministic fallback for local demo when LLM JSON extraction is unavailable."""
    triples = []
    head = (filename.rsplit(".", 1)[0] or "上传条款").strip()
    product_match = re.search(r"(?:产品名称|保险名称|名称)[:：\s]*([^\n，。；;]{4,40})", text)
    if product_match:
        head = product_match.group(1).strip()

    age_match = re.search(r"(?:投保年龄|承保年龄|年龄范围|被保险人年龄)[:：\s]*([^\n。；;]{2,50})", text)
    if age_match:
        triples.append({
            "head": head,
            "head_label": "Insurance",
            "relation": "ALLOWS_AGE",
            "tail": age_match.group(1).strip(),
            "tail_label": "AgeRange",
            "evidence": age_match.group(0)[:160],
        })

    for disease in ["高血压", "糖尿病", "恶性肿瘤", "癌症", "冠心病", "脑卒中"]:
        window = text[max(0, text.find(disease) - 40): text.find(disease) + 80] if disease in text else ""
        if window and any(word in window for word in ["免责", "除外", "不承担", "拒保", "责任免除"]):
            triples.append({
                "head": head,
                "head_label": "Insurance",
                "relation": "EXCLUDES",
                "tail": disease,
                "tail_label": "Disease",
                "evidence": window[:160],
            })
        elif window and any(word in window for word in ["保障", "赔付", "给付", "覆盖"]):
            triples.append({
                "head": head,
                "head_label": "Insurance",
                "relation": "COVERS_DISEASE",
                "tail": disease,
                "tail_label": "Disease",
                "evidence": window[:160],
            })

    for benefit in ["住院医疗", "重大疾病", "门诊", "手术", "护理", "质子重离子"]:
        if benefit in text:
            triples.append({
                "head": head,
                "head_label": "Insurance",
                "relation": "COVERS",
                "tail": benefit,
                "tail_label": "Service",
                "evidence": benefit,
            })
    return triples[:20]


def _extract_text_from_upload(payload: DocumentUploadRequest) -> str:
    if payload.text:
        return payload.text.strip()
    if not payload.content_base64:
        return ""

    raw = base64.b64decode(payload.content_base64)
    filename = payload.filename.lower()
    if filename.endswith(".txt") or (payload.mime_type or "").startswith("text/"):
        return raw.decode("utf-8", errors="ignore").strip()
    if filename.endswith(".pdf") or payload.mime_type == "application/pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            pages = [(page.extract_text() or "") for page in reader.pages[:8]]
            return "\n".join(pages).strip()
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"PDF 文本抽取失败，请确认已安装 pypdf 或改传 txt：{exc}",
            )
    if filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise HTTPException(
            status_code=422,
            detail="图片 OCR 暂未启用。第一阶段请优先上传 PDF/txt；后续可接入 PaddleOCR 或云端多模态模型。",
        )
    raise HTTPException(status_code=415, detail="暂只支持 PDF、txt 和常见图片格式。")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    global rag_engine
    logger.info("Initializing RAG Engine...")
    rag_engine = RAGEngine()
    yield
    # 关闭时清理
    logger.info("Closing RAG Engine...")
    if rag_engine:
        rag_engine.close()

app = FastAPI(title="Insurance & Medical KGQA API", lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "message": "Insurance & Medical KGQA backend is running.",
        "docs": "/docs",
        "health": "/health",
        "frontend": "Please open the Streamlit frontend at http://127.0.0.1:8501",
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # === 修改点 3：将 history 传给 rag_engine ===
        # 注意：这里的 rag_engine.chat 需要你在 rag_engine.py 里同步修改支持接收 history 参数
        result = rag_engine.chat(request.query, request.history)
        
        return ChatResponse(
            answer=result["answer"],
            context=result["context"],
            intent=result["intent"],
            rewritten_query=result.get("rewritten_query"), # 获取重写后的问题
            sources=result.get("sources", []),
            graph=result.get("graph", {"nodes": [], "edges": [], "paths": []}),
            recommendations=result.get("recommendations", {"insurance": [], "nursing_homes": []}),
            trace=result.get("trace", []),
            reasoning_paths=result.get("reasoning_paths", []),
        )
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    def event_stream():
        try:
            yield _sse("trace_start", {"query": request.query})
            yield _sse("trace_step", {
                "agent": "RequestAgent",
                "status": "ok",
                "note": "收到用户问题，启动 GraphRAG Agent 流程。",
                "input": request.query,
                "output": "accepted",
            })
            result = rag_engine.chat(request.query, request.history)
            emitted = set()
            for step in result.get("trace", []):
                key = (step.get("agent"), step.get("status"), step.get("note"))
                if key in emitted:
                    continue
                emitted.add(key)
                yield _sse("trace_step", step)
            yield _sse("retrieval", {
                "sources": result.get("sources", []),
                "graph": result.get("graph", {}),
                "recommendations": result.get("recommendations", {}),
                "reasoning_paths": result.get("reasoning_paths", []),
            })
            answer = result.get("answer", "")
            chunk = ""
            for char in answer:
                chunk += char
                if len(chunk) >= 18 or char in "。！？\n":
                    yield _sse("token", {"text": chunk})
                    chunk = ""
            if chunk:
                yield _sse("token", {"text": chunk})
            yield _sse("final", result)
        except Exception as exc:
            logger.error(f"SSE chat error: {exc}")
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/health")
async def health_check():
    # Health must stay lightweight. Deep database verification belongs to /graph/stats.
    neo4j_status = bool(rag_engine and rag_engine.retriever and rag_engine.retriever.driver)
    llm_configured = bool(
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
    )
    return {"status": "ok", "neo4j_connected": neo4j_status, "llm_configured": llm_configured}


@app.get("/graph/stats")
async def graph_stats():
    if not rag_engine or not rag_engine.retriever:
        raise HTTPException(status_code=503, detail="RAG engine is not ready")
    return rag_engine.retriever.get_graph_stats()


@app.get("/graph/subgraph")
async def graph_subgraph(query: str = "", entity: str = "", depth: int = 1, limit: int = 40):
    if not rag_engine or not rag_engine.retriever:
        raise HTTPException(status_code=503, detail="RAG engine is not ready")
    return rag_engine.retriever.get_subgraph(entity=entity, query=query, depth=depth, limit=limit)


@app.get("/metrics/demo")
async def demo_metrics():
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine is not ready")
    stats = rag_engine.get_metrics()
    graph_stats = rag_engine.retriever.get_graph_stats() if rag_engine.retriever else {}
    stats["graph_connected"] = bool(graph_stats.get("connected"))
    stats["graph_stats"] = graph_stats
    return stats


@app.post("/documents/upload")
async def upload_document(payload: DocumentUploadRequest):
    text = _extract_text_from_upload(payload)
    if not text:
        raise HTTPException(status_code=400, detail="未抽取到有效文本。")
    document_id = str(uuid.uuid4())
    DOCUMENT_STORE[document_id] = {
        "document_id": document_id,
        "filename": payload.filename,
        "text": text,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return {
        "document_id": document_id,
        "filename": payload.filename,
        "summary": text[:500],
        "chars": len(text),
        "askable": True,
    }


@app.post("/documents/{document_id}/ask")
async def ask_document(document_id: str, payload: DocumentAskRequest):
    doc = DOCUMENT_STORE.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_id 不存在，请重新上传资料。")
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine is not ready")

    prompt = f"""
    你是保险条款解读助手。请严格依据 [上传资料] 回答 [用户问题]。
    如果资料中没有明确依据，请直接说明“资料中未发现明确说明”，不要编造。

    [上传资料]
    {doc['text'][:8000]}

    [用户问题]
    {payload.query}
    """
    answer = rag_engine.llm.generate(prompt, temperature=0.1)
    return {
        "document_id": document_id,
        "filename": doc["filename"],
        "answer": answer,
        "sources": [{"type": "uploaded_document", "name": doc["filename"], "snippet": doc["text"][:400]}],
    }


@app.post("/documents/{document_id}/extract-triples", response_model=ExtractTriplesResponse)
async def extract_document_triples(document_id: str):
    doc = DOCUMENT_STORE.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_id 不存在，请重新上传资料。")
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine is not ready")

    prompt = f"""
    你是保险条款结构化抽取助手。请从上传资料中抽取知识图谱三元组，严格输出 JSON 数组。
    每个元素字段为：head, head_label, relation, tail, tail_label, evidence。
    只允许以下标签：{sorted(ALLOWED_LABELS)}
    只允许以下关系：{sorted(ALLOWED_RELATIONSHIPS)}
    优先抽取保险产品、投保年龄、免责疾病、保障责任、目标人群。
    不要输出 Markdown，不要解释。

    [资料]
    {doc['text'][:7000]}
    """
    method = "llm"
    triples: List[Dict[str, str]] = []
    try:
        raw = rag_engine.llm.generate(prompt, temperature=0.0, max_tokens=900)
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            triples = json.loads(raw[start:end + 1])
    except Exception as exc:
        logger.warning(f"LLM triple extraction failed, fallback to rules: {exc}")
    valid, errors = _validate_triples(triples)
    if not valid:
        method = "rule"
        valid, errors = _validate_triples(_rule_extract_triples(doc["text"], doc["filename"]))
    if errors:
        logger.info(f"Triple extraction validation notes: {errors[:3]}")
    return ExtractTriplesResponse(triples=valid, method=method)


@app.post("/admin/ingest-triples")
async def ingest_triples(payload: TripleIngestRequest, dry_run: bool = True):
    if not rag_engine or not rag_engine.retriever or not rag_engine.retriever.driver:
        raise HTTPException(status_code=503, detail="Neo4j is not connected")

    valid, errors = _validate_triples(payload.triples)
    if dry_run:
        return {
            "dry_run": True,
            "valid_count": len(valid),
            "inserted": 0,
            "errors": errors,
            "triples": valid,
        }
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    inserted = 0
    with rag_engine.retriever.driver.session(database=rag_engine.retriever.database) as session:
        for item in valid:
            head = item["head"]
            tail = item["tail"]
            head_label = item["head_label"]
            tail_label = item["tail_label"]
            rel = item["relation"]
            cypher = f"""
            MERGE (h:{head_label} {{name: $head}})
            MERGE (t:{tail_label} {{name: $tail}})
            MERGE (h)-[r:{rel}]->(t)
            SET r.evidence = coalesce($evidence, r.evidence)
            """
            session.run(cypher, head=head, tail=tail, evidence=item.get("evidence"))
            inserted += 1
    return {"dry_run": False, "valid_count": len(valid), "inserted": inserted, "errors": []}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
