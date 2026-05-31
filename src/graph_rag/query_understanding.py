import json
import re
from src.utils.logger import logger
from src.graph_rag.llm_integration import LLMIntegration  # <--- 引入统一的 LLM 管家

class QueryParser:
    def __init__(self):
        # === 核心修改：不再直接连接 OpenAI，而是使用 LLMIntegration ===
        # 这样它就能自动读取 .env 里的 DASHSCOPE_API_KEY 了
        self.llm = LLMIntegration()

    def _rule_parse(self, query: str) -> dict:
        """Fast deterministic parser for common demo queries, avoiding an LLM hop."""
        result = {}
        text = query or ""

        age_match = re.search(r"(\d{1,3})\s*岁", text)
        if age_match:
            result["age"] = int(age_match.group(1))

        price_match = re.search(r"(\d{3,6})\s*(?:元|块|￥|以下|以内|内|预算)", text)
        if price_match:
            result["price_max"] = int(price_match.group(1))

        city_match = re.search(r"(北京|上海|广州|深圳|成都|武汉|杭州|南京|重庆|天津|西安|苏州|长沙|郑州|青岛|厦门|朝阳区|海淀区|通州|房山)", text)
        if city_match:
            result["city"] = city_match.group(1)

        diseases = []
        for disease in ("高血压", "糖尿病", "冠心病", "癌症", "恶性肿瘤", "肺炎", "脑梗", "心梗", "阿尔茨海默病"):
            if disease in text:
                diseases.append(disease)
        if diseases:
            result["disease"] = diseases

        drugs = []
        for drug in ("阿司匹林", "二甲双胍", "胰岛素", "硝苯地平", "氨氯地平"):
            if drug in text:
                drugs.append(drug)
        if drugs:
            result["drug"] = drugs

        if any(k in text for k in ("养老院", "养老机构", "护理院", "床位", "月费", "养老")):
            result["intent"] = "nursing_home_search"
        elif any(k in text for k in ("保险", "投保", "保费", "医疗险", "重疾险", "防癌险", "护理险", "保障")):
            result["intent"] = "insurance_query"
        elif diseases or drugs or any(k in text for k in ("症状", "并发症", "治疗", "药")):
            result["intent"] = "medical_query"
        else:
            result["intent"] = "general_qa"

        result["_parser"] = "rule"
        return result

    def parse(self, query: str) -> dict:
        """
        利用大模型解析用户查询意图和关键实体。
        """
        rule_result = self._rule_parse(query)
        if rule_result.get("intent") != "general_qa" or any(k in rule_result for k in ("age", "price_max", "city", "disease", "drug")):
            return rule_result

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
        response_text = ""

        try:
            # 调用 LLM 生成解析结果
            response_text = self.llm.generate(
                prompt=user_prompt, 
                system_prompt=system_prompt,
                temperature=0.1, # 意图识别需要精确，温度调低
                max_tokens=200,
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
