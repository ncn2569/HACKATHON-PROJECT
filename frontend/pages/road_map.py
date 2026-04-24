import time

import streamlit as st


st.set_page_config(page_title="Lo trinh hoc", page_icon="🗺️", layout="wide")

st.title("Lo trinh hoc")
st.write("Nhap muc tieu de AI phan tich va de xuat ke hoach hoc tap.")

with st.form("roadmap_form"):
	goal = st.text_input("Muc tieu hoc tap", placeholder="Thi giua ky mon Vi tich phan")
	level = st.selectbox("Trinh do hien tai", ["Mat goc", "Co ban", "Kha"])
	submitted = st.form_submit_button("Phan tich & Len lo trinh")

if submitted:
	with st.spinner("AI dang suy nghi..."):
		time.sleep(2)

	# TODO: Gan API/Logic cua AI tao lo trinh thuc te vao day de chuan bi ghep noi code sau nay.
	st.success("Da tao lo trinh hoc tap de xuat.")
	st.markdown(f"**Muc tieu:** {goal if goal else 'Chua nhap'}")
	st.markdown(f"**Trinh do hien tai:** {level}")

	with st.expander("Buoc 1: On lai dao ham", expanded=True):
		st.markdown("- Nham lai quy tac dao ham co ban\n- Lam 10 bai tap nhanh")

	with st.expander("Buoc 2: Luyen phuong trinh va gioi han"):
		st.markdown("- Luyen cac dang bai thuong gap\n- Tu kiem tra sau moi chu de")

	with st.expander("Buoc 3: Thuc hanh de tong hop"):
		st.markdown("- Lam de mo phong 45 phut\n- Ghi lai loi sai de sua")

	with st.expander("Buoc 4: On tap co trong tam"):
		st.markdown("- Tap trung vao phan yeu\n- Chot cong thuc truoc ky thi")
