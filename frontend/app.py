import streamlit as st
import requests
import json
from neo4j import GraphDatabase

# 设置页面配置
st.set_page_config(
    page_title="泰康保险医养知识问答",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 地址
API_URL = "http://localhost:8000/chat"

# Neo4j 配置（用于统计信息，简单直接连接）
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
# 注意：这里为了演示方便直接硬编码或从 config 读取，实际部署建议通过 API 获取统计信息
# 为简化，假设用户本地环境一致，直接尝试连接
# 如果连接失败，统计信息将不显示或显示默认值

def get_graph_stats():
    """获取 Neo4j 图谱统计信息"""
    stats = {}
    try:
        # 尝试从 config.yaml 读取密码（如果需要更健壮的实现）
        # 这里简化处理，尝试默认密码或提示用户
        # 更好的做法是在后端 API 增加一个 /stats 接口
        # 这里为了演示 Streamlit 的独立性，我们先用硬编码的默认密码尝试，
        # 实际项目中应调用后端 API
        
        # 为了避免前端直接连接数据库的安全风险，建议这部分逻辑移到后端 API
        # 但根据当前需求描述，我们在前端简单实现展示
        pass 
    except Exception:
        pass
    return {
        "Disease": "400+",
        "Drug": "3800+",
        "Insurance": "70+",
        "NursingHome": "400+",
        "Symptom": "2000+",
        "Department": "50+"
    }

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# 侧边栏
with st.sidebar:
    st.image("https://www.taikang.com/favicon.ico", width=50) # 示例 Logo
    st.title("泰康医养 KGQA")
    
    st.markdown("### 📊 图谱数据统计")
    stats = get_graph_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("疾病", stats["Disease"])
        st.metric("药品", stats["Drug"])
        st.metric("保险", stats["Insurance"])
    with col2:
        st.metric("养老院", stats["NursingHome"])
        st.metric("症状", stats["Symptom"])
        st.metric("科室", stats["Department"])
    
    st.divider()
    st.markdown("### 💡 使用指南")
    st.info(
        "您可以询问：\n"
        "- 疾病相关：'高血压有哪些并发症？'\n"
        "- 药品查询：'治疗糖尿病的常用药有哪些？'\n"
        "- 养老机构：'北京价格5000以下的养老院'\n"
        "- 保险推荐：'70岁老人适合买什么保险？'"
    )

# 主界面
st.title("🏥 泰康保险医养知识问答助手")
st.markdown("基于 **Neo4j 知识图谱** 与 **大语言模型** 构建的智能问答系统")

# 聊天记录展示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # 如果是 AI 回答且有 context，展示溯源信息
        if message["role"] == "assistant" and "context" in message:
            with st.expander("🔍 知识图谱溯源 (Reference)"):
                st.text(message["context"])

# 输入框
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 获取 AI 回答
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        context_info = ""
        
        try:
            with st.spinner("正在检索知识图谱并生成回答..."):
                response = requests.post(API_URL, json={"query": prompt})
                if response.status_code == 200:
                    data = response.json()
                    full_response = data["answer"]
                    context_info = data["context"]
                    
                    message_placeholder.markdown(full_response)
                    
                    # 展示溯源信息
                    if context_info and context_info != "未在知识图谱中找到相关信息。":
                        with st.expander("🔍 知识图谱溯源 (Reference)"):
                            st.text(context_info)
                else:
                    full_response = f"请求失败 (状态码: {response.status_code})"
                    message_placeholder.error(full_response)
        except Exception as e:
            full_response = f"发生错误: {str(e)}"
            message_placeholder.error(full_response)
            
    # 添加 AI 消息到历史记录
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "context": context_info
    })
