# ==================================================
# FILE: .\frontend\pages\tutor.py (CẬP NHẬT)
# ==================================================
import pandas as pd
import streamlit as st
import requests

st.set_page_config(page_title="Dashboard Giao vien", page_icon="📊", layout="wide")

st.title("Dashboard Giáo Viên")
st.write("Theo dõi tổng quan lớp học và cảnh báo sớm học sinh có nguy cơ.")

session_token = st.session_state.get("session_token", "")
if not session_token or st.session_state.auth_user.get("role") != "admin":
    st.warning("Bạn cần đăng nhập bằng tài khoản Giáo viên (admin) để xem trang này.")
    st.stop()

# Gọi API lấy thống kê lớp học
API_URL = "http://localhost:1891"

class_res = requests.post(f"{API_URL}/dashboard/class", json={"session_token": session_token}).json()
risk_res = requests.post(f"{API_URL}/dashboard/at-risk", json={"session_token": session_token}).json()

if class_res.get("success") == False:
    st.error("Lỗi lấy dữ liệu: " + class_res.get("error", ""))
    st.stop()

# Hiển thị số liệu tổng quan
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng học sinh", class_res.get("total_students", 0))
col2.metric("Số bài Quiz đã làm", class_res.get("total_quizzes", 0))
col3.metric("Điểm trung bình hệ thống", f"{class_res.get('avg_score', 0):.2f}")
col4.metric("Elo trung bình", class_res.get("avg_elo", 0))

st.divider()

# Xử lý dữ liệu học sinh nguy cơ
st.subheader("⚠️ Danh sách học sinh cần lưu ý (At Risk)")
risk_data = risk_res.get("at_risk_students", [])

if not risk_data:
    st.success("Tuyệt vời! Hiện tại không có học sinh nào bị tụt Elo hoặc có điểm số quá thấp.")
else:
    df = pd.DataFrame(risk_data)
    df = df.rename(columns={
        "user_id": "ID", 
        "email": "Email", 
        "avg_score": "Điểm TB", 
        "avg_elo": "Elo TB", 
        "elo_drop": "Độ tụt Elo lớn nhất"
    })
    
    def highlight_drop(val):
        color = '#ffebee' if val > 0 else ''
        return f'background-color: {color}'
        
    styled_df = df.style.map(highlight_drop, subset=["Độ tụt Elo lớn nhất"])
    st.dataframe(styled_df, width="stretch")

# Phân phối điểm (Dùng biểu đồ có sẵn của Streamlit)
dist = class_res.get("score_distribution", {})
if dist:
    st.subheader("Phân phối năng lực lớp học")
    dist_df = pd.DataFrame(list(dist.items()), columns=['Mức độ', 'Số lượng'])
    st.bar_chart(dist_df.set_index('Mức độ'))