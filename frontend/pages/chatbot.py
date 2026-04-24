from pathlib import Path
import random
import sys

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.chatbot_service import STYLE_MAP, chat_with_memory


st.set_page_config(page_title="Chatbot Socratic", page_icon="💬", layout="wide")
st.title("Chatbot Ho Tro Tu Duy")
st.caption("Du lieu RAG: 12.docx | Logic giu nguyen theo chatbot.txt (ask-back, memory, ep EXPLAIN khi be tac)")

if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = f"student_{random.randint(1000, 9999)}"

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "Chao ban! Minh se khong dua dap an ngay, minh se hoi goi mo de ban tu suy luan.",
            "action": "ASK_BACK",
        }
    ]

selected_style = st.selectbox("Phong cach AI", options=list(STYLE_MAP.keys()), index=2)

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("action"):
            st.caption(f"Action: {msg['action']}")

prompt = st.chat_input("Nhap cau hoi hoc tap...")
if prompt:
    st.session_state.chat_messages.append({"role": "user", "content": prompt, "action": ""})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            response = chat_with_memory(
                question=prompt,
                session_id=st.session_state.chat_session_id,
                style=selected_style,
            )
            action = response.get("action", "")
            text = response.get("text", "")
            st.write(text)
            st.caption(f"Action: {action}")
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": text, "action": action}
            )
        except Exception as exc:
            error_text = f"Khong the khoi tao chatbot: {exc}"
            st.error(error_text)
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": error_text, "action": "ERROR"}
            )
