import json
import re
from src.utils.logger import logger
from src.graph_rag.llm_integration import LLMIntegration  # <--- 引入统一的 LLM 管家

class QueryParser:
    def __init__(self):
        # === 核心修改：不再直接连接 OpenAI，而是使用 LLMIntegration ===
        # 这样它就能自动读取 .env 里的 DASHSCOPE_API_KEY 了
        self.llm = LLMIntegration()

    def parse(self, query: str) -> dict:
        """
        利用大模型解析用户查询意图和关键实体。
        """
        system_prompt = """
        你是一个智能意图识别助手。你的任务是分析用户的自然语言问题，提取关键信息，并以严格的 JSON 格式返回。
        
        请提取以下字段：
        1. intent (字符串, 必选): 用户意图。可选值：
           - "insurance_query" (咨询保险产品、投保条件等)
           - "medical_query" (咨询疾病、药品、症状等)
           - "nursing_home_search" (咨询养老院、养老机构、查找养老院)
           - "general_qa" (其他通用闲聊)
        2. age (整数, 可选): 用户提到的年龄（如有）。
        3. disease (列表, 可选): 提到的疾病名称。
        4. drug (列表, 可选): 提到的药品名称。
        5. city (字符串, 可选): 提到的城市或地区（如“北京”、“朝阳区”）。
        6. price_max (整数, 可选): 提到的预算或价格上限（如“5000以下”则提取为 5000）。

        注意：
        - 如果没有提取到某个字段，请不要包含在 JSON 中，或者设为 null。
        - 仅返回 JSON 字符串，不要包含 Markdown 格式（如 ```json ... ```）。
        """

        user_prompt = f"用户问题：{query}"

        try:
            # 调用 LLM 生成解析结果
            response_text = self.llm.generate(
                prompt=user_prompt, 
                system_prompt=system_prompt,
                temperature=0.1 # 意图识别需要精确，温度调低
            )
            
            # 清理可能存在的 Markdown 格式
            cleaned_text = re.sub(r"```json|```", "", response_text).strip()
            
            # 解析 JSON
            parsed_result = json.loads(cleaned_text)
            
            # 简单的后处理：确保 intent 存在
            if "intent" not in parsed_result:
                parsed_result["intent"] = "general_qa"
                
            return parsed_result

        except json.JSONDecodeError:
            logger.error(f"Intent parsing failed (JSON Error). LLM Output: {response_text}")
            return {"intent": "general_qa"} # 降级处理
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            return {"intent": "general_qa"}

if __name__ == "__main__":
    # 测试代码
    parser = QueryParser()
    test_queries = [
        "70岁高血压老人能买什么保险？",
        "北京有哪些5000元以下的养老院？",
        "介绍一下阿司匹林"
    ]
    
    for q in test_queries:
        print(f"Q: {q}")
        print(f"A: {parser.parse(q)}\n")