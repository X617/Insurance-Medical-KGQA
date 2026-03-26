from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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
    history: List[Dict[str, str]] = []

# === 修改点 2：定义响应模型，增加 rewritten_query 方便调试 ===
class ChatResponse(BaseModel):
    answer: str
    context: str
    intent: Optional[dict] = None
    rewritten_query: Optional[str] = None  # 返回重写后的问题

# 全局 RAG 引擎实例
rag_engine = None

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
            rewritten_query=result.get("rewritten_query") # 获取重写后的问题
        )
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    # 增加一个简单的 Neo4j 连接状态检查
    neo4j_status = False
    if rag_engine and rag_engine.retriever and rag_engine.retriever.driver:
        neo4j_status = True
        
    return {"status": "ok", "neo4j_connected": neo4j_status}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)