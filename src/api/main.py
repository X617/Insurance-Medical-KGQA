import base64
import io
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
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


class DocumentUploadRequest(BaseModel):
    filename: str
    content_base64: Optional[str] = None
    text: Optional[str] = None
    mime_type: Optional[str] = None


class DocumentAskRequest(BaseModel):
    query: str


class TripleIngestRequest(BaseModel):
    triples: List[Dict[str, str]]

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
        )
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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


@app.post("/admin/ingest-triples")
async def ingest_triples(payload: TripleIngestRequest):
    if not rag_engine or not rag_engine.retriever or not rag_engine.retriever.driver:
        raise HTTPException(status_code=503, detail="Neo4j is not connected")

    inserted = 0
    with rag_engine.retriever.driver.session(database=rag_engine.retriever.database) as session:
        for item in payload.triples:
            head = item.get("head")
            tail = item.get("tail")
            head_label = item.get("head_label") or item.get("type") or "Insurance"
            tail_label = item.get("tail_label") or item.get("tail_type") or "Disease"
            rel = item.get("relation") or "RELATED_TO_DISEASE"
            if not head or not tail:
                continue
            if head_label not in ALLOWED_LABELS or tail_label not in ALLOWED_LABELS or rel not in ALLOWED_RELATIONSHIPS:
                raise HTTPException(status_code=400, detail=f"非法标签或关系：{head_label}, {rel}, {tail_label}")
            cypher = f"""
            MERGE (h:{head_label} {{name: $head}})
            MERGE (t:{tail_label} {{name: $tail}})
            MERGE (h)-[:{rel}]->(t)
            """
            session.run(cypher, head=head, tail=tail)
            inserted += 1
    return {"inserted": inserted}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
