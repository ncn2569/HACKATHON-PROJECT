from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
# ==================================================
# FILE: .\backend\be.py (CẬP NHẬT)
# ==================================================
# Thêm các import mới ở đầu file:
try:
    from .dashboard_service import get_class_dashboard, get_student_dashboard, get_student_habit, get_at_risk_students
except ImportError:
    from dashboard_service import get_class_dashboard, get_student_dashboard, get_student_habit, get_at_risk_students

try:
	from .chatbot_service import chat_with_memory
except ImportError:
	from chatbot_service import chat_with_memory

try:
	from .auth_service import get_session_user, login_user, logout_user
	from .roadmap_service import create_roadmap_for_user
except ImportError:
	from auth_service import get_session_user, login_user, logout_user
	from roadmap_service import create_roadmap_for_user

# Thêm models Pydantic mới (đặt dưới class RoadmapQuery):
class DashboardQuery(BaseModel):
    session_token: str

class StudentDashboardQuery(BaseModel):
    session_token: str
    target_user_id: int = None # Nếu không truyền, lấy chính user đang đăng nhập

app = FastAPI(title="LMS Backend API")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


class ChatQuery(BaseModel):
	question: str
	session_id: str = "default_student_1"
	style: str = "Holmes"


class LoginQuery(BaseModel):
	email: str
	password: str


class LogoutQuery(BaseModel):
	session_token: str


class RoadmapQuery(BaseModel):
	session_token: str
	goal: str
	level: str = "Co ban"
	learning_style: str = "Doc tai lieu"
	subjects: list[str] = []
	target_time: int = 30


@app.get("/health")
def health() -> dict:
	return {"ok": True}


@app.post("/chat")
def chat(query: ChatQuery) -> dict:
	try:
		return chat_with_memory(
			question=query.question,
			session_id=query.session_id,
			style=query.style,
		)
	except Exception as exc:
		return {"action": "ERROR", "value": "", "text": f"Server lỗi: {exc}"}


@app.post("/auth/login")
def auth_login(query: LoginQuery) -> dict:
	return login_user(email=query.email, password=query.password)


@app.post("/auth/logout")
def auth_logout(query: LogoutQuery) -> dict:
	return logout_user(query.session_token)


@app.post("/roadmap/create")
def roadmap_create(query: RoadmapQuery) -> dict:
	user = get_session_user(query.session_token)
	if not user:
		return {"success": False, "error": "Session khong hop le. Vui long dang nhap lai."}

	profile = {
		"goal": query.goal,
		"level": query.level,
		"learning_style": query.learning_style,
		"subjects": query.subjects,
		"target_time": query.target_time,
	}
	return create_roadmap_for_user(int(user["user_id"]), profile)



# Kéo xuống dưới cùng, thêm các route API này trước if __name__ == "__main__":

@app.post("/dashboard/class")
def api_class_dashboard(query: DashboardQuery) -> dict:
    user = get_session_user(query.session_token)
    if not user or user.get("role") != "admin":
        return {"success": False, "error": "Khong co quyen truy cap."}
    return get_class_dashboard()

@app.post("/dashboard/at-risk")
def api_at_risk(query: DashboardQuery) -> dict:
    user = get_session_user(query.session_token)
    if not user or user.get("role") != "admin":
        return {"success": False, "error": "Khong co quyen truy cap."}
    return get_at_risk_students()

@app.post("/dashboard/student")
def api_student_dashboard(query: StudentDashboardQuery) -> dict:
    user = get_session_user(query.session_token)
    if not user:
        return {"success": False, "error": "Phien dang nhap het han."}
    
    # Giáo viên có thể xem bất kỳ ai, học sinh chỉ xem được mình
    target_id = query.target_user_id if query.target_user_id else user["user_id"]
    if user.get("role") != "admin" and target_id != user["user_id"]:
        return {"success": False, "error": "Khong co quyen truy cap du lieu nguoi khac."}
        
    dashboard_data = get_student_dashboard(target_id)
    habit_data = get_student_habit(target_id)
    dashboard_data.update(habit_data)
    
    return {"success": True, "data": dashboard_data}

if __name__ == "__main__":
	uvicorn.run(app, host="0.0.0.0", port=1891)

