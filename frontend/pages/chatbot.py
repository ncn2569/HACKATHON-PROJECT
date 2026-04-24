from pathlib import Path
import random
import sys

import requests
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


API_URL = "http://localhost:1891"
# STYLE_OPTIONS = ["Tiêu chuẩn", "Gen Z", "Holmes", "Quân đội"]


st.set_page_config(page_title="Chatbot Socratic", page_icon="💬", layout="wide")
st.title("Chatbot Ho Tro Tu Duy")
st.caption("Du lieu RAG: 12.docx | Logic giu nguyen theo chatbot.txt (ask-back, memory, ep EXPLAIN khi be tac)")

session_token = st.session_state.get("session_token", "")
auth_user = st.session_state.get("auth_user")
if not session_token or not auth_user:
    st.warning("Ban can dang nhap o trang chinh truoc khi dung chatbot.")
    st.stop()

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

selected_style = st.text_input("Phong cach AI", value= "Professional")

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
            res = requests.post(
                f"{API_URL}/chat",
                json={
                    "question": prompt,
                    "session_id": st.session_state.chat_session_id,
                    "style": selected_style,
                    "session_token": session_token,
                },
                timeout=30,
            )
            response = res.json()
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
