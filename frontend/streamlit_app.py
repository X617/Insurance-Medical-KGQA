import streamlit as st
import requests
import re

# ==========================================
# 1. 配置与全局样式 (Visual Design & CSS)
# ==========================================
st.set_page_config(
    page_title="泰康医养智能助手",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 品牌色定义
PRIMARY_COLOR = "#2E86DE"  # 医疗蓝 (信任/专业)
ACCENT_COLOR = "#00B894"   # 生命绿 (健康)
BG_COLOR = "#F4F7F6"       # 浅灰背景 (护眼)
CARD_BG = "#FFFFFF"        # 卡片白
TEXT_COLOR = "#2D3436"     # 深灰字 (高对比度)

# 注入自定义 CSS
st.markdown(f"""
<style>
    /* 全局背景与字体 */
    .stApp {{
        background-color: {BG_COLOR};
        font-family: "Microsoft YaHei", "Segoe UI", Roboto, sans-serif;
    }}
    
    /* 标题样式 */
    h1, h2, h3 {{
        color: {PRIMARY_COLOR} !important;
        font-weight: 600;
    }}
    
    /* 侧边栏优化 */
    [data-testid="stSidebar"] {{
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }}
    
    /* 聊天气泡/卡片通用样式 */
    .chat-card {{
        background-color: {CARD_BG};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); /* 轻微阴影 */
        border-left: 5px solid {PRIMARY_COLOR}; /* 左侧强调线 */
    }}
    
    /* 推荐产品卡片 (特殊强调) */
    .product-card {{
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(46, 134, 222, 0.1);
        transition: transform 0.2s;
    }}
    .product-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(46, 134, 222, 0.15);
    }}
    
    /* 关键数据高亮 (适老设计) */
    .highlight-data {{
        color: {ACCENT_COLOR};
        font-weight: bold;
        font-size: 1.1em;
    }}
    
    /* 按钮美化 */
    .stButton>button {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border-radius: 25px;
        height: 50px;
        padding: 0 30px;
        font-size: 16px;
        border: none;
        box-shadow: 0 4px 6px rgba(46, 134, 222, 0.3);
    }}
    .stButton>button:hover {{
        background-color: #2674c2;
    }}
    
    /* 调整正文字号 (适老) */
    p, li {{
        font-size: 16px !important;
        line-height: 1.6 !important;
        color: {TEXT_COLOR};
    }}
</style>
""", unsafe_allow_html=True)

# API 地址
API_URL = "http://127.0.0.1:8000/chat"

# ==========================================
# 2. 功能函数
# ==========================================

def get_graph_stats():
    """模拟图谱统计数据 (实际项目可调后端 API)"""
    return {
        "Disease": "403",
        "Drug": "3,827",
        "Insurance": "78",
        "NursingHome": "469",
        "Symptom": "2,000+"
    }

# ==========================================
# 修复点 1：消除 HTML 缩进，防止被解析为代码块
# ==========================================
# def format_product_card(text_segment):
#     """
#     渲染单个产品卡片。
#     """
#     # 1. 提取标题
#     lines = text_segment.strip().split('\n')
#     title_line = lines[0]
#     # 尝试提取 "1. 蓝医保..." 中的 "蓝医保..."
#     title_match = re.match(r"^\d+\.\s*(.*)|【(.*)】|\*\*(.*)\*\*", title_line)
    
#     if title_match:
#         # 取匹配到的非空组
#         title = next((g for g in title_match.groups() if g), "推荐方案")
#         # 清理可能残留的 markdown 符号
#         title = title.replace("**", "").strip()
#     else:
#         title = title_line.replace("**", "").strip() # 兜底清理

#     # 2. 提取并格式化内容
#     # 我们希望把 "- 投保年龄：" 这样的字段加粗显示
#     content_lines = []
#     for line in lines[1:]:
#         line = line.strip()
#         if not line: continue
        
#         # 正则匹配关键字段（支持冒号中文或英文）
#         # 例如匹配 "- 投保年龄：" 或 "- 投保年龄:"
#         line = re.sub(r"^[-*]\s*(.*?)([:：])", r"<b>\1\2</b>", line)
#         content_lines.append(line)
    
#     # 合并内容
#     content_html = "<br>".join(content_lines)
    
#     # 3. 构建 HTML (注意：这里不要有缩进，顶格写！)
#     html_code = f"""
# <div class="product-card">
#     <div style="display: flex; align-items: center; margin-bottom: 10px;">
#         <span style="font-size: 24px; margin-right: 10px;">🛡️</span>
#         <h3 style="margin:0; color: #2E86DE;">{title}</h3>
#     </div>
#     <div style="color: #555; font-size: 16px; line-height: 1.6;">
#         {content_html}
#     </div>
# </div>
# """
#     st.markdown(html_code, unsafe_allow_html=True)

# ==========================================
# 修复点 2：增强总结文字的剥离逻辑
# ==========================================
# def display_smart_answer(answer_text):
#     """
#     智能解析回答。
#     """
#     # 只有当包含 "1." 且 "2." 时才启用卡片模式
#     if ("1." in answer_text and "2." in answer_text) and ("保险" in answer_text or "养老院" in answer_text):
        
#         # 按数字列表切分
#         segments = re.split(r'(?=\n\d+\.)', answer_text)
        
#         # 1. 处理开场白
#         if segments and not re.match(r'\d+\.', segments[0].strip()):
#             st.markdown(f"<div style='margin-bottom:15px'>{segments[0]}</div>", unsafe_allow_html=True)
#             segments = segments[1:]
        
#         # 2. 处理末尾总结 (关键修复)
#         conclusion = ""
#         if segments:
#             last_seg = segments[-1]
#             # 尝试通过“双换行”或关键词来切分总结
#             if "\n\n" in last_seg:
#                 parts = last_seg.rsplit("\n\n", 1)
#                 # 如果切出来的后半段不包含列表项特征，就认定为总结
#                 if len(parts) == 2 and not re.match(r'\d+\.', parts[1].strip()):
#                     segments[-1] = parts[0]
#                     conclusion = parts[1]
#             elif "综上" in last_seg or "建议" in last_seg:
#                 # 备用逻辑：如果最后一段话里有“综上”，尝试强行切分（可选）
#                 pass

#         # 3. 渲染卡片
#         if len(segments) > 0:
#             cols = st.columns(min(len(segments), 2))
#             for i, seg in enumerate(segments):
#                 if seg.strip():
#                     with cols[i % len(cols)]:
#                         format_product_card(seg.strip())

#         # 4. 渲染总结
#         if conclusion:
#             st.info(conclusion) # 使用 info 样式展示总结，更清晰

#     else:
#         # 普通模式
#         st.markdown(f"""
# <div class="chat-card">
# {answer_text.replace(chr(10), '<br>')}
# </div>
# """, unsafe_allow_html=True)

 

# --- 侧边栏 ---
with st.sidebar:
    st.image("https://www.taikang.com/favicon.ico", width=60) 
    st.title("泰康医养 KGQA")
    st.markdown("---")
    
    st.markdown("### 📊 知识储备")
    stats = get_graph_stats()
    
    # 统计数据使用指标展示
    c1, c2 = st.columns(2)
    c1.metric("疾病库", stats["Disease"], delta_color="normal")
    c1.metric("保险产品", stats["Insurance"])
    c2.metric("药品库", stats["Drug"])
    c2.metric("合作养老院", stats["NursingHome"])
    
    st.markdown("---")
    st.markdown("### ⚙️ 偏好设置")
    temperature = st.slider("严谨度 (Temperature)", 0.0, 1.0, 0.3, help="数值越低，回答越保守严谨；数值越高，回答越发散。")
    
    st.info("💡 **提示**：我是基于知识图谱的专家助手，请尽量描述清楚您的年龄和健康状况，以便我为您推荐精准的保险或养老方案。")

# --- 主区域 ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown("# 🏥")
with col_title:
    st.title("泰康保险医养智能助手")
    st.caption("基于 GraphRAG 技术 | 您的专属健康财富管家")

# 初始化历史记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 展示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # 核心修改：直接使用 st.markdown，不再调用 display_smart_answer
        st.markdown(msg["content"])
        
        # 如果是 AI 回答且有 context，展示溯源信息
        if msg["role"] == "assistant" and "context" in msg:
            # 只有当 context 有实质内容时才显示
            if msg["context"] and "已屏蔽" not in msg["context"] and "检索失败" not in msg["context"]:
                 with st.expander("📚 参考来源 (Knowledge Context)"):
                    st.info(msg["context"])

# --- 输入区域 ---
prompt = st.chat_input("请描述您的情况，例如：70岁老人有高血压，推荐什么保险？")

# --- 2. 输入框与回答生成 (简化版) ---
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 获取 AI 回答
    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        with st.spinner("👩‍⚕️ 正在分析您的需求..."):
            try:
                # 构造请求数据 (带历史记录)
                # 限制历史记录长度，防止 Token 溢出
                history_payload = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.messages[:-1]
                ][-6:] # 只取最近6条

                payload = {
                    "query": prompt,
                    "history": history_payload
                }
                
                # 调用后端
                response = requests.post(API_URL, json=payload, timeout=60)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "抱歉，由于网络原因未能生成回答。")
                    context = data.get("context", "")
                    
                    # 核心修改：直接渲染 Markdown
                    # Streamlit 会自动把 **加粗** 渲染得很好看
                    placeholder.markdown(answer)
                    
                    # 展示溯源
                    if context and "已屏蔽" not in context and len(str(context)) > 5:
                        with st.expander("📚 参考来源 (Knowledge Context)"):
                            st.info(context)
                    
                    # 保存到历史
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "context": context
                    })
                else:
                    err_msg = f"服务暂时不可用 (状态码: {response.status_code})"
                    placeholder.error(err_msg)
                    
            except Exception as e:
                placeholder.error(f"发生连接错误: {e}")