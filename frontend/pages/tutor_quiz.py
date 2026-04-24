from pathlib import Path
import sys

import pandas as pd
import requests
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

API_URL = "http://localhost:1891"

st.set_page_config(page_title="Quan ly Cau hoi Quiz", page_icon="📝", layout="wide")

session_token = st.session_state.get("session_token", "")
auth_user = st.session_state.get("auth_user") or {}

if not session_token or auth_user.get("role") != "admin":
    st.warning("Trang nay chi danh cho giang vien. Vui long dang nhap bang tai khoan admin.")
    st.stop()

try:
    me_res = requests.post(f"{API_URL}/auth/me", json={"session_token": session_token}, timeout=10).json()
except Exception as exc:
    st.error(f"Khong ket noi duoc backend auth: {exc}")
    st.stop()

if me_res.get("success") is False or (me_res.get("user") or {}).get("role") != "admin":
    st.error("Phien dang nhap khong hop le hoac khong co quyen admin.")
    st.stop()

st.title("Quan ly Ngan hang Cau hoi")
st.caption(f"Dang nhap: {auth_user.get('email', '')} (Giang vien)")


def _fetch_subjects() -> list[dict]:
    try:
        res = requests.post(f"{API_URL}/tutor/subjects", json={"session_token": session_token}, timeout=15)
        payload = res.json()
        if payload.get("success"):
            return payload.get("subjects", [])
        st.error(payload.get("error", "Khong lay duoc danh sach mon hoc"))
        return []
    except Exception as exc:
        st.error(f"Loi lay mon hoc: {exc}")
        return []


def _fetch_topics(subject_id: int) -> list[dict]:
    try:
        res = requests.post(
            f"{API_URL}/tutor/topics",
            json={"session_token": session_token, "subject_id": int(subject_id)},
            timeout=15,
        )
        payload = res.json()
        if payload.get("success"):
            return payload.get("topics", [])
        st.error(payload.get("error", "Khong lay duoc danh sach chu de"))
        return []
    except Exception as exc:
        st.error(f"Loi lay chu de: {exc}")
        return []


subjects = _fetch_subjects()
subject_map = {s["name"]: s["subject_id"] for s in subjects}
if not subjects:
    st.error("Khong tim thay mon hoc nao trong he thong. Vui long kiem tra database.")
    st.stop()

tab_add, tab_stats = st.tabs(["Them cau hoi", "Thong ke ngan hang"])

with tab_add:
    st.subheader("Them cau hoi moi vao ngan hang de")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        selected_subject_name = st.selectbox("Mon hoc", options=list(subject_map.keys()), key="quiz_subject")
        selected_subject_id = int(subject_map[selected_subject_name])

        topics = _fetch_topics(selected_subject_id)
        topic_map = {t["name"]: t["topic_id"] for t in topics}
        if not topics:
            st.warning(f"Mon '{selected_subject_name}' chua co chu de nao.")
            st.stop()

        selected_topic_name = st.selectbox("Chu de", options=list(topic_map.keys()), key="quiz_topic")
        selected_topic_id = int(topic_map[selected_topic_name])

        content = st.text_area(
            "Noi dung cau hoi",
            placeholder="Nhap noi dung cau hoi trac nghiem tai day...",
            height=120,
            key="quiz_content",
        )

    with col_right:
        difficulty_labels = {
            1: "Rat de (1)",
            2: "De (2)",
            3: "Trung binh (3)",
            4: "Kho (4)",
            5: "Rat kho (5)",
        }
        difficulty = st.select_slider(
            "Do kho",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: difficulty_labels[x],
            key="quiz_difficulty",
        )

        st.divider()
        st.info(
            f"Mon: {selected_subject_name}\n"
            f"Chu de: {selected_topic_name}\n"
            f"Do kho: {difficulty}/5"
        )

    st.markdown("---")
    st.markdown("Cac dap an (nhap dung 4 dap an)")

    ans_cols = st.columns(2)
    with ans_cols[0]:
        option_a = st.text_input("A.", placeholder="Dap an A", key="opt_a")
        option_b = st.text_input("B.", placeholder="Dap an B", key="opt_b")
    with ans_cols[1]:
        option_c = st.text_input("C.", placeholder="Dap an C", key="opt_c")
        option_d = st.text_input("D.", placeholder="Dap an D", key="opt_d")

    correct_labels = {"A": 0, "B": 1, "C": 2, "D": 3}
    correct_answer = st.radio("Dap an dung", options=["A", "B", "C", "D"], horizontal=True, key="correct_ans")
    correct_index = int(correct_labels[correct_answer])

    st.markdown("---")
    if st.button("Them cau hoi vao ngan hang", type="primary", use_container_width=True):
        if not content.strip():
            st.error("Vui long nhap noi dung cau hoi.")
        elif not all([option_a.strip(), option_b.strip(), option_c.strip(), option_d.strip()]):
            st.error("Vui long nhap day du 4 dap an.")
        else:
            with st.spinner("Dang them cau hoi..."):
                try:
                    res = requests.post(
                        f"{API_URL}/tutor/question/add",
                        json={
                            "session_token": session_token,
                            "content": content,
                            "options": [option_a, option_b, option_c, option_d],
                            "correct_answer_index": correct_index,
                            "topic_id": selected_topic_id,
                            "subject_id": selected_subject_id,
                            "difficulty": difficulty,
                        },
                        timeout=20,
                    )
                    result = res.json()
                except Exception as exc:
                    result = {"success": False, "error": f"Khong ket noi duoc backend tutor: {exc}"}

            if result.get("success"):
                st.success("Da them cau hoi thanh cong!")
                q = result.get("question", {})
                st.json(
                    {
                        "ID": q.get("id"),
                        "Topic": q.get("topic"),
                        "Elo": q.get("elo"),
                        "Content": q.get("content", "")[:100],
                    }
                )
            else:
                st.error(f"Loi: {result.get('error', 'Khong xac dinh')}")

with tab_stats:
    st.subheader("Thong ke Ngan hang Cau hoi")

    try:
        stats = requests.post(
            f"{API_URL}/tutor/question/stats",
            json={"session_token": session_token},
            timeout=15,
        ).json()
    except Exception as exc:
        st.error(f"Loi lay thong ke: {exc}")
        st.stop()

    if not stats.get("success"):
        st.error(f"Loi lay thong ke: {stats.get('error', '')}")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Tong cau hoi", stats.get("total_questions", 0))

        by_topic = stats.get("by_topic", [])
        col2.metric("So chu de", len(by_topic))

        by_diff = stats.get("by_difficulty", [])
        col3.metric("Muc do kho", f"{len(by_diff)} muc")

        st.divider()

        if by_topic:
            st.markdown("So cau hoi theo chu de:")
            df_topic = pd.DataFrame(by_topic)
            df_topic.columns = ["Chu de", "So luong"]
            st.bar_chart(df_topic.set_index("Chu de"))
            with st.expander("Xem bang chi tiet"):
                st.dataframe(df_topic, use_container_width=True)

        if by_diff:
            st.markdown("So cau hoi theo do kho:")
            diff_labels = {1: "Rat de", 2: "De", 3: "Trung binh", 4: "Kho", 5: "Rat kho"}
            df_diff = pd.DataFrame(by_diff)
            df_diff.columns = ["Do kho", "So luong"]
            df_diff["Do kho"] = df_diff["Do kho"].map(lambda x: diff_labels.get(x, str(x)))
            st.bar_chart(df_diff.set_index("Do kho"))
