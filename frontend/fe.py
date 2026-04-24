import streamlit as st
from pathlib import Path
import sys
import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
	sys.path.append(str(ROOT_DIR))


API_URL = "http://localhost:1891"


st.set_page_config(page_title="LMS - Anti Brainrot", layout="wide")

st.title("LMS Platform")

if "session_token" not in st.session_state:
	st.session_state.session_token = ""
if "auth_user" not in st.session_state:
	st.session_state.auth_user = None


def clear_app_session() -> None:
	st.session_state.session_token = ""
	st.session_state.auth_user = None
	for key in [
		"chat_messages",
		"chat_session_id",
		"quiz_user",
		"quiz_set_ids",
		"quiz_answers",
		"quiz_report",
		"generated_count",
		"generation_errors",
		"entered_lms",
		"role",
	]:
		if key in st.session_state:
			del st.session_state[key]


# Session is managed by backend API process; keep local user from login response.

if not st.session_state.auth_user:
	st.sidebar.header("Dang nhap")
	email = st.sidebar.text_input("Email")
	password = st.sidebar.text_input("Mat khau", type="password")

	if st.sidebar.button("Dang nhap", use_container_width=True):
		try:
			res = requests.post(
				f"{API_URL}/auth/login",
				json={"email": email, "password": password},
				timeout=10,
			)
			result = res.json()
			if result.get("success"):
				st.session_state.session_token = result.get("session_token", "")
				st.session_state.auth_user = result.get("user")
				st.rerun()
			else:
				st.sidebar.error(result.get("message", "Dang nhap that bai"))
		except Exception as exc:
			st.sidebar.error(f"Khong ket noi duoc backend auth: {exc}")

	st.info("Vui long dang nhap de su dung LMS.")
	st.stop()

st.sidebar.success(f"Xin chao, {st.session_state.auth_user.get('email', 'user')}!")
st.sidebar.caption(f"Role: {st.session_state.auth_user.get('role', 'student')}")

if st.sidebar.button("Dang xuat", use_container_width=True):
	try:
		requests.post(
			f"{API_URL}/auth/logout",
			json={"session_token": st.session_state.session_token},
			timeout=10,
		)
	except Exception:
		pass
	clear_app_session()
	st.rerun()

st.subheader("Chao mung den voi nen tang LMS chong Brainrot")
st.write(
	"Day la trang chinh don gian cho he thong hoc tap. "
	"Nen tang giup nguoi hoc tap trung, giam xao nhang va xay dung thoi quen hoc hieu qua."
)

st.write(f"Ban dang dang nhap voi role: **{st.session_state.auth_user.get('role', 'student')}**")
