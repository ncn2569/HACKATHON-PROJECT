# LMS Anti Brainrot

He thong LMS mini cho hackathon, tap trung vao:
- Dang nhap/phan quyen student-admin.
- Chatbot Socratic + RAG.
- Adaptive Quiz theo Elo.
- Dashboard giao vien/student.
- Tao lo trinh hoc tap ca nhan hoa.
- Quan ly ngan hang cau hoi cho giao vien.

## Team
- Bui Dinh Phuc
- Pham Hong Nhan
- Phan Tran Trung Nam
- Nguyen Canh Nguyen

## Tech Stack
- Frontend: Streamlit
- Backend API: FastAPI + Uvicorn
- Database: PostgreSQL
- AI: Google Gemini, LangChain, FAISS
- Python libs: pandas, psycopg2, python-dotenv, docx2txt, pypdf

## Project Structure
```
.
|-- backend/
|   |-- be.py                 # FastAPI entrypoint
|   |-- auth_service.py       # login/logout/session
|   |-- data_pool.py          # PostgreSQL query helpers
|   |-- chatbot_service.py    # RAG + Socratic chat logic
|   |-- roadmap_service.py    # roadmap generation + save profile
|   |-- dashboard_service.py  # dashboard queries
|   |-- quiz.py               # adaptive quiz + Elo + DB persist
|   |-- tutor_service.py      # teacher question bank operations
|   `-- quizz.py              # compatibility re-export
|
|-- frontend/
|   |-- fe.py
|   `-- pages/
|       |-- adaptive_quiz.py
|       |-- chatbot.py
|       |-- road_map.py
|       |-- tutor.py
|       `-- tutor_quiz.py
|
|-- database.txt              # schema + seed data tham khao
|-- requirements.txt
|-- meme/                     # meme images for quiz result
|-- meme.txt                  # score -> meme mapping
`-- README.md
```

## Main Features
1. Authentication
- Login/logout qua API backend.
- Session token duoc luu trong memory cua backend.
- Kiem tra role admin cho trang giao vien.

2. Adaptive Quiz
- Chon cau hoi theo topic va Elo.
- Cham diem ngay tren UI.
- Ghi DB cho quiz/answers/elo history.
- Hien meme cuoi bai theo so cau dung.

3. Chatbot Socratic
- RAG tu tai lieu (docx/pdf/txt).
- Co memory theo session chat.
- Luu lich su hoi dap vao bang chat_history.

4. Roadmap Generator
- Luu profile hoc tap vao DB.
- Goi Gemini de sinh roadmap JSON.
- Co fallback roadmap mau neu chua cau hinh API key.

5. Dashboard & Teacher Tools
- Dashboard lop hoc va canh bao hoc sinh at-risk.
- Trang teacher them cau hoi va xem thong ke ngan hang.

## Requirements
- Python 3.10+ (khuyen nghi 3.11)
- PostgreSQL da co schema theo database.txt

## Setup
1. Tao virtual environment
```bash
python -m venv venv
```

2. Kich hoat virtual environment (Windows)
```bash
venv\Scripts\activate
```

3. Cai dependencies
```bash
pip install -r requirements.txt
```

## Environment Variables
Tao file .env o root project:

```env
# PostgreSQL
DB_HOST=your_host
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password
DB_SSLMODE=require
DB_CONNECT_TIMEOUT=10

# Gemini
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GEMINI_MODEL=gemini-3.1-flash-lite-preview

Luu y:
- Neu khong co GOOGLE_API_KEY, roadmap van chay fallback.
- Chatbot can API key de chay RAG voi Gemini.

## Run Project
Mo 2 terminal rieng.

1. Run backend API
```bash
python backend/be.py
```
Backend chay mac dinh tai: http://localhost:1891

2. Run frontend Streamlit
```bash
streamlit run frontend/fe.py
```

## Seed Database
- Co the tham khao va execute file database.txt de tao schema + seed data.
- File seed da co tai khoan admin/student mau.

## Core API Endpoints
Auth:
- POST /auth/login
- POST /auth/logout
- POST /auth/me

Chatbot:
- POST /chat

Roadmap:
- GET /roadmap/subjects
- POST /roadmap/create

Dashboard:
- POST /dashboard/class
- POST /dashboard/at-risk
- POST /dashboard/student

Teacher quiz bank:
- POST /tutor/subjects
- POST /tutor/topics
- POST /tutor/question/add
- POST /tutor/question/stats

Health check:
- GET /health

## Current Notes
- Session store dang o memory backend (restart backend se mat session).
- Adaptive quiz hien su dung logic backend.quiz truc tiep trong Streamlit page.
- Cac tinh nang chinh da duoc dong bo theo flow frontend -> backend -> database.

## Quick Troubleshooting
1. Khong login duoc
- Kiem tra backend co dang chay o port 1891.
- Kiem tra users/password trong database.

2. Khong co quyen admin
- Dang nhap bang account role admin.
- Goi /auth/me de verify role/session.

3. Chatbot loi API key
- Kiem tra GOOGLE_API_KEY trong .env.

4. Loi ket noi DB
- Kiem tra DB_HOST, DB_USER, DB_PASSWORD, SSL mode.

## License
Internal hackathon project.