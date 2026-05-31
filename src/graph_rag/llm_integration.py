# # src/graph_rag/llm_integration.py
# import os  # <--- 新增：引入系统模块
# from typing import List, Dict, Any, Optional, Generator
# from src.utils.config_loader import config  # <--- 关键修改：直接引入全局配置
# from src.utils.logger import logger
# from dotenv import load_dotenv # <--- 新增：确保加载 .env


# # 强制加载一次环境变量
# load_dotenv()
# class LLMIntegration:
#     """大模型集成：自动从 config.yaml 读取配置，统一封装。"""

#     def __init__(self):
#         # === 核心修改：优先从 config 中读取，不再依赖硬编码的默认值 ===
#         llm_conf = config.get("llm", {})
        
#         self.model_type = llm_conf.get("model_type", "api")
#         self.api_key = llm_conf.get("api_key")
#         self.api_base = llm_conf.get("api_base")
#         self.model_name = llm_conf.get("model_name") # 这里会读到 config.yaml 里的 "qwen-turbo"
        
#         self._client = None
        
#         # 打印一下，方便调试看到底读到了啥
#         logger.info(f"LLM Init: Model={self.model_name}, BaseURL={self.api_base}")

#     def _get_client(self):
#         """懒加载 OpenAI 兼容客户端"""
#         if self._client is not None:
#             return self._client
#         try:
#             from openai import OpenAI
#             # 校验一下 Key 是否存在
#             if not self.api_key or "sk-" not in self.api_key:
#                 logger.warning("API Key 似乎未正确配置，请检查 config.yaml")
                
#             self._client = OpenAI(
#                 api_key=self.api_key, 
#                 base_url=self.api_base
#             )
#             return self._client
#         except Exception as e:
#             logger.error(f"LLM 客户端初始化失败: {e}")
#             raise RuntimeError(f"LLM Client Error: {e}")

#     def chat(
#         self,
#         messages: List[Dict[str, str]],
#         temperature: float = 0.3, # RAG 场景建议温度低一点，更严谨
#         max_tokens: Optional[int] = None,
#         **kwargs: Any,
#     ) -> str:
#         """多轮对话式生成。"""
#         if self.model_type == "api":
#             try:
#                 client = self._get_client()
#                 resp = client.chat.completions.create(
#                     model=self.model_name, # <--- 使用配置里的模型名
#                     messages=messages,
#                     temperature=temperature,
#                     max_tokens=max_tokens or 1024,
#                     **kwargs,
#                 )
#                 return (resp.choices[0].message.content or "").strip()
#             except Exception as e:
#                 logger.error(f"调用大模型 API 失败: {e}")
#                 return "抱歉，系统暂时无法生成回答 (LLM API Error)。"
        
#         return "（当前配置为非 API 模式，未实现本地模型调用逻辑）"

#     def generate(
#         self,
#         prompt: str,
#         system_prompt: Optional[str] = None,
#         temperature: float = 0.3,
#         **kwargs: Any,
#     ) -> str:
#         """单轮生成（RAG 问答）。"""
#         messages = []
#         if system_prompt:
#             messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": prompt})
#         return self.chat(messages, temperature=temperature, **kwargs)


# # # 大模型集成：Qwen 本地 / 百炼 API（OpenAI 兼容）
# # from typing import List, Dict, Any, Optional, Generator


# # class LLMIntegration:
# #     """大模型集成：统一封装本地模型与云端 API。"""

# #     def __init__(
# #         self,
# #         model_type: str = "local",
# #         model_path: Optional[str] = None,
# #         api_key: Optional[str] = None,
# #         api_base: Optional[str] = None,
# #         model_name: Optional[str] = None,
# #         **kwargs: Any,
# #     ):
# #         self.model_type = model_type
# #         self.model_path = model_path
# #         self.api_key = api_key
# #         self.api_base = api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 百炼兼容
# #         self.model_name = model_name or "qwen-turbo"
# #         self._client = None

# #     def _get_client(self):
# #         """懒加载 OpenAI 兼容客户端（用于 api 模式）。"""
# #         if self._client is not None:
# #             return self._client
# #         try:
# #             from openai import OpenAI
# #             self._client = OpenAI(api_key=self.api_key or "dummy", base_url=self.api_base)
# #             return self._client
# #         except Exception as e:
# #             raise RuntimeError(f"LLM 客户端初始化失败: {e}") from e

# #     def chat(
# #         self,
# #         messages: List[Dict[str, str]],
# #         temperature: float = 0.7,
# #         max_tokens: Optional[int] = None,
# #         **kwargs: Any,
# #     ) -> str:
# #         """多轮对话式生成。"""
# #         if self.model_type == "api" and self.api_key and self.api_key != "your_api_key":
# #             client = self._get_client()
# #             resp = client.chat.completions.create(
# #                 model=self.model_name,
# #                 messages=messages,
# #                 temperature=temperature,
# #                 max_tokens=max_tokens or 1024,
# #                 **kwargs,
# #             )
# #             return (resp.choices[0].message.content or "").strip()
# #         return "（当前为未配置或本地模式，仅返回占位。请在 config.yaml 中配置 llm.model_type=api 与 api_key 后使用百炼等 API。）"

# #     def generate(
# #         self,
# #         prompt: str,
# #         system_prompt: Optional[str] = None,
# #         temperature: float = 0.7,
# #         max_tokens: Optional[int] = None,
# #         **kwargs: Any,
# #     ) -> str:
# #         """单轮生成（RAG 问答）。"""
# #         messages = []
# #         if system_prompt:
# #             messages.append({"role": "system", "content": system_prompt})
# #         messages.append({"role": "user", "content": prompt})
# #         return self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

# #     def stream_generate(
# #         self,
# #         prompt: str,
# #         system_prompt: Optional[str] = None,
# #         **kwargs: Any,
# #     ) -> Generator[str, None, None]:
# #         """流式生成（可选）。"""
# #         messages = []
# #         if system_prompt:
# #             messages.append({"role": "system", "content": system_prompt})
# #         messages.append({"role": "user", "content": prompt})
# #         if self.model_type == "api" and self.api_key and self.api_key != "your_api_key":
# #             client = self._get_client()
# #             stream = client.chat.completions.create(
# #                 model=self.model_name,
# #                 messages=messages,
# #                 stream=True,
# #                 **kwargs,
# #             )
# #             for chunk in stream:
# #                 if chunk.choices and chunk.choices[0].delta.content:
# #                     yield chunk.choices[0].delta.content
# #         else:
# #             yield self.generate(prompt, system_prompt=system_prompt, **kwargs)





import os  # <--- 新增：引入系统模块
from typing import List, Dict, Any, Optional, Generator
from src.utils.config_loader import config
from src.utils.logger import logger
from dotenv import load_dotenv # <--- 新增：确保加载 .env

# 强制加载一次环境变量
load_dotenv()

class LLMIntegration:
    """大模型集成：优先读 config，其次读环境变量。"""

    def __init__(self):
        llm_conf = config.get("llm", {})
        
        self.model_type = llm_conf.get("model_type", "api")
        self.model_name = (
            os.getenv("DEEPSEEK_MODEL")
            or os.getenv("OPENAI_MODEL")
            or llm_conf.get("model_name", "deepseek-v4-pro")
        )
        self.api_base = (
            llm_conf.get("api_base")
            or os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
        )
        
        # config.yaml → 环境变量（支持 DeepSeek / 百炼兼容 / OpenAI 风格）
        self.api_key = (
            llm_conf.get("api_key")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        
        # 同样的逻辑也可以用于 Neo4j 密码（虽然这里只处理 LLM）
        
        self._client = None
        
        # 调试日志：只打印前几位，防止泄露
        masked_key = (self.api_key[:8] + "...") if self.api_key else "未找到!"
        logger.info(f"LLM Init: Model={self.model_name}, Key={masked_key}")

    # ... (后面的代码 _get_client, chat, generate 等保持不变) ...
    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            if not self.api_key:
                logger.error("❌ 致命错误: 未找到 API Key！请检查 config.yaml 或 .env 文件")
            
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=20.0,
                max_retries=0,
            )
            return self._client
        except Exception as e:
            logger.error(f"LLM 客户端初始化失败: {e}")
            raise
    
    # 下面的 chat 和 generate 函数直接复用之前的即可，不用改
    def chat(self, messages, temperature=0.3, max_tokens=None, **kwargs):
        if self.model_type == "api":
            try:
                client = self._get_client()
                resp = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 1024,
                    **kwargs,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as e:
                logger.error(f"调用大模型 API 失败: {e}")
                return "抱歉，系统暂时无法生成回答 (LLM API Error)。"
        return "非 API 模式"

    def generate(self, prompt, system_prompt=None, temperature=0.3, **kwargs):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, temperature=temperature, **kwargs)
