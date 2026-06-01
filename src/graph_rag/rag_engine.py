import time
from typing import List, Dict, Optional
from src.utils.logger import logger
from src.graph_rag.query_understanding import QueryParser
from src.graph_rag.graph_retriever import GraphRetriever
from src.graph_rag.llm_integration import LLMIntegration

class RAGEngine:
    def __init__(self):
        logger.info("Initializing RAG Engine...")
        self.parser = QueryParser()
        self.retriever = GraphRetriever()
        self.llm = LLMIntegration()
        self._response_cache = {}
        self._response_cache_order = []
        self._metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "total_latency_ms": 0.0,
            "graph_hits": 0,
            "rule_filter_hits": 0,
            "last_eval": None,
        }

    def _record_metrics(self, result: dict, latency_ms: float, cache_hit: bool = False) -> None:
        self._metrics["total_queries"] += 1
        self._metrics["total_latency_ms"] += latency_ms
        if cache_hit:
            self._metrics["cache_hits"] += 1
        if result.get("graph", {}).get("nodes"):
            self._metrics["graph_hits"] += 1
        recs = result.get("recommendations", {}) or {}
        if recs.get("insurance") or recs.get("nursing_homes"):
            self._metrics["rule_filter_hits"] += 1

    def get_metrics(self) -> dict:
        total = max(1, self._metrics["total_queries"])
        return {
            "total_queries": self._metrics["total_queries"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_hit_rate": round(self._metrics["cache_hits"] / total, 4),
            "avg_latency_ms": round(self._metrics["total_latency_ms"] / total, 2),
            "graph_hit_rate": round(self._metrics["graph_hits"] / total, 4),
            "rule_filter_hits": self._metrics["rule_filter_hits"],
            "last_eval": self._metrics.get("last_eval"),
        }

    def update_last_eval(self, summary: dict) -> None:
        self._metrics["last_eval"] = summary

    # === 新增函数：独立的问题重写模块 ===
    def _rewrite_query(self, user_query: str, history: List[Dict[str, str]], trace: Optional[list] = None) -> str:
        """
        利用历史记录，将用户的后续问题重写为独立完整的句子。
        例如：Context="北京有哪些养老院?", Query="价格多少?" -> Rewrite="北京的养老院价格是多少?"
        """
        if not history:
            if trace is not None:
                trace.append({
                    "agent": "QueryRewriteAgent",
                    "status": "skipped",
                    "input": user_query,
                    "output": user_query,
                    "note": "无历史对话，直接使用原始问题。",
                })
            return user_query

        followup_keywords = ["上面", "上述", "刚才", "这几个", "其中", "推荐的", "第二个", "第一个", "它", "这个", "那个", "价格多少", "适合吗"]
        if not any(keyword in user_query for keyword in followup_keywords):
            if trace is not None:
                trace.append({
                    "agent": "QueryRewriteAgent",
                    "status": "skipped",
                    "input": user_query,
                    "output": user_query,
                    "note": "未检测到明显指代追问，跳过 LLM 重写以降低延迟。",
                })
            return user_query

        # 取最近的 2-3 轮对话作为上下文，节省 token 且避免干扰
        recent_history = history[-4:] 
        
        history_text = ""
        for msg in recent_history:
            role = "用户" if msg['role'] == "user" else "AI助手"
            history_text += f"{role}: {msg['content']}\n"

        prompt = f"""
        你是一个对话重写助手。你的任务是根据【对话历史】将【用户最新问题】重写为一个语义完整、指代清晰的独立问题。
        
        【对话历史】
        {history_text}
        
        【用户最新问题】
        {user_query}
        
        要求：
        1. 补全省略的主语（如“它”、“第一家”指代的是什么）。
        2. 如果问题本身已经很清晰，不需要上下文，则原样返回。
        3. 直接返回重写后的句子，不要任何解释。
        """
        
        # 调用 LLM 进行重写
        try:
            rewritten_query = self.llm.generate(prompt, temperature=0.1, max_tokens=80) # 低温保证稳定
            logger.info(f"🔄 Query Rewrite: '{user_query}' -> '{rewritten_query}'")
            if trace is not None:
                trace.append({
                    "agent": "QueryRewriteAgent",
                    "status": "ok",
                    "input": user_query,
                    "output": rewritten_query,
                    "note": "结合最近对话历史补全省略和指代。",
                })
            return rewritten_query
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            if trace is not None:
                trace.append({
                    "agent": "QueryRewriteAgent",
                    "status": "fallback",
                    "input": user_query,
                    "output": user_query,
                    "note": f"重写失败，回退原问题：{e}",
                })
            return user_query

    # === 修改 chat 函数，接收 history 参数 ===
    def chat(self, user_query: str, history: Optional[List[Dict[str, str]]] = None) -> dict:
        started = time.perf_counter()
        history = history or []
        cache_key = user_query.strip()
        if not history and cache_key in self._response_cache:
            cached = dict(self._response_cache[cache_key])
            cached["trace"] = [
                {
                    "agent": "CacheAgent",
                    "status": "hit",
                    "input": user_query,
                    "output": "cached_response",
                    "note": "命中本地问答缓存，跳过意图解析、图谱检索和大模型生成。",
                },
                *cached.get("trace", []),
            ]
            self._record_metrics(cached, (time.perf_counter() - started) * 1000, cache_hit=True)
            return cached
        trace = []
        
        # 1. 【核心升级】多轮对话意图补全
        # 如果有历史记录，先尝试重写问题
        current_query = self._rewrite_query(user_query, history, trace)
        
        # logger.info(f"Processing query (Original): {user_query}")
        logger.info(f"Processing query (Rewritten): {current_query}")
        
        # 2. 意图识别（使用重写后的问题）
        try:
            # 注意：这里传给 parser 的是 current_query (补全后的)
            parsed_intent = self.parser.parse(current_query)
            # ===【新增】把问题文本也塞进去，方便检索器做关键词匹配 ===
            parsed_intent['raw_query'] = current_query
            logger.info(f"Parsed intent: {parsed_intent}")
            trace.append({
                "agent": "IntentAgent",
                "status": "ok",
                "input": current_query,
                "output": parsed_intent,
                "note": "抽取意图、年龄、疾病、城市、预算等结构化字段。",
            })
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            parsed_intent = {}
            trace.append({
                "agent": "IntentAgent",
                "status": "fallback",
                "input": current_query,
                "output": {"intent": "general_qa"},
                "note": f"意图解析失败，使用兜底意图：{e}",
            })

        # 3. 图谱检索（使用重写后的问题）
        try:
            retrieval_payload = self.retriever.retrieve_structured(parsed_intent)
            context = retrieval_payload["context"]
            recs = retrieval_payload.get("recommendations", {})
            trace.append({
                "agent": "RetrieverAgent",
                "status": "ok",
                "input": parsed_intent,
                "output": {
                    "source_count": len(retrieval_payload.get("sources", [])),
                    "graph_nodes": len(retrieval_payload.get("graph", {}).get("nodes", [])),
                    "graph_edges": len(retrieval_payload.get("graph", {}).get("edges", [])),
                    "insurance_candidates": len(recs.get("insurance", [])),
                    "nursing_home_candidates": len(recs.get("nursing_homes", [])),
                },
                "note": "执行图谱召回、关键词语义兜底召回与规则重排。",
            })
        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}")
            context = "检索失败"
            retrieval_payload = {
                "context": context,
                "sources": [],
                "graph": {"nodes": [], "edges": [], "paths": []},
                "recommendations": {"insurance": [], "nursing_homes": []},
                "reasoning_paths": [],
            }
            trace.append({
                "agent": "RetrieverAgent",
                "status": "failed",
                "input": parsed_intent,
                "output": context,
                "note": str(e),
            })

        # 4. 生成回答
        # 提取上一轮 AI 的回答，作为补充上下文
        history_content = "无"
        if history:
            # 找到 AI 最近的一次回答
            last_ai_reply = next((msg['content'] for msg in reversed(history) if msg['role'] == 'assistant'), "无")
            history_content = last_ai_reply

            # 检测是否为“回溯型”问题
            # 如果用户用了“上面的”、“这些”、“刚才”等词，说明他只想在历史里选
            keywords = ["上面的", "上述", "刚才", "这几个", "其中", "推荐的"]
            if any(k in user_query for k in keywords):
                logger.info("🔒 检测到指代性追问，强制屏蔽新检索结果，仅依赖历史记录。")
                # 关键操作：把 context 替换掉！让 AI 没得选，只能看 history
                context = "（本轮检索结果已屏蔽，请严格基于 [用户上轮对话历史] 回答）"
                retrieval_payload["context"] = context
                trace.append({
                    "agent": "ComplianceAgent",
                    "status": "ok",
                    "input": user_query,
                    "output": "history_only",
                    "note": "检测到指代性追问，避免引入新的无关产品。",
                })
            else:
                trace.append({
                    "agent": "ComplianceAgent",
                    "status": "ok",
                    "input": user_query,
                    "output": "graph_context_allowed",
                    "note": "使用当前图谱检索结果，并保留历史上下文。",
                })
        else:
            trace.append({
                "agent": "ComplianceAgent",
                "status": "ok",
                "input": user_query,
                "output": "single_turn",
                "note": "单轮问题，使用图谱检索结果与硬规则过滤候选。",
            })

        # System Prompt 保持不变...
        system_prompt = """
       你是一名资深的保险与医养专家，服务于泰康保险集团。你的职责是利用提供的专业知识库（Context）来回答客户关于保险产品、疾病医疗和养老机构的问题。

        *** 核心原则（必须严格遵守） ***
       1. **指代一致性**：如果 [Context] 显示“结果已屏蔽”，你必须 **完全忽略外界知识**，仅从 [用户上轮对话历史] 中筛选产品。
           - 如果历史产品都不符合（如70岁超龄），直接说“上述产品均不适用”。
           - 严禁自己编造或引入新产品。
        
        2. **格式要求**：推荐产品时，**必须**按以下 Markdown 列表格式输出详细信息（这是前端渲染卡片的关键）：
           
           1. **产品名称**
              - 投保年龄：xxx
              - 保障内容：xxx
              - 适用人群：xxx
              - 推荐理由：xxx
           
           2. **产品名称**
              ...
        
        3. **年龄合规性（最高优先级）**：
           - 用户会提供年龄（如 70岁）。你必须严格检查 Context 中保险产品的【投保年龄/承保年龄】。
           - 例子：如果产品写着“出生满28天-60周岁”，而用户是 70 岁，**绝对不能推荐**该产品。
           - 如果 Context 里所有的保险产品都超龄了，请直接回答：“很抱歉，知识库中暂无适合您当前年龄（{age}岁）的重疾/医疗险产品，建议关注防癌险或意外险。”
           - **严禁**把“最高续保年龄”（如105岁）当成“投保年龄”来忽悠用户。

        4. **险种匹配**：
           - 用户问“重疾险”，不要推荐“医疗险”。
           - 用户问“养老院”，不要推荐“保险”。

        5. **基于事实**：严格基于提供的 [Context] 信息回答。不要编造。
        6. **专业亲切**：语气要专业、温暖。
        
        """

        # 在 User Prompt 中，也可以适当加入一点历史信息，或者只给 Context
        # 这里我们选择只给 Context 和 Rewrite 后的问题，这样模型干扰最少
        user_prompt = f"""
        [用户上轮对话历史 - History]
        (这是你上一轮推荐给用户的产品列表，如果用户问“上面的”，请在这里找答案)
        {history_content}

        [新检索到的知识 -Context]
        
        {context}

        [结构化候选推荐 - Recommendations]
        {retrieval_payload.get("recommendations", {})}

        [用户当前问题 - Current Question]
        {current_query}

        请根据上述指令回答：
        """

        # 生成回答
        try:
            answer = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1, max_tokens=900) # 温度调低，让它更听话
            trace.append({
                "agent": "AnswerAgent",
                "status": "ok",
                "input": "context + recommendations + current_question",
                "output": answer[:240],
                "note": f"基于检索上下文和结构化候选生成最终回答。模型：{getattr(self.llm, 'last_model_used', 'unknown')}",
            })
        except Exception as e:
            logger.error(f"Generate failed: {e}")
            answer = "抱歉，生成回答时出现错误。"
            trace.append({
                "agent": "AnswerAgent",
                "status": "failed",
                "input": "context + recommendations + current_question",
                "output": answer,
                "note": str(e),
            })
        result = {
            "answer": answer,
            "context": context,
            "intent": parsed_intent,
            "rewritten_query": current_query, # 可以返回给前端看看效果
            "sources": retrieval_payload.get("sources", []),
            "graph": retrieval_payload.get("graph", {"nodes": [], "edges": [], "paths": []}),
            "recommendations": retrieval_payload.get("recommendations", {"insurance": [], "nursing_homes": []}),
            "trace": trace,
            "reasoning_paths": retrieval_payload.get("reasoning_paths", []),
        }
        if not history and cache_key and "LLM API Error" not in answer:
            self._response_cache[cache_key] = result
            self._response_cache_order.append(cache_key)
            if len(self._response_cache_order) > 64:
                oldest = self._response_cache_order.pop(0)
                self._response_cache.pop(oldest, None)
        self._record_metrics(result, (time.perf_counter() - started) * 1000)
        return result

    def close(self):
        self.retriever.close()

if __name__ == "__main__":
    # 测试代码
    engine = RAGEngine()
    try:
        test_q = "70岁高血压老人推荐买什么保险？"
        result = engine.chat(test_q)
        print("\n=== 用户问题 ===")
        print(test_q)
        print("\n=== 参考知识 (Context) ===")
        print(result["context"])
        print("\n=== AI 回答 ===")
        print(result["answer"])
    finally:
        engine.close()
