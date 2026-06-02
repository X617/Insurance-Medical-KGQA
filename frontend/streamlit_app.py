import base64
from datetime import date, datetime, timedelta
import hashlib
import html
import json
import os
from pathlib import Path
import uuid
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
USER_STORE_PATH = Path("data/demo_users.json")
PAYMENT_QR_PATH = Path("fig/IMG_8724.JPG")

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
[data-testid="stAppViewContainer"] .main .block-container {{ padding-bottom: 8rem; }}
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
.confidence-card {{
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-left: 5px solid {PRIMARY};
    border-radius: 8px;
    padding: .85rem 1rem;
    margin: .7rem 0;
}}
.confidence-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .55rem;
    margin-top: .65rem;
}}
.confidence-pill {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: .55rem .65rem;
}}
.confidence-bar {{
    height: 7px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
    margin-top: .35rem;
}}
.confidence-fill {{
    height: 7px;
    background: linear-gradient(90deg, #0f766e, #2563eb);
}}
.algo-chip {{
    display: inline-block;
    background: #eef2ff;
    color: #3730a3;
    border: 1px solid #c7d2fe;
    border-radius: 999px;
    padding: .18rem .55rem;
    margin: .18rem .25rem .18rem 0;
    font-size: .82rem;
}}
.counter-card {{
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 8px;
    padding: .7rem .85rem;
    margin-bottom: .55rem;
}}
.chat-rail {{
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: .7rem;
    min-height: calc(100vh - 2rem);
}}
.rail-title {{ font-weight: 800; color: #111827; font-size: 1.05rem; margin-bottom: .3rem; }}
.rail-caption {{ color: #64748b; font-size: .78rem; margin-bottom: .55rem; }}
.user-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: .7rem .75rem;
    margin: .7rem 0;
}}
.user-avatar {{
    display: inline-flex;
    width: 28px;
    height: 28px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #b45309;
    color: white;
    font-size: .78rem;
    font-weight: 800;
    margin-right: .45rem;
}}
.current-plan {{
    border: 1px solid #dbeafe;
    background: #eff6ff;
    border-radius: 8px;
    padding: .7rem .8rem;
    margin: .65rem 0;
}}
.plan-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .75rem;
}}
.plan-card {{
    background: #fff;
    border: 1px solid #dbe3ef;
    border-radius: 8px;
    padding: 1rem;
    min-height: 220px;
}}
.plan-name {{ font-weight: 850; color: #111827; font-size: 1.08rem; }}
.plan-price {{ color: #2563eb; font-weight: 850; font-size: 1.35rem; margin: .3rem 0 .45rem; }}
.payment-box {{
    background: #fff;
    border: 1px solid #fed7aa;
    border-left: 5px solid #f59e0b;
    border-radius: 8px;
    padding: 1rem;
    margin-top: .8rem;
}}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(1) input[aria-label="聊天输入"]):has(> div:nth-child(2) button),
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(1) input[aria-label="资料输入"]):has(> div:nth-child(2) button) {{
    position: fixed;
    left: var(--chat-input-left, 28rem);
    right: 2.2rem;
    bottom: .85rem;
    z-index: 999;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: .55rem .65rem;
    box-shadow: 0 16px 36px rgba(15, 23, 42, .14);
}}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(1) input[aria-label="聊天输入"]):has(> div:nth-child(2) button) input,
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(1) input[aria-label="资料输入"]):has(> div:nth-child(2) button) input {{
    background: #f3f6fb;
    border: 0 !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(1) input[aria-label="聊天输入"]):has(> div:nth-child(2) button) button,
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(1) input[aria-label="资料输入"]):has(> div:nth-child(2) button) button {{
    min-height: 2.45rem;
}}
[data-testid="stSidebar"] > div:first-child {{
    max-height: 100vh;
    overflow-y: auto;
}}
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
def cached_subgraph(seed: str, depth: int, limit: int) -> Dict[str, Any]:
    return api_get("/graph/subgraph", query=seed, depth=depth, limit=limit, timeout=10.0)


@st.cache_data(ttl=120, show_spinner=False)
def cached_graph_analysis(seed: str, depth: int, limit: int) -> Dict[str, Any]:
    return api_get("/graph/analysis", query=seed, depth=depth, limit=limit, timeout=10.0)


PLAN_CATALOG = {
    "Free": {
        "price": "免费",
        "highlight": "基础图谱问答与交互体验",
        "features": ["基础 GraphRAG 问答", "少量资料解析", "基础可信问答功能"],
    },
    "Go": {
        "price": "¥5/月",
        "highlight": "更长上下文与快速图谱探索",
        "features": ["更长会话历史", "图谱探索增强", "资料问答优先队列"],
    },
    "Plus": {
        "price": "¥28/月",
        "highlight": "DeepSeek V4 Pro 与算法增强",
        "features": ["HyDE / DRIFT 检索", "条款抽取入图", "评测报告导出"],
    },
    "Ultra": {
        "price": "¥288/月",
        "highlight": "高阶医养顾问与企业能力",
        "features": ["批量资料解析", "专属图谱空间", "高并发服务性能"],
    },
}


def today_text() -> str:
    return date.today().isoformat()


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def load_user_store() -> Dict[str, Any]:
    if not USER_STORE_PATH.exists():
        return {"users": {}}
    try:
        return json.loads(USER_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"users": {}}


def save_user_store(store: Dict[str, Any]) -> None:
    USER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def make_chat_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def compact_title(text: str) -> str:
    text = " ".join(str(text or "").replace("\n", " ").split())
    text = text.strip(" ，。！？,.!?;；:：")
    if not text:
        return "新对话"
    return text[:18] + ("..." if len(text) > 18 else "")


def clean_title(text: str, fallback: str = "新对话") -> str:
    title = " ".join(str(text or "").replace("\n", " ").split())
    title = title.strip(" \t\r\n\"'“”‘’《》[]【】()（）。，、！？,.!?;；:：")
    if not title:
        return fallback
    for prefix in ("标题：", "标题:", "会话标题：", "会话标题:"):
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    return title[:18] + ("..." if len(title) > 18 else "")


def summarize_chat_title(user_text: str, assistant_text: str = "") -> str:
    fallback = compact_title(user_text)
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key == "sk-your-key":
        return fallback
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    title_model = os.getenv("DEEPSEEK_TITLE_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"
    prompt = (
        "请为下面这轮保险医养问答生成一个中文会话标题。"
        "要求：6到14个汉字，精准概括用户意图，不要标点，不要解释。\n\n"
        f"用户问题：{user_text[:500]}\n"
        f"系统回答：{assistant_text[:700]}"
    )
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": title_model,
                "messages": [
                    {"role": "system", "content": "你是一个会话标题生成器，只输出短标题。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 32,
                "stream": False,
            },
            timeout=(4, 10),
        )
        response.raise_for_status()
        data = response.json()
        title = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return clean_title(title, fallback)
    except Exception:
        return fallback


def empty_chat(chat_id: str) -> Dict[str, Any]:
    return {
        "id": chat_id,
        "title": "新对话",
        "messages": [],
        "created_at": now_text(),
        "updated_at": now_text(),
    }


def default_user(username: str) -> Dict[str, Any]:
    qa_id = make_chat_id("qa")
    doc_id = make_chat_id("doc")
    return {
        "username": username,
        "membership": {"tier": "Free", "expires_at": "-", "renewal": "未订阅"},
        "chat_spaces": {
            "qa": {"active_id": qa_id, "sessions": {qa_id: empty_chat(qa_id)}},
            "doc": {"active_id": doc_id, "sessions": {doc_id: empty_chat(doc_id)}},
        },
    }


def first_user_content(chat: Dict[str, Any]) -> str:
    for msg in chat.get("messages", []) or []:
        if msg.get("role") == "user":
            return " ".join(str(msg.get("content", "")).split())
    return ""


def normalize_chat_space(space_key: str, space: Dict[str, Any]) -> bool:
    changed = False
    sessions = space.setdefault("sessions", {})
    if not sessions:
        chat_id = make_chat_id(space_key)
        sessions[chat_id] = empty_chat(chat_id)
        space["active_id"] = chat_id
        return True

    active_id = space.get("active_id")
    seen: Dict[str, str] = {}
    for chat_id, chat in list(sessions.items()):
        if not isinstance(chat, dict):
            sessions[chat_id] = empty_chat(chat_id)
            changed = True
            continue
        if chat.get("id") != chat_id:
            chat["id"] = chat_id
            changed = True
        if not chat.get("created_at"):
            chat["created_at"] = now_text()
            changed = True
        if not chat.get("updated_at"):
            chat["updated_at"] = chat.get("created_at") or now_text()
            changed = True

        first_user = first_user_content(chat)
        dedupe_key = first_user or f"__empty__:{chat.get('title', '新对话')}"
        if dedupe_key in seen:
            kept_id = seen[dedupe_key]
            kept = sessions.get(kept_id, {})
            current_is_active = chat_id == active_id
            kept_is_active = kept_id == active_id
            current_newer = str(chat.get("updated_at", "")) > str(kept.get("updated_at", ""))
            if current_is_active or (current_newer and not kept_is_active):
                sessions.pop(kept_id, None)
                seen[dedupe_key] = chat_id
            else:
                sessions.pop(chat_id, None)
            changed = True
        else:
            seen[dedupe_key] = chat_id

    if space.get("active_id") not in sessions:
        latest_id = max(
            sessions,
            key=lambda cid: str(sessions[cid].get("updated_at") or sessions[cid].get("created_at") or ""),
        )
        space["active_id"] = latest_id
        changed = True
    return changed


def normalize_user_chats(user: Dict[str, Any]) -> bool:
    changed = False
    spaces = user.setdefault("chat_spaces", {})
    for space_key in ("qa", "doc"):
        if space_key not in spaces:
            chat_id = make_chat_id(space_key)
            spaces[space_key] = {"active_id": chat_id, "sessions": {chat_id: empty_chat(chat_id)}}
            changed = True
        changed = normalize_chat_space(space_key, spaces[space_key]) or changed
    return changed


def ensure_local_session() -> None:
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "auth_error" not in st.session_state:
        st.session_state.auth_error = ""
    if "chat_manager_open" not in st.session_state:
        st.session_state.chat_manager_open = False
    if "chat_manager_scope" not in st.session_state:
        st.session_state.chat_manager_scope = "qa"
    if "pending_payment" not in st.session_state:
        st.session_state.pending_payment = None
    if "legacy_messages_migrated" not in st.session_state:
        st.session_state.legacy_messages_migrated = False
    if "local_guest" not in st.session_state:
        st.session_state.local_guest = default_user("访客")
    if normalize_user_chats(st.session_state.local_guest):
        st.session_state.local_guest = st.session_state.local_guest
    if (
        not st.session_state.legacy_messages_migrated
        and "messages" in st.session_state
        and st.session_state.messages
    ):
        guest_space = st.session_state.local_guest["chat_spaces"]["qa"]
        guest_chat = guest_space["sessions"][guest_space["active_id"]]
        if not guest_chat["messages"]:
            guest_chat["messages"] = st.session_state.messages
            first_user = next((m.get("content", "") for m in st.session_state.messages if m.get("role") == "user"), "")
            guest_chat["title"] = compact_title(first_user)
            guest_chat["updated_at"] = now_text()
        st.session_state.legacy_messages_migrated = True


def current_user_record() -> Dict[str, Any]:
    ensure_local_session()
    username = st.session_state.auth_user
    if not username:
        return st.session_state.local_guest
    store = load_user_store()
    user = store.get("users", {}).get(username)
    if not user:
        user = default_user(username)
        store.setdefault("users", {})[username] = user
        save_user_store(store)
    if normalize_user_chats(user):
        store.setdefault("users", {})[username] = user
        save_user_store(store)
    return user


def save_current_user_record(user: Dict[str, Any]) -> None:
    normalize_user_chats(user)
    if st.session_state.get("auth_user"):
        store = load_user_store()
        store.setdefault("users", {})[st.session_state.auth_user] = user
        save_user_store(store)
    else:
        st.session_state.local_guest = user


def active_chat(space_key: str = "qa") -> Dict[str, Any]:
    user = current_user_record()
    spaces = user.setdefault("chat_spaces", {})
    if space_key not in spaces:
        chat_id = make_chat_id(space_key)
        spaces[space_key] = {"active_id": chat_id, "sessions": {chat_id: empty_chat(chat_id)}}
        save_current_user_record(user)
    space = spaces[space_key]
    if space.get("active_id") not in space.get("sessions", {}):
        chat_id = make_chat_id(space_key)
        space["active_id"] = chat_id
        space.setdefault("sessions", {})[chat_id] = empty_chat(chat_id)
        save_current_user_record(user)
    return space["sessions"][space["active_id"]]


def active_messages(space_key: str = "qa") -> List[Dict[str, Any]]:
    return active_chat(space_key).setdefault("messages", [])


def active_chat_from_user(user: Dict[str, Any], space_key: str = "qa") -> Dict[str, Any]:
    spaces = user.setdefault("chat_spaces", {})
    if space_key not in spaces:
        chat_id = make_chat_id(space_key)
        spaces[space_key] = {"active_id": chat_id, "sessions": {chat_id: empty_chat(chat_id)}}
    space = spaces[space_key]
    sessions = space.setdefault("sessions", {})
    if space.get("active_id") not in sessions:
        chat_id = make_chat_id(space_key)
        sessions[chat_id] = empty_chat(chat_id)
        space["active_id"] = chat_id
    return sessions[space["active_id"]]


def sync_legacy_messages(space_key: str = "qa") -> None:
    if space_key == "qa":
        st.session_state.messages = active_messages("qa")


def start_new_chat(space_key: str = "qa") -> None:
    user = current_user_record()
    chat_id = make_chat_id(space_key)
    space = user["chat_spaces"].setdefault(space_key, {"active_id": chat_id, "sessions": {}})
    space["sessions"][chat_id] = empty_chat(chat_id)
    space["active_id"] = chat_id
    save_current_user_record(user)
    st.session_state.sidebar_prompt = None
    st.session_state.pop("doc_pending_question", None)
    st.session_state.doc_request_inflight = False
    sync_legacy_messages(space_key)


def select_chat(space_key: str, chat_id: str) -> None:
    user = current_user_record()
    space = user["chat_spaces"].get(space_key)
    if space and chat_id in space.get("sessions", {}):
        space["active_id"] = chat_id
        save_current_user_record(user)
        st.session_state.sidebar_prompt = None
        st.session_state.pop("doc_pending_question", None)
        st.session_state.doc_request_inflight = False
        sync_legacy_messages(space_key)


def append_chat_pair(space_key: str, user_msg: Dict[str, Any], assistant_msg: Dict[str, Any]) -> None:
    user = current_user_record()
    chat = active_chat_from_user(user, space_key)
    was_empty = not chat.get("messages")
    chat.setdefault("messages", []).extend([user_msg, assistant_msg])
    if was_empty or chat.get("title") == "新对话":
        chat["title"] = summarize_chat_title(user_msg.get("content", ""), assistant_msg.get("content", ""))
    chat["updated_at"] = now_text()
    save_current_user_record(user)
    sync_legacy_messages(space_key)


def clear_active_chat(space_key: str = "qa") -> None:
    user = current_user_record()
    chat = active_chat_from_user(user, space_key)
    chat["messages"] = []
    chat["title"] = "新对话"
    chat["updated_at"] = now_text()
    save_current_user_record(user)
    sync_legacy_messages(space_key)


def login_user(username: str, password: str) -> bool:
    username = username.strip()
    store = load_user_store()
    user = store.get("users", {}).get(username)
    if not user:
        st.session_state.auth_error = "账号不存在，请先注册。"
        return False
    if hash_password(password, user.get("salt", "")) != user.get("password_hash"):
        st.session_state.auth_error = "密码不正确。"
        return False
    st.session_state.auth_user = username
    st.session_state.auth_error = ""
    sync_legacy_messages()
    return True


def register_user(username: str, password: str, password_confirm: str) -> bool:
    username = username.strip()
    if len(username) < 3:
        st.session_state.auth_error = "账号至少需要 3 个字符。"
        return False
    if len(password) < 6:
        st.session_state.auth_error = "密码至少需要 6 位。"
        return False
    if password != password_confirm:
        st.session_state.auth_error = "两次输入的密码不一致。"
        return False
    store = load_user_store()
    if username in store.get("users", {}):
        st.session_state.auth_error = "账号已存在，请直接登录。"
        return False
    salt = uuid.uuid4().hex
    user = default_user(username)
    user["salt"] = salt
    user["password_hash"] = hash_password(password, salt)
    store.setdefault("users", {})[username] = user
    save_user_store(store)
    st.session_state.auth_user = username
    st.session_state.auth_error = ""
    sync_legacy_messages()
    return True


def logout_user() -> None:
    st.session_state.auth_user = None
    st.session_state.auth_error = ""
    sync_legacy_messages()


def set_membership(plan: str) -> None:
    user = current_user_record()
    if plan == "Free":
        user["membership"] = {"tier": "Free", "expires_at": "-", "renewal": "未订阅"}
    else:
        user["membership"] = {
            "tier": plan,
            "expires_at": (date.today() + timedelta(days=30)).isoformat(),
            "renewal": "微信支付月付",
        }
    save_current_user_record(user)
    st.session_state.pending_payment = None


ensure_local_session()
sync_legacy_messages()


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


def render_graph(graph: Dict[str, Any], height: int = 420, max_nodes: int = 72, max_edges: int = 140) -> None:
    nodes = (graph.get("nodes") or [])[:max_nodes]
    node_ids = {node["id"] for node in nodes}
    edges = [
        edge for edge in (graph.get("edges") or [])
        if edge.get("source") in node_ids and edge.get("target") in node_ids
    ][:max_edges]
    if not nodes:
        st.info("本轮没有可视化子图。可以换一个包含疾病、保险或养老院实体的问题。")
        return

    color_map = {label: label_color(label) for label in sorted({n.get("label", "Entity") for n in nodes})}
    safe_nodes = [
        {
            "id": str(node.get("id")),
            "label": str(node.get("label", "Entity")),
            "name": str(node.get("name") or node.get("label") or "Entity"),
            "degree": int(node.get("degree") or 0),
            "seed": bool(node.get("seed")),
            "size": int(node.get("size") or 16),
        }
        for node in nodes
    ]
    safe_edges = [
        {
            "id": str(edge.get("id") or idx),
            "source": str(edge.get("source")),
            "target": str(edge.get("target")),
            "type": str(edge.get("type", "")),
        }
        for idx, edge in enumerate(edges)
    ]
    component_id = f"kg_{uuid.uuid4().hex}"
    payload = json.dumps(
        {"nodes": safe_nodes, "edges": safe_edges, "colors": color_map},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    graph_html = """
<div id="__ID__" class="kg-wrap">
  <div class="kg-topbar">
    <div class="kg-title">交互式知识图谱</div>
    <div class="kg-meta">拖动节点整理布局 · 滚轮缩放 · 拖动画布平移 · 双击节点聚焦</div>
    <button class="kg-reset" type="button">重置视图</button>
  </div>
  <div class="kg-legend"></div>
  <svg class="kg-svg" width="100%" height="__HEIGHT__" role="img"></svg>
  <div class="kg-tip"></div>
</div>
<style>
  #__ID__.kg-wrap {
    background: #fff;
    border: 1px solid #dbe3ef;
    border-radius: 8px;
    padding: 12px;
    font-family: Inter, "Microsoft YaHei", Arial, sans-serif;
  }
  #__ID__ .kg-topbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  #__ID__ .kg-title { font-weight: 780; color: #172033; }
  #__ID__ .kg-meta { flex: 1; color: #64748b; font-size: 12px; }
  #__ID__ .kg-reset {
    border: 1px solid #dbe3ef;
    background: #f8fafc;
    color: #334155;
    border-radius: 6px;
    padding: 5px 10px;
    cursor: pointer;
  }
  #__ID__ .kg-legend { color: #475569; font-size: 12px; margin-bottom: 8px; }
  #__ID__ .kg-legend span { margin-right: 14px; white-space: nowrap; }
  #__ID__ .kg-svg {
    border-radius: 8px;
    background:
      radial-gradient(circle at 50% 50%, rgba(37,99,235,.08), transparent 32%),
      linear-gradient(180deg, #fbfdff 0%, #f8fafc 100%);
    cursor: grab;
  }
  #__ID__ .kg-svg:active { cursor: grabbing; }
  #__ID__ .edge { stroke: #94a3b8; stroke-opacity: .62; }
  #__ID__ .edge-label { fill: #64748b; font-size: 10px; opacity: .78; pointer-events: none; }
  #__ID__ .node circle { stroke: #fff; stroke-width: 2.2px; filter: drop-shadow(0 4px 10px rgba(15,23,42,.16)); }
  #__ID__ .node.seed circle { stroke: #111827; stroke-width: 3px; }
  #__ID__ .node text { fill: #111827; font-size: 11px; text-anchor: middle; pointer-events: none; paint-order: stroke; stroke: #fff; stroke-width: 3px; }
  #__ID__ .kg-tip {
    margin-top: 8px;
    min-height: 22px;
    color: #475569;
    font-size: 12px;
  }
</style>
<script>
(function() {
  const root = document.getElementById("__ID__");
  const data = __DATA__;
  const svg = root.querySelector(".kg-svg");
  const legend = root.querySelector(".kg-legend");
  const tip = root.querySelector(".kg-tip");
  const width = svg.clientWidth || 960;
  const height = __HEIGHT__;
  const colors = data.colors || {};
  const nodes = data.nodes.map((d, i) => ({
    ...d,
    x: width / 2 + (Math.random() - 0.5) * width * 0.35,
    y: height / 2 + (Math.random() - 0.5) * height * 0.35,
    vx: 0,
    vy: 0,
    fixed: false,
    r: Math.max(11, Math.min(32, Number(d.size || 16)))
  }));
  const byId = new Map(nodes.map(n => [n.id, n]));
  const edges = data.edges
    .map(e => ({...e, sourceNode: byId.get(e.source), targetNode: byId.get(e.target)}))
    .filter(e => e.sourceNode && e.targetNode);

  legend.innerHTML = Object.keys(colors).map(label =>
    `<span><b style="color:${colors[label]}">●</b> ${label}</span>`
  ).join("");

  const ns = "http://www.w3.org/2000/svg";
  const viewport = document.createElementNS(ns, "g");
  svg.appendChild(viewport);
  const edgeLayer = document.createElementNS(ns, "g");
  const labelLayer = document.createElementNS(ns, "g");
  const nodeLayer = document.createElementNS(ns, "g");
  viewport.appendChild(edgeLayer);
  viewport.appendChild(labelLayer);
  viewport.appendChild(nodeLayer);

  const edgeEls = edges.map(e => {
    const line = document.createElementNS(ns, "line");
    line.setAttribute("class", "edge");
    line.setAttribute("stroke-width", Math.max(1.2, Math.min(2.8, 1.2 + (e.sourceNode.degree + e.targetNode.degree) / 18)));
    edgeLayer.appendChild(line);
    return line;
  });
  const edgeLabelEls = edges.slice(0, 36).map(e => {
    const text = document.createElementNS(ns, "text");
    text.setAttribute("class", "edge-label");
    text.textContent = e.type.length > 18 ? e.type.slice(0, 18) : e.type;
    labelLayer.appendChild(text);
    return text;
  });
  const nodeEls = nodes.map(n => {
    const g = document.createElementNS(ns, "g");
    g.setAttribute("class", `node ${n.seed ? "seed" : ""}`);
    const circle = document.createElementNS(ns, "circle");
    circle.setAttribute("r", n.r);
    circle.setAttribute("fill", colors[n.label] || "#64748b");
    const text = document.createElementNS(ns, "text");
    text.setAttribute("y", n.r + 15);
    text.textContent = n.name.length > 13 ? n.name.slice(0, 12) + "…" : n.name;
    g.appendChild(circle);
    g.appendChild(text);
    nodeLayer.appendChild(g);

    g.addEventListener("pointerdown", ev => {
      ev.stopPropagation();
      n.fixed = true;
      g.setPointerCapture(ev.pointerId);
      const start = toLocal(ev);
      const ox = n.x - start.x;
      const oy = n.y - start.y;
      function move(evt) {
        const p = toLocal(evt);
        n.x = p.x + ox;
        n.y = p.y + oy;
        draw();
      }
      function up(evt) {
        g.releasePointerCapture(evt.pointerId);
        g.removeEventListener("pointermove", move);
        g.removeEventListener("pointerup", up);
      }
      g.addEventListener("pointermove", move);
      g.addEventListener("pointerup", up);
    });
    g.addEventListener("mouseenter", () => {
      tip.textContent = `${n.label} · ${n.name} · degree=${n.degree}`;
    });
    g.addEventListener("dblclick", () => {
      transform.x = width / 2 - n.x * transform.k;
      transform.y = height / 2 - n.y * transform.k;
      draw();
    });
    return g;
  });

  let transform = {x: 0, y: 0, k: 1};
  function toLocal(ev) {
    const rect = svg.getBoundingClientRect();
    return {
      x: (ev.clientX - rect.left - transform.x) / transform.k,
      y: (ev.clientY - rect.top - transform.y) / transform.k
    };
  }
  svg.addEventListener("wheel", ev => {
    ev.preventDefault();
    const oldK = transform.k;
    const nextK = Math.max(0.35, Math.min(2.8, oldK * (ev.deltaY < 0 ? 1.1 : 0.9)));
    const rect = svg.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    transform.x = mx - (mx - transform.x) * nextK / oldK;
    transform.y = my - (my - transform.y) * nextK / oldK;
    transform.k = nextK;
    draw();
  }, {passive: false});
  svg.addEventListener("pointerdown", ev => {
    const sx = ev.clientX, sy = ev.clientY, ox = transform.x, oy = transform.y;
    svg.setPointerCapture(ev.pointerId);
    function move(evt) {
      transform.x = ox + evt.clientX - sx;
      transform.y = oy + evt.clientY - sy;
      draw();
    }
    function up(evt) {
      svg.releasePointerCapture(evt.pointerId);
      svg.removeEventListener("pointermove", move);
      svg.removeEventListener("pointerup", up);
    }
    svg.addEventListener("pointermove", move);
    svg.addEventListener("pointerup", up);
  });
  root.querySelector(".kg-reset").addEventListener("click", () => {
    transform = {x: 0, y: 0, k: 1};
    nodes.forEach(n => n.fixed = false);
    tick(120);
    draw();
  });

  const labelBuckets = {};
  nodes.forEach(n => {
    if (!labelBuckets[n.label]) labelBuckets[n.label] = Object.keys(labelBuckets).length;
  });
  function tick(iterations) {
    const area = Math.max(width * height, 1);
    const charge = Math.sqrt(area / Math.max(nodes.length, 1)) * 1.65;
    for (let t = 0; t < iterations; t++) {
      edges.forEach(e => {
        const a = e.sourceNode, b = e.targetNode;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const ideal = 92 + Math.min(90, (a.r + b.r) * 1.8);
        const force = (dist - ideal) * 0.012;
        const fx = dx / dist * force, fy = dy / dist * force;
        if (!a.fixed) { a.vx += fx; a.vy += fy; }
        if (!b.fixed) { b.vx -= fx; b.vy -= fy; }
      });
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const dist2 = dx * dx + dy * dy + 0.01;
          const dist = Math.sqrt(dist2);
          const minDist = a.r + b.r + 10;
          const repel = Math.min(2.2, charge * charge / dist2);
          const overlap = dist < minDist ? (minDist - dist) * 0.08 : 0;
          const fx = dx / dist * (repel + overlap);
          const fy = dy / dist * (repel + overlap);
          if (!a.fixed) { a.vx -= fx; a.vy -= fy; }
          if (!b.fixed) { b.vx += fx; b.vy += fy; }
        }
      }
      nodes.forEach(n => {
        const bucket = labelBuckets[n.label] || 0;
        const lanes = Math.max(1, Object.keys(labelBuckets).length);
        const targetX = n.seed ? width * 0.5 : width * (0.18 + 0.64 * (bucket + 0.5) / lanes);
        const targetY = n.seed ? height * 0.5 : height * 0.5;
        if (!n.fixed) {
          n.vx += (targetX - n.x) * (n.seed ? 0.035 : 0.006);
          n.vy += (targetY - n.y) * (n.seed ? 0.035 : 0.006);
          n.vx *= 0.82;
          n.vy *= 0.82;
          n.x = Math.max(40, Math.min(width - 40, n.x + n.vx));
          n.y = Math.max(40, Math.min(height - 52, n.y + n.vy));
        }
      });
    }
  }
  function draw() {
    viewport.setAttribute("transform", `translate(${transform.x},${transform.y}) scale(${transform.k})`);
    edges.forEach((e, i) => {
      edgeEls[i].setAttribute("x1", e.sourceNode.x);
      edgeEls[i].setAttribute("y1", e.sourceNode.y);
      edgeEls[i].setAttribute("x2", e.targetNode.x);
      edgeEls[i].setAttribute("y2", e.targetNode.y);
      if (edgeLabelEls[i]) {
        edgeLabelEls[i].setAttribute("x", (e.sourceNode.x + e.targetNode.x) / 2);
        edgeLabelEls[i].setAttribute("y", (e.sourceNode.y + e.targetNode.y) / 2 - 4);
      }
    });
    nodes.forEach((n, i) => nodeEls[i].setAttribute("transform", `translate(${n.x},${n.y})`));
  }
  tick(220);
  draw();
  tip.textContent = `当前子图：${nodes.length} 个节点，${edges.length} 条关系。`;
})();
</script>
"""
    graph_html = (
        graph_html
        .replace("__ID__", component_id)
        .replace("__HEIGHT__", str(height))
        .replace("__DATA__", payload)
    )
    components.html(graph_html, height=height + 92, scrolling=False)


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


def render_confidence(confidence: Dict[str, Any]) -> None:
    if not confidence:
        return
    overall = float(confidence.get("overall", 0) or 0)
    level = confidence.get("level", "-")
    items = [
        ("图谱依据", confidence.get("graph_grounding", 0)),
        ("语义匹配", confidence.get("semantic_match", 0)),
        ("规则合规", confidence.get("rule_compliance", 0)),
        ("答案稳定", confidence.get("answer_stability", 0)),
    ]
    pills = []
    for label, value in items:
        pct = max(0, min(100, float(value or 0) * 100))
        pills.append(
            f"""
<div class="confidence-pill">
  <div class="small-muted">{html.escape(label)}</div>
  <b>{pct:.0f}%</b>
  <div class="confidence-bar"><div class="confidence-fill" style="width:{pct:.0f}%"></div></div>
</div>
"""
        )
    st.markdown(
        f"""
<div class="confidence-card">
  <div><b>回答可信度：{overall:.1f}/100</b> <span class="tag">等级：{html.escape(str(level))}</span></div>
  <div class="small-muted">基于图谱命中、HybridRAG 证据、规则合规与模型稳定性综合估计。</div>
  <div class="confidence-grid">{''.join(pills)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_algorithm_signals(msg: Dict[str, Any]) -> None:
    chips = []
    if msg.get("retrieval_mode"):
        chips.append(f"检索模式：{msg.get('retrieval_mode')}")
    if msg.get("hyde_query"):
        chips.append("HyDE 查询扩展")
    if msg.get("drift_queries"):
        chips.append(f"DRIFT 二次追问 × {len(msg.get('drift_queries', []))}")
    if msg.get("counterfactual_checks"):
        chips.append(f"反事实校验 × {len(msg.get('counterfactual_checks', []))}")
    if chips:
        st.markdown("".join(f'<span class="algo-chip">{html.escape(chip)}</span>' for chip in chips), unsafe_allow_html=True)
    if msg.get("hyde_query") or msg.get("drift_queries"):
        with st.expander("HyDE / DRIFT 检索增强", expanded=False):
            if msg.get("hyde_query"):
                st.markdown("**HyDE 假设性专业检索扩展**")
                st.info(msg.get("hyde_query"))
            if msg.get("drift_queries"):
                st.markdown("**DRIFT 局部深挖子问题**")
                for query in msg.get("drift_queries", []):
                    st.markdown(f"- {query}")


def render_counterfactual(checks: List[Dict[str, Any]]) -> None:
    if not checks:
        return
    with st.expander("反事实合规校验", expanded=False):
        for item in checks:
            status = "通过" if item.get("passed") else "需谨慎"
            st.markdown(
                f"""
<div class="counter-card">
  <b>{html.escape(str(item.get("name", "反事实校验")))}</b>
  <span class="tag">{html.escape(status)}</span>
  <div>{html.escape(str(item.get("question", "")))}</div>
  <div class="small-muted">{html.escape(str(item.get("result", "")))}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            if item.get("evidence"):
                st.json(item.get("evidence"), expanded=False)


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


def render_login_box() -> None:
    if st.session_state.get("auth_user"):
        return
    with st.expander("登录 / 注册", expanded=True):
        mode = st.radio("账号入口", ["登录", "注册"], horizontal=True, label_visibility="collapsed")
        username = st.text_input("账号", placeholder="请输入账号/手机号", key=f"auth_user_{mode}")
        password = st.text_input("密码", type="password", key=f"auth_pwd_{mode}")
        if mode == "注册":
            password_confirm = st.text_input("再次输入密码", type="password", key="auth_pwd_confirm")
            if st.button("注册并登录", use_container_width=True):
                register_user(username, password, password_confirm)
        else:
            if st.button("登录", use_container_width=True):
                login_user(username, password)
        if st.session_state.get("auth_error"):
            st.error(st.session_state.auth_error)
        st.caption("演示版使用本地账号系统；Google 登录需要 OAuth 回调域名，正式部署时可接入。")


def render_user_card() -> None:
    user = current_user_record()
    membership = user.get("membership", {})
    username = st.session_state.get("auth_user") or user.get("username", "访客")
    initials = (username[:2] or "KG").upper()
    st.markdown(
        f"""
<div class="user-card">
  <span class="user-avatar">{html.escape(initials)}</span>
  <b>{html.escape(username)}</b>
  <div class="small-muted">当前会员：{html.escape(str(membership.get("tier", "Free")))} · 到期：{html.escape(str(membership.get("expires_at", "-")))}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.session_state.get("auth_user"):
        if st.button("退出登录", use_container_width=True):
            logout_user()
            st.rerun()
    else:
        render_login_box()


def render_chat_manager() -> None:
    if not st.session_state.chat_manager_open:
        if st.button("☰", help="展开 Chat 管理", use_container_width=True):
            st.session_state.chat_manager_open = True
            st.rerun()
        if st.button("＋", help="新建当前空间对话", use_container_width=True):
            start_new_chat(st.session_state.chat_manager_scope)
            st.rerun()
        if st.button("💎", help="会员中心", use_container_width=True):
            st.session_state.show_membership_tab = True
            st.rerun()
        return

    st.markdown('<div class="rail-title">Chat 管理</div>', unsafe_allow_html=True)
    col_title, col_close = st.columns([3, 1])
    with col_title:
        st.caption("独立管理问答与资料解析会话")
    with col_close:
        if st.button("收起", key="collapse_chat_rail", use_container_width=True):
            st.session_state.chat_manager_open = False
            st.rerun()

    scope_label = st.radio(
        "会话空间",
        ["智能问答", "资料解析"],
        horizontal=True,
        label_visibility="collapsed",
        key="chat_manager_scope_label",
    )
    st.session_state.chat_manager_scope = "qa" if scope_label == "智能问答" else "doc"
    scope = st.session_state.chat_manager_scope

    if st.button("新建 Chat", use_container_width=True, key=f"new_chat_{scope}"):
        start_new_chat(scope)
        st.rerun()
    search = st.text_input("Search Chat", placeholder="按标题搜索", key=f"chat_search_{scope}")

    user = current_user_record()
    space = user["chat_spaces"].setdefault(scope, {"active_id": "", "sessions": {}})
    sessions = list(space.get("sessions", {}).values())
    sessions = sorted(sessions, key=lambda item: item.get("updated_at", ""), reverse=True)
    if search.strip():
        keyword = search.strip().lower()
        sessions = [item for item in sessions if keyword in item.get("title", "").lower()]

    st.markdown("**Recents**")
    if not sessions:
        st.caption("暂无匹配会话")
    for item in sessions[:18]:
        title = item.get("title") or "新对话"
        active = item.get("id") == space.get("active_id")
        label = f"● {title}" if active else title
        if st.button(label, key=f"select_{scope}_{item.get('id')}", use_container_width=True):
            select_chat(scope, item["id"])
            st.rerun()

    st.divider()
    render_user_card()
    membership = current_user_record().get("membership", {})
    st.markdown(
        f"""
<div class="current-plan">
  <b>{html.escape(str(membership.get("tier", "Free")))}</b>
  <div class="small-muted">{html.escape(str(membership.get("renewal", "未订阅")))} · 有效期 {html.escape(str(membership.get("expires_at", "-")))}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button("查看会员方案", use_container_width=True):
        st.session_state.show_membership_tab = True


def membership_panel() -> None:
    st.markdown("### 会员订阅")
    user = current_user_record()
    membership = user.get("membership", {})
    st.markdown(
        f"""
<div class="current-plan">
  <b>当前账号：</b>{html.escape(str(user.get("username", "访客")))}
  <br/><b>当前会员：</b>{html.escape(str(membership.get("tier", "Free")))}
  <br/><span class="small-muted">有效期：{html.escape(str(membership.get("expires_at", "-")))} · {html.escape(str(membership.get("renewal", "未订阅")))}</span>
</div>
""",
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    for col, (plan, meta) in zip(cols, PLAN_CATALOG.items()):
        with col:
            features = "".join(f"<li>{html.escape(feature)}</li>" for feature in meta["features"])
            st.markdown(
                f"""
<div class="plan-card">
  <div class="plan-name">{html.escape(plan)}</div>
  <div class="plan-price">{html.escape(meta["price"])}</div>
  <div class="small-muted">{html.escape(meta["highlight"])}</div>
  <ul>{features}</ul>
</div>
""",
                unsafe_allow_html=True,
            )
            if plan == membership.get("tier"):
                st.button("当前方案", disabled=True, use_container_width=True, key=f"plan_current_{plan}")
            elif plan == "Free":
                if st.button("切换 Free", use_container_width=True, key="plan_free"):
                    set_membership("Free")
            else:
                if st.button(f"订阅 {plan}", type="primary", use_container_width=True, key=f"plan_{plan}"):
                    st.session_state.pending_payment = plan

    pending = st.session_state.get("pending_payment")
    if pending:
        st.markdown(
            f"""
<div class="payment-box">
  <b>微信支付收银台（演示沙箱）</b>
  <div class="small-muted">方案：{html.escape(pending)} · 金额：{html.escape(PLAN_CATALOG[pending]["price"])}</div>
  <div class="small-muted">正式系统可接入微信/支付宝 Native Pay；当前演示展示收款码并支持模拟支付成功。</div>
</div>
""",
            unsafe_allow_html=True,
        )
        col_qr, col_actions = st.columns([1, 2])
        with col_qr:
            if PAYMENT_QR_PATH.exists():
                st.image(str(PAYMENT_QR_PATH), caption="微信收款码", use_column_width=True)
            else:
                st.warning("未找到 fig/IMG_8724.JPG，请确认收款码图片存在。")
        with col_actions:
            st.markdown("[跳转到微信支付](https://pay.weixin.qq.com/)")
            # st.caption("浏览器环境可能不会直接拉起微信客户端，答辩时展示收款码即可形成闭环。")
            if st.button("模拟支付成功并开通会员", type="primary", use_container_width=True):
                set_membership(pending)
                st.success(f"{pending} 已开通，有效期 30 天。")
            if st.button("取消支付", use_container_width=True):
                st.session_state.pending_payment = None


def document_question_just_answered(question: str) -> bool:
    messages = active_messages("doc")
    return (
        len(messages) >= 2
        and messages[-2].get("role") == "user"
        and messages[-2].get("content") == question
        and messages[-1].get("role") == "assistant"
    )


def answer_document_question(question: str) -> None:
    document_id = st.session_state.get("document_id")
    question = (question or "").strip()
    if not document_id or not question:
        return
    if st.session_state.get("doc_request_inflight"):
        return
    if document_question_just_answered(question):
        return

    st.session_state.doc_request_inflight = True
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("正在结合资料生成回答..."):
                resp = requests.post(
                    f"{API_ROOT}/documents/{document_id}/ask",
                    json={"query": question},
                    timeout=60,
                )
            if resp.status_code == 200:
                answer = resp.json().get("answer", "资料问答完成，但未返回明确答案。")
                st.markdown(answer)
                append_chat_pair(
                    "doc",
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                )
            else:
                error_text = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                st.error(error_text)
        except Exception as exc:
            st.error(f"资料问答失败：{exc}")
        finally:
            st.session_state.doc_request_inflight = False


def submit_document_question(question: str) -> None:
    answer_document_question(question)


def handle_pending_document_question() -> None:
    question = st.session_state.pop("doc_pending_question", None)
    if question:
        answer_document_question(question)


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

        st.markdown("#### 资料会话")
        for msg in active_messages("doc"):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        handle_pending_document_question()

        with st.form("doc_question_form", clear_on_submit=True):
            doc_input_col, doc_send_col = st.columns([10, 1])
            with doc_input_col:
                doc_question = st.text_input(
                    "资料输入",
                    placeholder="围绕已上传资料追问，例如：这份条款 70 岁能不能买？",
                    key="doc_text_input",
                    label_visibility="collapsed",
                    disabled=st.session_state.get("doc_request_inflight", False),
                )
            with doc_send_col:
                doc_submitted = st.form_submit_button(
                    "➤",
                    use_container_width=True,
                    disabled=st.session_state.get("doc_request_inflight", False),
                )
        if doc_submitted:
            submit_document_question(doc_question)


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
    cols2 = st.columns(4)
    cards2 = [
        ("平均可信度", f"{metrics.get('avg_confidence', 0)}"),
        ("HyDE 次数", str(metrics.get("hyde_hits", 0))),
        ("DRIFT 次数", str(metrics.get("drift_hits", 0))),
        ("反事实通过率", f"{metrics.get('counterfactual_pass_rate', 0) * 100:.1f}%"),
    ]
    for col, (label, value) in zip(cols2, cards2):
        with col:
            render_metric(label, value)
    st.markdown("**消融实验对比**")
    if st.button("运行固定问题消融评测", use_container_width=True):
        with st.spinner("正在运行消融评测，可能需要几十秒..."):
            try:
                resp = requests.post(f"{API_ROOT}/eval/ablation", timeout=(5, 180))
                if resp.status_code == 200:
                    st.session_state.ablation_report = resp.json()
                    st.success("消融评测完成。")
                else:
                    st.error(resp.text)
            except Exception as exc:
                st.error(f"评测失败：{exc}")
    report = st.session_state.get("ablation_report") or {}
    if report.get("rows"):
        st.dataframe(report["rows"], use_container_width=True, hide_index=True)
        st.caption("说明：轻量演示版以完整链路结果为基准估计各检索模式贡献，并展示算法消融趋势。")
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
        for m in active_messages("qa")
    ][-6:]

    try:
        response = requests.post(CHAT_URL, json={"query": prompt, "history": history_payload}, timeout=(5, 150))
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
                "confidence": data.get("confidence", {}),
                "hyde_query": data.get("hyde_query"),
                "drift_queries": data.get("drift_queries", []),
                "counterfactual_checks": data.get("counterfactual_checks", []),
                "retrieval_mode": data.get("retrieval_mode"),
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
        for m in active_messages("qa")
    ][-6:]
    response = requests.post(
        STREAM_URL,
        json={"query": prompt, "history": history_payload},
        timeout=(5, 150),
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
    render_algorithm_signals(msg)
    render_confidence(msg.get("confidence", {}))
    render_counterfactual(msg.get("counterfactual_checks", []))
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
    append_chat_pair("qa", user_msg, assistant_msg)


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
            "confidence": {},
            "hyde_query": None,
            "drift_queries": [],
            "counterfactual_checks": [],
            "retrieval_mode": None,
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
                            "confidence": payload.get("confidence", {}),
                            "hyde_query": payload.get("hyde_query"),
                            "drift_queries": payload.get("drift_queries", []),
                            "counterfactual_checks": payload.get("counterfactual_checks", []),
                            "retrieval_mode": payload.get("retrieval_mode"),
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
                            "confidence": payload.get("confidence", assistant_msg.get("confidence", {})),
                            "hyde_query": payload.get("hyde_query", assistant_msg.get("hyde_query")),
                            "drift_queries": payload.get("drift_queries", assistant_msg.get("drift_queries", [])),
                            "counterfactual_checks": payload.get("counterfactual_checks", assistant_msg.get("counterfactual_checks", [])),
                            "retrieval_mode": payload.get("retrieval_mode", assistant_msg.get("retrieval_mode")),
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

    append_chat_pair("qa", user_msg, assistant_msg)


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


def algorithm_explain_panel() -> None:
    st.markdown("### 算法解释")
    st.markdown(
        """
本系统的第三阶段链路定位为 **GraphRAG + HybridRAG + HyDE/DRIFT + 合规规则 + 反事实校验**。
这里展示的是可公开解释的执行轨迹，不展示模型隐藏思维链。
"""
    )
    flow = [
        ("Intent", "抽取年龄、疾病、城市、预算、险种等结构化字段。"),
        ("HyDE", "生成假设性专业检索扩展，弥补短问题语义不足。"),
        ("Graph / Vector Recall", "Neo4j 精确图谱召回 + 本地语义/关键词召回。"),
        ("DRIFT", "基于初始证据生成局部追问，二次深挖相关证据。"),
        ("Rule Filter", "年龄、险种、预算、城市等硬规则过滤候选。"),
        ("Counterfactual", "检查年龄或疾病变化后推荐是否仍成立。"),
        ("Answer", "基于证据和结构化候选生成最终回答。"),
    ]
    for name, desc in flow:
        st.markdown(
            f"""
<div class="trace-step">
  <span class="trace-agent">{html.escape(name)}</span>
  <div class="small-muted">{html.escape(desc)}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    # st.markdown("**设计思路**")
    # st.info(
    #     "先用固定问题触发回答，再依次展开：结构化推荐、知识图谱证据图、证据来源、Agent 推理过程、可信度与反事实校验。"
    #     "最后切到系统评测页展示消融实验，说明 Hybrid + HyDE + DRIFT 相比关键词或纯图谱召回有更高证据覆盖。"
    # )


if "messages" not in st.session_state:
    st.session_state.messages = active_messages("qa")
if "sidebar_prompt" not in st.session_state:
    st.session_state.sidebar_prompt = None


def choose_sidebar_prompt(prompt: str) -> None:
    st.session_state.sidebar_prompt = prompt


def clear_chat() -> None:
    clear_active_chat("qa")
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
    # temperature = st.slider("严谨度", 0.0, 1.0, 0.3, help="演示版后端当前固定低温生成，该滑块保留为交互偏好。")
    temperature = st.slider("严谨度", 0.0, 1.0, 0.3)
    st.markdown(
        """
<div class="feature-box">
  <div class="feature-title">系统能力</div>
  <div class="feature-copy">图谱证据链、Agent 推理过程、保险合规过滤、养老机构预算筛选、条款资料问答。</div>
</div>
<div class="feature-box">
  <div class="feature-title">证据溯源</div>
  <div class="feature-copy">每个回答都能展开底层证据图和推理链路，提供有力证据支撑和模型可解释性。</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown("#### 示例")
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

rail_weight = 0.16 if st.session_state.chat_manager_open else 0.035
rail_col, app_col = st.columns([rail_weight, 1.0 - rail_weight], gap="small")
chat_input_left = "37.5rem" if st.session_state.chat_manager_open else "25.5rem"
st.markdown(
    f"<style>:root {{ --chat-input-left: {chat_input_left}; }}</style>",
    unsafe_allow_html=True,
)

with rail_col:
    render_chat_manager()

with app_col:
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

    tab_chat, tab_upload, tab_graph, tab_metrics, tab_algo, tab_member = st.tabs(
        ["智能问答", "资料解析", "图谱探索", "系统评测", "算法解释", "会员订阅"]
    )

    with tab_chat:
        with st.container():
            qa_messages = active_messages("qa")
            for idx, msg in enumerate(qa_messages):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant":
                        render_assistant_details(msg, expanded_graph=False)

            if chat_prompt_to_submit:
                render_current_turn(chat_prompt_to_submit)
                qa_messages = active_messages("qa")

            if not qa_messages:
                st.info("从下方输入问题，或在左侧选择一个演示场景开始。")

        input_col, send_col = st.columns([10, 1])
        with input_col:
            typed_prompt = st.text_input(
                "聊天输入",
                placeholder="请描述您的情况，例如：70岁老人有高血压，推荐什么保险？",
                label_visibility="collapsed",
                key="qa_text_input",
            )
        with send_col:
            send_clicked = st.button("➤", use_container_width=True, key="qa_send_button")
        if send_clicked and typed_prompt.strip():
            render_current_turn(typed_prompt)

    with tab_upload:
        upload_document_panel()

    with tab_graph:
        st.markdown("### 图谱子图探索")
        st.caption("交互式子图工作台：支持更深层关系扩展、拖拽节点、滚轮缩放和证据路径查看。")
        col_query, col_depth, col_limit = st.columns([4, 1.4, 1.6])
        with col_query:
            seed = st.text_input("输入实体或问题关键词", value="高血压")
        with col_depth:
            depth = st.slider("探索深度", 1, 4, 2)
        with col_limit:
            limit = st.slider("路径上限", 20, 180, 90, step=10)
        if st.button("加载交互式子图", use_container_width=True):
            st.session_state.explore_graph = cached_subgraph(seed, depth, limit)
        if st.session_state.get("explore_graph"):
            graph = st.session_state.explore_graph
            meta = graph.get("meta", {})
            count_cols = st.columns(4)
            with count_cols[0]:
                render_metric("节点", str(meta.get("node_count", len(graph.get("nodes", [])))))
            with count_cols[1]:
                render_metric("关系", str(meta.get("edge_count", len(graph.get("edges", [])))))
            with count_cols[2]:
                render_metric("深度", str(meta.get("depth", depth)))
            with count_cols[3]:
                render_metric("种子实体", str(meta.get("start_count", "-")))
            render_graph(graph, height=520, max_nodes=95, max_edges=180)

            path_col, node_col = st.columns([1.1, 1])
            with path_col:
                st.markdown("**证据路径预览**")
                paths = graph.get("paths", [])[:12]
                if paths:
                    for path in paths:
                        st.markdown(f'<div class="source-line">{html.escape(str(path))}</div>', unsafe_allow_html=True)
                else:
                    st.info("暂无路径信息。")
            with node_col:
                st.markdown("**高连接节点**")
                top_nodes = sorted(
                    graph.get("nodes", []),
                    key=lambda item: item.get("degree", 0),
                    reverse=True,
                )[:12]
                st.dataframe(
                    [
                        {
                            "类型": item.get("label"),
                            "名称": item.get("name"),
                            "度数": item.get("degree", 0),
                            "种子": "是" if item.get("seed") else "",
                        }
                        for item in top_nodes
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            analysis = cached_graph_analysis(seed, depth, limit).get("analysis", {})
            if analysis:
                st.markdown("**局部图分析**")
                st.info(analysis.get("summary", ""))
                a_col, b_col = st.columns(2)
                with a_col:
                    st.markdown("核心实体排行")
                    st.dataframe(analysis.get("core_nodes", []), use_container_width=True, hide_index=True)
                with b_col:
                    st.markdown("社区摘要")
                    st.dataframe(analysis.get("communities", []), use_container_width=True, hide_index=True)
                with st.expander("k-core 近似分层与最短路径", expanded=False):
                    st.dataframe(analysis.get("k_core_layers", []), use_container_width=True, hide_index=True)
                    for path in analysis.get("shortest_paths", []):
                        st.caption(path)

    with tab_metrics:
        metrics_panel()

    with tab_algo:
        algorithm_explain_panel()

    with tab_member:
        membership_panel()
