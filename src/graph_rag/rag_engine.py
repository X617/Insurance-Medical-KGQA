from typing import List, Dict
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

    # === 新增函数：独立的问题重写模块 ===
    def _rewrite_query(self, user_query: str, history: List[Dict[str, str]]) -> str:
        """
        利用历史记录，将用户的后续问题重写为独立完整的句子。
        例如：Context="北京有哪些养老院?", Query="价格多少?" -> Rewrite="北京的养老院价格是多少?"
        """
        if not history:
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
            rewritten_query = self.llm.generate(prompt, temperature=0.1) # 低温保证稳定
            logger.info(f"🔄 Query Rewrite: '{user_query}' -> '{rewritten_query}'")
            return rewritten_query
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return user_query

    # === 修改 chat 函数，接收 history 参数 ===
    def chat(self, user_query: str, history: List[Dict[str, str]] = []) -> dict:
        
        # 1. 【核心升级】多轮对话意图补全
        # 如果有历史记录，先尝试重写问题
        current_query = self._rewrite_query(user_query, history)
        
        # logger.info(f"Processing query (Original): {user_query}")
        logger.info(f"Processing query (Rewritten): {current_query}")
        
        # 2. 意图识别（使用重写后的问题）
        try:
            # 注意：这里传给 parser 的是 current_query (补全后的)
            parsed_intent = self.parser.parse(current_query)
            # ===【新增】把问题文本也塞进去，方便检索器做关键词匹配 ===
            parsed_intent['raw_query'] = current_query
            logger.info(f"Parsed intent: {parsed_intent}")
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            parsed_intent = {}

        # 3. 图谱检索（使用重写后的问题）
        try:
            context = self.retriever.retrieve(parsed_intent)
        except Exception as e:
            context = "检索失败"

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

        [用户当前问题 - Current Question]
        {current_query}

        请根据上述指令回答：
        """

        # 生成回答
        try:
            answer = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1) # 温度调低，让它更听话
        except Exception as e:
            logger.error(f"Generate failed: {e}")
            answer = "抱歉，生成回答时出现错误。"
        return {
            "answer": answer,
            "context": context,
            "intent": parsed_intent,
            "rewritten_query": current_query # 可以返回给前端看看效果
        }

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