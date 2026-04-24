import streamlit as st


st.set_page_config(page_title="Socratic AI", page_icon="💬", layout="wide")

st.title("Socratic AI - Chatbot ho tro tu duy")
st.write("Dat cau hoi hoc tap, AI se goi mo de ban tu suy luan va tim huong giai.")

if "messages" not in st.session_state:
	st.session_state.messages = [
		{
			"role": "assistant",
			"content": "Chao em! Hay gui mot cau hoi, minh se dong hanh theo phong cach Socratic.",
		}
	]

for message in st.session_state.messages:
	with st.chat_message(message["role"]):
		st.markdown(message["content"])

user_question = st.chat_input("Nhap cau hoi cua ban...")

if user_question:
	st.session_state.messages.append({"role": "user", "content": user_question})
	with st.chat_message("user"):
		st.markdown(user_question)

	ai_reply = (
		"De giai bai nay, em da thu ap dung dinh ly nao chua? "
		"Neu tach bai toan thanh 2 buoc nho hon, em se bat dau tu buoc nao?"
	)

	# TODO: Tich hop API Gemini/OpenAI tai day de mang ML de dang gan vao.

	st.session_state.messages.append({"role": "assistant", "content": ai_reply})
	with st.chat_message("assistant"):
		st.markdown(ai_reply)
