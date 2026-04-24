from pathlib import Path
import sys

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
	sys.path.append(str(ROOT_DIR))

from backend.auth_service import get_session_user
from backend.roadmap_service import create_roadmap_for_user, get_subject_names


st.set_page_config(page_title="Lo trinh hoc", page_icon="🗺️", layout="wide")

st.title("Lo trinh hoc")
st.write("Nhap thong tin hoc tap de tao lo trinh ca nhan hoa.")

session_token = st.session_state.get("session_token", "")
auth_user = get_session_user(session_token) if session_token else None
if not auth_user:
	st.warning("Ban can dang nhap o trang chinh truoc khi tao lo trinh.")
	st.stop()

subject_options = get_subject_names()
if not subject_options:
	subject_options = ["Mathematics"]

with st.form("roadmap_form"):
	goal = st.text_input("Muc tieu hoc tap", placeholder="Thi giua ky mon Vi tich phan")
	level = st.selectbox("Trinh do hien tai", ["Mat goc", "Co ban", "Kha"])
	learning_style = st.selectbox("Phong cach hoc", ["Doc tai lieu", "Video", "Thuc hanh", "Hoi dap"])
	subjects = st.multiselect("Mon hoc", subject_options, default=[subject_options[0]])
	target_time = st.number_input("Thoi gian hoc moi ngay (phut)", min_value=10, max_value=180, value=30, step=5)
	submitted = st.form_submit_button("Phan tich & Len lo trinh")

if submitted:
	profile = {
		"goal": goal,
		"level": level,
		"learning_style": learning_style,
		"subjects": subjects,
		"target_time": int(target_time),
	}

	with st.spinner("AI dang tao lo trinh..."):
		result = create_roadmap_for_user(int(auth_user["user_id"]), profile)

	if not result.get("success"):
		st.error(result.get("error", "Khong the tao lo trinh"))
		st.stop()

	roadmap = result.get("roadmap", {})
	st.success("Da tao lo trinh hoc tap de xuat.")
	st.caption(f"Model: {result.get('model_used', 'unknown')}")

	st.markdown(f"**{roadmap.get('title', 'Lo trinh hoc tap')}**")
	st.write(roadmap.get("summary", ""))
	st.markdown(f"**Tong thoi gian:** {roadmap.get('total_weeks', '?')} tuan")

	steps = roadmap.get("steps", [])
	for step in steps:
		step_title = f"Buoc {step.get('step', '?')}: {step.get('title', 'N/A')}"
		with st.expander(step_title, expanded=step.get("step", 0) == 1):
			st.markdown(f"**Thoi gian:** {step.get('duration', 'N/A')}")
			st.write(step.get("description", ""))
			tasks = step.get("tasks", [])
			if tasks:
				st.markdown("**Nhiem vu:**")
				for task in tasks:
					st.markdown(f"- {task}")
			resources = step.get("resources", [])
			if resources:
				st.markdown("**Tai nguyen goi y:**")
				for item in resources:
					st.markdown(f"- {item}")

	tips = roadmap.get("tips", [])
	if tips:
		st.subheader("Meo hoc tap")
		for tip in tips:
			st.markdown(f"- {tip}")
