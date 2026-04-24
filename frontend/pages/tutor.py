import pandas as pd
import streamlit as st


st.set_page_config(page_title="Dashboard Giao vien", page_icon="📊", layout="wide")

st.title("Dashboard giao vien")
st.write("Theo doi nhanh tinh hinh lop hoc va canh bao som hoc sinh co nguy co.")

# Mock data: this table can later be replaced by SVM inference output.
students_df = pd.DataFrame(
	[
		{"Tên học sinh": "Nguyen Van An", "Tiến độ (%)": 92, "Trạng thái": "Bình thường"},
		{"Tên học sinh": "Tran Minh Khoa", "Tiến độ (%)": 58, "Trạng thái": "Nguy cơ"},
		{"Tên học sinh": "Le Thu Ha", "Tiến độ (%)": 76, "Trạng thái": "Bình thường"},
		{"Tên học sinh": "Pham Gia Bao", "Tiến độ (%)": 49, "Trạng thái": "Nguy cơ"},
		{"Tên học sinh": "Do Ngoc Linh", "Tiến độ (%)": 84, "Trạng thái": "Bình thường"},
	]
)

total_students = len(students_df)
avg_score = students_df["Tiến độ (%)"].mean()
at_risk_count = (students_df["Trạng thái"] == "Nguy cơ").sum()

col1, col2, col3 = st.columns(3)
col1.metric("Tổng học sinh", total_students)
col2.metric("Điểm trung bình", f"{avg_score:.1f}")
col3.metric("Số học sinh cần lưu ý", at_risk_count)


def highlight_risk_status(value: str) -> str:
	if value == "Nguy cơ":
		return "background-color: #ffebee; color: #b71c1c; font-weight: 700;"
	return ""


styled_df = students_df.style.map(highlight_risk_status, subset=["Trạng thái"])

st.subheader("Danh sach hoc sinh")
st.dataframe(styled_df, width="stretch")

st.caption(
	"Trang thai 'Nguy cơ' dang duoc highlight. Day la vi tri de hien thi ket qua tu mo hinh SVM sau nay."
)
