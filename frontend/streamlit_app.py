import base64
import html
import json
import math
import os
from typing import Any, Dict, List

import requests
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="泰康保险医养智能助手",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_ROOT = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
CHAT_URL = os.getenv("API_URL", f"{API_ROOT}/chat")
STREAM_URL = f"{API_ROOT}/chat/stream"

PRIMARY = "#2563eb"
SECONDARY = "#0f766e"
WARNING = "#f59e0b"
SURFACE = "#ffffff"
BG = "#f6f8fb"
TEXT = "#172033"


st.markdown(
    f"""
<style>
.stApp {{ background: {BG}; color: {TEXT}; }}
[data-testid="stSidebar"] {{ background: #ffffff; border-right: 1px solid #e5e7eb; }}
h1, h2, h3 {{ color: {PRIMARY} !important; letter-spacing: 0; }}
.hero {{
    padding: 1.4rem 0 0.8rem 0;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 1.2rem;
}}
.hero-title {{ font-size: 2.15rem; font-weight: 800; color: {PRIMARY}; }}
.hero-subtitle {{ font-size: 1rem; color: #4b5563; margin-top: .35rem; }}
.metric-card {{
    background: {SURFACE};
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1.05rem;
    min-height: 104px;
    margin-bottom: .75rem;
}}
.metric-label {{ color: #64748b; font-size: .88rem; }}
.metric-value {{ color: #111827; font-size: 1.75rem; font-weight: 760; }}
.feature-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: .85rem .9rem;
    margin: .8rem 0;
}}
.feature-title {{ font-weight: 760; color: #172033; margin-bottom: .35rem; }}
.feature-copy {{ color: #64748b; font-size: .9rem; line-height: 1.55; }}
.scenario-button button {{
    border-radius: 8px !important;
    min-height: 48px;
    white-space: normal;
    text-align: left;
}}
.rec-card {{
    background: {SURFACE};
    border: 1px solid #dbe3ef;
    border-left: 5px solid {PRIMARY};
    border-radius: 8px;
    padding: .95rem 1rem;
    margin: .65rem 0;
}}
.rec-card.nursing {{ border-left-color: {SECONDARY}; }}
.rec-title {{ font-weight: 760; color: #111827; font-size: 1.02rem; }}
.rec-meta {{ color: #475569; font-size: .92rem; line-height: 1.55; margin-top: .35rem; }}
.tag {{
    display: inline-block;
    padding: .16rem .45rem;
    border-radius: 6px;
    background: #e0f2fe;
    color: #075985;
    font-size: .78rem;
    margin: .22rem .25rem .05rem 0;
}}
.trace-step {{
    border: 1px solid #e5e7eb;
    background: #fff;
    border-radius: 8px;
    padding: .7rem .85rem;
    margin-bottom: .55rem;
}}
.trace-json {{
    margin: .55rem 0 0 0;
    padding: .65rem;
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    color: #334155;
    font-size: .78rem;
    line-height: 1.45;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}}
.trace-agent {{ font-weight: 750; color: {PRIMARY}; }}
.live-trace {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: .65rem .75rem;
}}
.live-step {{
    padding: .22rem 0;
    color: #172033;
    font-size: .92rem;
}}
.source-line {{
    border-bottom: 1px solid #eef2f7;
    padding: .55rem 0;
}}
.small-muted {{ color: #64748b; font-size: .9rem; }}
</style>
""",
    unsafe_allow_html=True,
)


def api_get(path: str, timeout: float = 2.0, **params: Any) -> Dict[str, Any]:
    try:
        resp = requests.get(f"{API_ROOT}{path}", params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


@st.cache_data(ttl=30, show_spinner=False)
def get_graph_stats() -> Dict[str, str]:
    data = api_get("/graph/stats")
    labels = data.get("labels") or {}
    if not labels:
        return {"Disease": "403", "Drug": "3,827", "Insurance": "78", "NursingHome": "469", "Relations": "-"}
    return {
        "Disease": f"{labels.get('Disease', 0):,}",
        "Drug": f"{labels.get('Drug', 0):,}",
        "Insurance": f"{labels.get('Insurance', 0):,}",
        "NursingHome": f"{labels.get('NursingHome', 0):,}",
        "Relations": f"{data.get('relationships', 0):,}",
    }


@st.cache_data(ttl=120, show_spinner=False)
def cached_subgraph(seed: str, depth: int) -> Dict[str, Any]:
    return api_get("/graph/subgraph", query=seed, depth=depth, limit=50, timeout=6.0)


def render_metric(label: str, value: str) -> None:
    st.markdown(
        f"""
<div class="metric-card">
  <div class="metric-label">{html.escape(label)}</div>
  <div class="metric-value">{html.escape(value)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def label_color(label: str) -> str:
    return {
        "Disease": "#ef4444",
        "Insurance": "#2563eb",
        "Drug": "#8b5cf6",
        "NursingHome": "#0f766e",
        "Symptom": "#f97316",
        "Population": "#f59e0b",
        "City": "#06b6d4",
        "Service": "#22c55e",
    }.get(label, "#64748b")


def render_graph(graph: Dict[str, Any], height: int = 320) -> None:
    nodes = (graph.get("nodes") or [])[:28]
    node_ids = {node["id"] for node in nodes}
    edges = [
        edge for edge in (graph.get("edges") or [])
        if edge.get("source") in node_ids and edge.get("target") in node_ids
    ][:48]
    if not nodes:
        st.info("本轮没有可视化子图。可以换一个包含疾病、保险或养老院实体的问题。")
        return

    width = 940
    cx, cy = width / 2, height / 2
    radius = max(105, min(width, height) * 0.36)
    positions = {}
    for idx, node in enumerate(nodes):
        angle = 2 * math.pi * idx / max(1, len(nodes))
        positions[node["id"]] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    edge_svg = []
    for edge in edges:
        if edge["source"] not in positions or edge["target"] not in positions:
            continue
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        edge_svg.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#94a3b8" stroke-width="1.8"><title>{html.escape(edge.get("type", ""))}</title></line>'
        )

    node_svg = []
    for node in nodes:
        x, y = positions[node["id"]]
        name = str(node.get("name") or node.get("label") or "")[:14]
        label = node.get("label", "Entity")
        color = label_color(label)
        node_svg.append(
            f"""
<g class="node">
  <circle cx="{x:.1f}" cy="{y:.1f}" r="28" fill="{color}" opacity="0.92">
    <title>{html.escape(label)}: {html.escape(str(node.get("name", "")))}</title>
  </circle>
  <text x="{x:.1f}" y="{y + 43:.1f}" text-anchor="middle" font-size="12" fill="#111827">{html.escape(name)}</text>
</g>
"""
        )

    legend_items = "".join(
        f'<span style="margin-right:14px;"><b style="color:{label_color(label)};">●</b> {label}</span>'
        for label in sorted({n.get("label", "Entity") for n in nodes})
    )
    svg = f"""
<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:10px;">
  <div style="font:13px sans-serif;color:#475569;margin:2px 0 8px 4px;">{legend_items}</div>
  <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">
    <rect x="0" y="0" width="{width}" height="{height}" fill="#fbfdff"/>
    {''.join(edge_svg)}
    {''.join(node_svg)}
  </svg>
</div>
"""
    components.html(svg, height=height + 56, scrolling=False)


def render_recommendations(recommendations: Dict[str, Any]) -> None:
    insurance = recommendations.get("insurance") or []
    nursing = recommendations.get("nursing_homes") or []
    if not insurance and not nursing:
        return

    st.markdown("### 结构化推荐")
    if insurance:
        st.markdown("**保险产品候选**")
        for item in insurance[:4]:
            tags = "".join(f'<span class="tag">{html.escape(str(tag))}</span>' for tag in item.get("risk_tags", []))
            st.markdown(
                f"""
<div class="rec-card">
  <div class="rec-title">{html.escape(str(item.get("name", "保险产品")))}</div>
  <div>{tags}</div>
  <div class="rec-meta">
    险种：{html.escape(str(item.get("category", "未知")))}　
    投保年龄：{html.escape(str(item.get("age_limit", "未标注")))}　
    推荐分：{html.escape(str(item.get("score", "-")))}
    <br/>推荐理由：{html.escape(str(item.get("suitable_reason", "")))}
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
    if nursing:
        st.markdown("**养老机构候选**")
        rows = [
            {
                "名称": item.get("name"),
                "价格": item.get("price"),
                "地址": item.get("address"),
                "床位": item.get("beds"),
                "特色服务": item.get("services"),
                "推荐分": item.get("score"),
            }
            for item in nursing[:6]
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_reasoning_paths(paths: List[Dict[str, Any]]) -> None:
    if not paths:
        return
    st.markdown("**StepChain 证据路径**")
    for item in paths[:6]:
        path = " → ".join(str(part) for part in item.get("path", []) if part)
        st.markdown(
            f"""
<div class="trace-step">
  <div class="trace-agent">{html.escape(str(item.get("title", "证据路径")))}</div>
  <div>{html.escape(path)}</div>
  <div class="small-muted">{html.escape(str(item.get("evidence", ""))[:220])}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_sources(sources: List[Dict[str, Any]]) -> None:
    if not sources:
        st.info("暂无结构化证据来源。")
        return
    for src in sources[:10]:
        st.markdown(
            f"""
<div class="source-line">
  <b>{html.escape(str(src.get("label") or src.get("type") or "Source"))}</b>
  · {html.escape(str(src.get("name", "")))}
  <span class="small-muted"> · hybrid={html.escape(str(src.get("hybrid_score", src.get("score", "-"))))}</span>
  <div class="small-muted">{html.escape(str(src.get("snippet", ""))[:260])}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_trace(trace: List[Dict[str, Any]]) -> None:
    if not trace:
        st.info("暂无 Agent trace。")
        return
    for step in trace:
        payload = json.dumps(
            {"input": step.get("input"), "output": step.get("output")},
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        st.markdown(
            f"""
<div class="trace-step">
  <div><span class="trace-agent">{html.escape(str(step.get("agent", "Agent")))}</span>
  · {html.escape(str(step.get("status", "")))}</div>
  <div class="small-muted">{html.escape(str(step.get("note", "")))}</div>
  <pre class="trace-json">{html.escape(payload[:1800])}</pre>
</div>
""",
            unsafe_allow_html=True,
        )


def upload_document_panel() -> None:
    st.markdown("### 资料解析工作台")
    uploaded = st.file_uploader("上传保险条款 PDF / txt / 图片", type=["pdf", "txt", "png", "jpg", "jpeg", "webp"])
    if uploaded and st.button("解析资料", use_container_width=True):
        encoded = base64.b64encode(uploaded.getvalue()).decode("ascii")
        payload = {"filename": uploaded.name, "content_base64": encoded, "mime_type": uploaded.type}
        try:
            resp = requests.post(f"{API_ROOT}/documents/upload", json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.document_id = data["document_id"]
                st.session_state.document_filename = data["filename"]
                st.session_state.extracted_triples = []
                st.success(f"已解析：{data['filename']}，共 {data['chars']} 字")
                st.text_area("资料摘要", data["summary"], height=150)
            else:
                st.error(resp.json().get("detail", resp.text))
        except Exception as exc:
            st.error(f"资料上传失败：{exc}")

    if st.session_state.get("document_id"):
        st.info(f"当前资料：{st.session_state.get('document_filename', st.session_state.document_id)}")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("抽取三元组", use_container_width=True):
                resp = requests.post(
                    f"{API_ROOT}/documents/{st.session_state.document_id}/extract-triples",
                    timeout=80,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.extracted_triples = data.get("triples", [])
                    st.success(f"抽取完成：{len(st.session_state.extracted_triples)} 条，方法：{data.get('method')}")
                else:
                    st.error(resp.text)
        with col_b:
            triples = st.session_state.get("extracted_triples") or []
            if st.button("Dry-run 校验", use_container_width=True, disabled=not triples):
                resp = requests.post(
                    f"{API_ROOT}/admin/ingest-triples",
                    params={"dry_run": "true"},
                    json={"triples": triples},
                    timeout=20,
                )
                st.json(resp.json() if resp.status_code == 200 else {"error": resp.text})

        if st.session_state.get("extracted_triples"):
            edited = st.data_editor(
                st.session_state.extracted_triples,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="triple_editor",
            )
            if st.button("确认写入 Neo4j", type="primary", use_container_width=True):
                triples_to_write = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
                resp = requests.post(
                    f"{API_ROOT}/admin/ingest-triples",
                    params={"dry_run": "false"},
                    json={"triples": triples_to_write},
                    timeout=30,
                )
                if resp.status_code == 200:
                    st.success(f"已写入 {resp.json().get('inserted', 0)} 条三元组。")
                    get_graph_stats.clear()
                    cached_subgraph.clear()
                else:
                    st.error(resp.text)

        q = st.text_input("围绕已上传资料追问", placeholder="例如：这份条款 70 岁能不能买？")
        if q and st.button("询问资料", use_container_width=True):
            resp = requests.post(
                f"{API_ROOT}/documents/{st.session_state.document_id}/ask",
                json={"query": q},
                timeout=60,
            )
            if resp.status_code == 200:
                st.markdown(resp.json()["answer"])
            else:
                st.error(resp.text)


def metrics_panel() -> None:
    st.markdown("### 系统评测与性能仪表盘")
    metrics = api_get("/metrics/demo", timeout=4.0)
    if not metrics:
        st.warning("暂未获取到后端指标，请确认 FastAPI 已启动。")
        return
    cols = st.columns(4)
    cards = [
        ("平均响应", f"{metrics.get('avg_latency_ms', 0)} ms"),
        ("缓存命中率", f"{metrics.get('cache_hit_rate', 0) * 100:.1f}%"),
        ("图谱命中率", f"{metrics.get('graph_hit_rate', 0) * 100:.1f}%"),
        ("规则过滤", str(metrics.get("rule_filter_hits", 0))),
    ]
    for col, (label, value) in zip(cols, cards):
        with col:
            render_metric(label, value)
    graph_stats = metrics.get("graph_stats", {})
    st.markdown(
        f"图谱连接：**{'正常' if metrics.get('graph_connected') else '异常'}**　"
        f"节点标签：`{len(graph_stats.get('labels', {}))}`　"
        f"关系数：`{graph_stats.get('relationships', 0)}`"
    )
    st.markdown("**Golden Queries 覆盖面**")
    golden = [
        "70岁老人有高血压，推荐什么保险？",
        "北京5000元以下有哪些养老院？",
        "上面第二个适合糖尿病老人吗？",
        "糖尿病有哪些并发症？",
        "蓝医保适合高血压老人吗？",
        "这份条款70岁能不能买？",
    ]
    st.dataframe([{"问题": q, "覆盖能力": "GraphRAG / 规则过滤 / 多轮 / 资料问答"} for q in golden], use_container_width=True, hide_index=True)
    st.caption("完整评测可在终端运行：python scripts/eval_demo.py")


def request_chat_reply(prompt: str) -> Dict[str, Any]:
    prompt = prompt.strip()
    if not prompt:
        return {
            "role": "assistant",
            "content": "请输入有效问题。",
            "context": "",
            "sources": [],
            "graph": {},
            "recommendations": {},
            "trace": [],
        }
    history_payload = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ][-6:]

    try:
        response = requests.post(CHAT_URL, json={"query": prompt, "history": history_payload}, timeout=(3, 25))
        if response.status_code == 200:
            data = response.json()
            return {
                "role": "assistant",
                "content": data.get("answer", "抱歉，未能生成回答。"),
                "context": data.get("context", ""),
                "sources": data.get("sources", []),
                "graph": data.get("graph", {}),
                "recommendations": data.get("recommendations", {}),
                "trace": data.get("trace", []),
                "reasoning_paths": data.get("reasoning_paths", []),
            }
        return {
            "role": "assistant",
            "content": f"服务暂时不可用：{response.status_code} {response.text}",
            "context": "",
            "sources": [],
            "graph": {},
            "recommendations": {},
            "trace": [],
        }
    except Exception as exc:
        return {
            "role": "assistant",
            "content": f"发生连接错误：{exc}",
            "context": "",
            "sources": [],
            "graph": {},
            "recommendations": {},
            "trace": [],
        }


def iter_sse_chat(prompt: str):
    history_payload = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ][-6:]
    response = requests.post(
        STREAM_URL,
        json={"query": prompt, "history": history_payload},
        timeout=(3, 45),
        stream=True,
    )
    response.raise_for_status()
    current_event = "message"
    data_lines: List[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        line = raw_line or ""
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif line == "" and data_lines:
            payload = json.loads("\n".join(data_lines))
            yield current_event, payload
            current_event = "message"
            data_lines = []


def render_assistant_details(msg: Dict[str, Any], expanded_graph: bool = False, include_trace: bool = True) -> None:
    render_recommendations(msg.get("recommendations", {}))
    with st.expander("知识图谱证据图", expanded=expanded_graph):
        render_graph(msg.get("graph", {}))
        render_reasoning_paths(msg.get("reasoning_paths") or msg.get("graph", {}).get("reasoning_paths", []))
        for path in (msg.get("graph", {}).get("paths") or [])[:5]:
            st.caption(path)
    if include_trace:
        cols = st.columns(2)
        with cols[0]:
            with st.expander("证据来源", expanded=False):
                render_sources(msg.get("sources", []))
        with cols[1]:
            with st.expander("Agent 推理过程", expanded=False):
                render_trace(msg.get("trace", []))
    else:
        with st.expander("证据来源", expanded=False):
            render_sources(msg.get("sources", []))


def process_chat_turn(prompt: str) -> None:
    prompt = prompt.strip()
    if not prompt:
        return
    user_msg = {"role": "user", "content": prompt}
    assistant_msg = request_chat_reply(prompt)
    st.session_state.messages.extend([user_msg, assistant_msg])


def render_current_turn(prompt: str) -> None:
    prompt = prompt.strip()
    if not prompt:
        return

    user_msg = {"role": "user", "content": prompt}
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer_box = st.empty()
        trace_holder = st.empty()
        details_holder = st.empty()
        answer_text = ""
        trace: List[Dict[str, Any]] = []
        assistant_msg = {
            "role": "assistant",
            "content": "",
            "context": "",
            "sources": [],
            "graph": {},
            "recommendations": {},
            "trace": [],
            "reasoning_paths": [],
        }
        try:
            with st.status("Agent 推理中：意图解析、HybridRAG 检索、规则过滤与答案生成...", expanded=False) as status:
                for event, payload in iter_sse_chat(prompt):
                    if event == "trace_step":
                        trace.append(payload)
                        with trace_holder.expander("实时推理链路", expanded=False):
                            render_trace(trace)
                    elif event == "token":
                        answer_text += payload.get("text", "")
                        answer_box.markdown(answer_text + "▌")
                    elif event == "retrieval":
                        assistant_msg.update({
                            "sources": payload.get("sources", []),
                            "graph": payload.get("graph", {}),
                            "recommendations": payload.get("recommendations", {}),
                            "reasoning_paths": payload.get("reasoning_paths", []),
                        })
                    elif event == "final":
                        assistant_msg.update({
                            "content": payload.get("answer", answer_text),
                            "context": payload.get("context", ""),
                            "sources": payload.get("sources", assistant_msg.get("sources", [])),
                            "graph": payload.get("graph", assistant_msg.get("graph", {})),
                            "recommendations": payload.get("recommendations", assistant_msg.get("recommendations", {})),
                            "trace": payload.get("trace", trace),
                            "reasoning_paths": payload.get("reasoning_paths", assistant_msg.get("reasoning_paths", [])),
                        })
                    elif event == "error":
                        raise RuntimeError(payload.get("message", "流式接口异常"))
                status.update(label="Agent 推理完成，正在渲染回答与证据链。", state="complete", expanded=False)
        except Exception as exc:
            st.warning(f"流式接口暂不可用，已回退同步接口：{exc}")
            assistant_msg = request_chat_reply(prompt)

        if not assistant_msg.get("content"):
            assistant_msg["content"] = answer_text or "抱歉，暂时没有生成有效回答。"
            assistant_msg["trace"] = trace
        answer_box.markdown(assistant_msg["content"])
        render_assistant_details(
            assistant_msg,
            expanded_graph=bool(assistant_msg.get("graph", {}).get("nodes")),
        )

    st.session_state.messages.extend([user_msg, assistant_msg])


def render_live_reasoning(stage_box, active: str = "") -> None:
    stages = [
        ("QueryRewriteAgent", "问题重写与多轮指代消解"),
        ("IntentAgent", "抽取年龄、疾病、城市、预算与问答意图"),
        ("RetrieverAgent", "执行图谱召回、语义召回与候选重排"),
        ("ComplianceAgent", "检查年龄、险种、预算等硬规则"),
        ("AnswerAgent", "组织最终回答与证据展示结构"),
    ]
    rows = []
    for name, desc in stages:
        mark = "●" if name == active else "○"
        color = "#2563eb" if name == active else "#94a3b8"
        rows.append(
            f'<div class="live-step"><span style="color:{color};font-weight:800;">{mark}</span> '
            f'<b>{html.escape(name)}</b><span class="small-muted"> · {html.escape(desc)}</span></div>'
        )
    stage_box.markdown(
        '<div class="live-trace">' + "".join(rows) + "</div>",
        unsafe_allow_html=True,
    )


if "messages" not in st.session_state:
    st.session_state.messages = []
if "sidebar_prompt" not in st.session_state:
    st.session_state.sidebar_prompt = None


def choose_sidebar_prompt(prompt: str) -> None:
    st.session_state.sidebar_prompt = prompt


def clear_chat() -> None:
    st.session_state.messages = []
    st.session_state.sidebar_prompt = None


with st.sidebar:
    st.markdown("## 泰康医养 KGQA")
    st.caption("GraphRAG · Agent Trace · Evidence Graph")
    st.markdown("")
    stats = get_graph_stats()
    col1, col2 = st.columns(2)
    with col1:
        render_metric("疾病库", stats["Disease"])
        render_metric("保险产品", stats["Insurance"])
    with col2:
        render_metric("药品库", stats["Drug"])
        render_metric("养老机构", stats["NursingHome"])
    render_metric("图谱关系", stats["Relations"])
    st.divider()
    temperature = st.slider("严谨度", 0.0, 1.0, 0.3, help="演示版后端当前固定低温生成，该滑块保留为交互偏好。")
    st.markdown(
        """
<div class="feature-box">
  <div class="feature-title">系统能力</div>
  <div class="feature-copy">图谱证据链、Agent 推理过程、保险合规过滤、养老机构预算筛选、条款资料问答。</div>
</div>
<div class="feature-box">
  <div class="feature-title">答辩看点</div>
  <div class="feature-copy">每个回答都能展开底层证据图和推理链路，突出系统不是普通聊天页面。</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown("#### 演示场景")
    st.markdown('<div class="scenario-button">', unsafe_allow_html=True)
    st.button(
        "70岁老人有高血压，推荐什么保险？",
        use_container_width=True,
        on_click=choose_sidebar_prompt,
        args=("70岁老人有高血压，推荐什么保险？",),
    )
    st.button(
        "北京5000元以下有哪些养老院？",
        use_container_width=True,
        on_click=choose_sidebar_prompt,
        args=("北京5000元以下有哪些养老院？",),
    )
    st.button(
        "上面第二个适合糖尿病老人吗？",
        use_container_width=True,
        on_click=choose_sidebar_prompt,
        args=("上面第二个适合糖尿病老人吗？",),
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.button("清空当前对话", use_container_width=True, on_click=clear_chat)

st.markdown(
    """
<div class="hero">
  <div class="hero-title">泰康保险医养智能助手</div>
  <div class="hero-subtitle">基于 Neo4j 知识图谱、GraphRAG、Agent 推理链与多源资料问答的跨域智能系统</div>
</div>
""",
    unsafe_allow_html=True,
)

prompt_from_sidebar = st.session_state.sidebar_prompt
if prompt_from_sidebar:
    st.session_state.sidebar_prompt = None
    chat_prompt_to_submit = prompt_from_sidebar
else:
    chat_prompt_to_submit = None

if typed_prompt := st.chat_input("请描述您的情况，例如：70岁老人有高血压，推荐什么保险？"):
    chat_prompt_to_submit = typed_prompt

tab_chat, tab_upload, tab_graph, tab_metrics = st.tabs(["智能问答", "资料解析", "图谱探索", "系统评测"])

with tab_chat:
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                render_assistant_details(msg, expanded_graph=False)

    if chat_prompt_to_submit:
        render_current_turn(chat_prompt_to_submit)

    if not st.session_state.messages:
        st.info("从下方输入问题，或在左侧选择一个演示场景开始。")

with tab_upload:
    upload_document_panel()

with tab_graph:
    st.markdown("### 图谱子图探索")
    seed = st.text_input("输入实体或问题关键词", value="高血压")
    depth = st.slider("探索深度", 1, 2, 1)
    if st.button("加载子图", use_container_width=True):
        st.session_state.explore_graph = cached_subgraph(seed, depth)
    if st.session_state.get("explore_graph"):
        graph = st.session_state.explore_graph
        render_graph(graph, height=360)
        st.json({"nodes": len(graph.get("nodes", [])), "edges": len(graph.get("edges", [])), "paths": graph.get("paths", [])[:8]})

with tab_metrics:
    metrics_panel()
