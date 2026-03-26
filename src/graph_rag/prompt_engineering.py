# Prompt 工程：问答模板与上下文组装
from typing import Optional

# 标准问答模板（与 info.md 一致）
PROMPT_TEMPLATE = """
基于以下知识图谱信息，回答用户问题：

知识图谱信息：
{graph_context}

用户问题：{question}

请生成准确、专业的回答，并注明信息来源。
回答格式：
• 直接答案

• 依据：[相关三元组]

"""


def build_qa_prompt(
    graph_context: str,
    question: str,
    template: Optional[str] = None,
    **kwargs: str,
) -> str:
    """
    组装 RAG 问答 Prompt。
    Args:
        graph_context: 检索到的子图文本。
        question: 用户问题。
        template: 模板字符串，默认使用 PROMPT_TEMPLATE。
        **kwargs: 额外占位符替换。
    Returns:
        填充后的完整 prompt 字符串。
    """
    t = template or PROMPT_TEMPLATE
    prompt = t.format(
        graph_context=graph_context,
        question=question,
        **kwargs,
    )
    return prompt


def get_system_prompt(role: Optional[str] = None) -> str:
    """
    返回系统角色 Prompt（可选）。
    Args:
        role: 角色描述，如「保险+医养领域知识助手」。
    Returns:
        系统 prompt 字符串。
    """
    default = "你是保险与医养知识图谱问答助手，请根据提供的知识图谱信息准确、专业地回答问题。"
    return role if role else default
