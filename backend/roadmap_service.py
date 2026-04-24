import json
import os

import google.generativeai as genai

try:
    from .data_pool import run_execute, run_query
except ImportError:
    from data_pool import run_execute, run_query


# Read available subject names from DB for roadmap profile input.
def get_subject_names() -> list[str]:
    rows = run_query("SELECT name FROM subjects ORDER BY subject_id")
    return [row["name"] for row in rows if row.get("name")]


# Save or update user study profile in PostgreSQL.
def save_study_profile(user_id: int, profile: dict) -> None:
    subjects = profile.get("subjects", [])
    subject_name = subjects[0] if subjects else None

    subject_id = None
    if subject_name:
        subject_rows = run_query(
            "SELECT subject_id FROM subjects WHERE LOWER(name) = LOWER(%s) LIMIT 1",
            (subject_name,),
        )
        if subject_rows:
            subject_id = subject_rows[0]["subject_id"]

    existing = run_query(
        "SELECT profile_id FROM user_study_profiles WHERE user_id = %s LIMIT 1",
        (user_id,),
    )

    if existing:
        run_execute(
            """
            UPDATE user_study_profiles
            SET subject_id = %s,
                goal = %s,
                level = %s,
                learning_style = %s
            WHERE profile_id = %s
            """,
            (
                subject_id,
                profile.get("goal", ""),
                profile.get("level", "Co ban"),
                profile.get("learning_style", "Doc tai lieu"),
                existing[0]["profile_id"],
            ),
        )
        return

    run_execute(
        """
        INSERT INTO user_study_profiles (user_id, subject_id, goal, target_time, level, learning_style)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            subject_id,
            profile.get("goal", ""),
            int(profile.get("target_time", 30)),
            profile.get("level", "Co ban"),
            profile.get("learning_style", "Doc tai lieu"),
        ),
    )


# Build roadmap prompt preserving logic from roadmap source file.
def _build_prompt(profile: dict) -> str:
    goal = profile.get("goal", "Hoc tot hon")
    learning_style = profile.get("learning_style", "Doc tai lieu")
    subjects = profile.get("subjects", [])
    level = profile.get("level", "Co ban")

    subjects_str = ", ".join(subjects) if subjects else "Toan hoc"

    return f"""Ban la mot chuyen gia giao duc AI. Hay tao lo trinh hoc tap ca nhan hoa cho hoc sinh voi thong tin sau:

- Muc tieu hoc tap: {goal}
- Phong cach hoc: {learning_style}
- Cac mon hoc: {subjects_str}
- Trinh do hien tai: {level}

Hay tra ve ket qua duoi dang JSON (KHONG co markdown code block, chi tra ve JSON thuan tuy) voi cau truc sau:
{{
  "title": "Tieu de lo trinh",
  "summary": "Tom tat ngan gon ve lo trinh",
  "total_weeks": <so tuan>,
  "steps": [
    {{
      "step": 1,
      "title": "Ten buoc",
      "duration": "Thoi gian (vd: 1 tuan)",
      "description": "Mo ta chi tiet",
      "tasks": ["Nhiem vu 1", "Nhiem vu 2"],
      "resources": ["Tai lieu/video goi y"],
      "subject": "Mon hoc lien quan"
    }}
  ],
  "tips": ["Meo hoc tap 1", "Meo hoc tap 2"]
}}

Hay tao lo trinh cu the, thuc te va phu hop voi phong cach hoc cua hoc sinh. Tra ve toi da 6 buoc.
Chi tra ve JSON, khong them bat ky text nao khac.
"""


# Generate roadmap using Gemini with fallback output if API config is missing.
def generate_roadmap(profile: dict) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model_name = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-1.5-flash")

    if not api_key:
        return {
            "success": True,
            "roadmap": {
                "title": "Lo trinh hoc tap co ban",
                "summary": "Chua cau hinh API key, dang dung lo trinh mau.",
                "total_weeks": 4,
                "steps": [
                    {
                        "step": 1,
                        "title": "On kien thuc nen",
                        "duration": "1 tuan",
                        "description": "Ra soat lai cac khai niem co ban.",
                        "tasks": ["Lam bai on", "Tong hop cong thuc"],
                        "resources": ["Slide mon hoc", "So tay ghi chu"],
                        "subject": ", ".join(profile.get("subjects", []) or ["Tong hop"]),
                    }
                ],
                "tips": ["Hoc deu moi ngay", "Tu kiem tra hang tuan"],
            },
            "model_used": "fallback",
        }

    prompt = _build_prompt(profile)
    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = (response.text or "").strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        roadmap = json.loads(text)
        return {"success": True, "roadmap": roadmap, "model_used": model_name}
    except Exception as exc:
        return {"success": False, "error": f"Khong the tao lo trinh: {exc}"}


# Save profile to DB then generate roadmap from profile context.
def create_roadmap_for_user(user_id: int, profile: dict) -> dict:
    save_study_profile(user_id, profile)
    return generate_roadmap(profile)
