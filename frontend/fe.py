import streamlit as st


st.set_page_config(page_title="LMS - Anti Brainrot", layout="wide")

st.title("LMS Platform")

# Sidebar: simple login
st.sidebar.header("Dang nhap")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

if "entered_lms" not in st.session_state:
	st.session_state.entered_lms = False

if "role" not in st.session_state:
	st.session_state.role = "Hoc sinh"

if username and password:
	st.sidebar.success(f"Xin chao, {username}!")
else:
	st.sidebar.info("Vui long nhap Username va Password.")

# Centered role-selection step before entering LMS content.
if not st.session_state.entered_lms:
	left, center, right = st.columns([1, 2, 1])
	with center:
		st.subheader("Buoc 1: Chon vai tro")
		selected_role = st.selectbox("Trang thai", ["Hoc sinh", "Giao vien"])

		if st.button("Vao he thong", use_container_width=True):
			if username and password:
				st.session_state.role = selected_role
				st.session_state.entered_lms = True
				st.rerun()
			else:
				st.warning("Vui long nhap Username va Password o sidebar truoc khi vao he thong.")

	st.stop()

st.subheader("Chao mung den voi nen tang LMS chong Brainrot")
st.write(
	"Day la trang chinh don gian cho he thong hoc tap. "
	"Nen tang giup nguoi hoc tap trung, giam xao nhang va xay dung thoi quen hoc hieu qua."
)

st.write(f"Ban dang o che do: **{st.session_state.role}**")
