from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .data_pool import run_query
except ImportError:
    from data_pool import run_query

try:
    from .quiz import add_question_to_pool, add_questions_to_pool
except ImportError:
    from quiz import add_question_to_pool, add_questions_to_pool


ROOT_DIR = Path(__file__).resolve().parents[1]
RAG_DOCUMENTS_DIR = ROOT_DIR / "rag_documents"
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}


# Ensure rag_documents directory exists.
def _ensure_rag_dir() -> Path:
    RAG_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return RAG_DOCUMENTS_DIR


# Return all subjects from DB as list[dict].
def get_subjects() -> list[dict]:
    try:
        rows = run_query("SELECT subject_id, name FROM subjects ORDER BY name")
        return [{"subject_id": r["subject_id"], "name": r["name"]} for r in rows]
    except Exception:
        return []


# Return all topics, optionally filtered by subject_id.
def get_topics(subject_id: int | None = None) -> list[dict]:
    try:
        if subject_id is not None:
            rows = run_query(
                "SELECT topic_id, name, subject_id FROM topics WHERE subject_id = %s ORDER BY name",
                (subject_id,),
            )
        else:
            rows = run_query("SELECT topic_id, name, subject_id FROM topics ORDER BY name")
        return [{"topic_id": r["topic_id"], "name": r["name"], "subject_id": r["subject_id"]} for r in rows]
    except Exception:
        return []


# Add a single quiz question via quiz.py's add_question_to_pool.
def tutor_add_question(
    content: str,
    options: list[str],
    correct_answer_index: int,
    topic_id: int,
    subject_id: int,
    difficulty: int = 3,
) -> dict[str, Any]:
    if not content.strip():
        return {"success": False, "error": "Noi dung cau hoi khong duoc trong."}

    if len(options) != 4 or any(not opt.strip() for opt in options):
        return {"success": False, "error": "Can dung 4 dap an va khong duoc de trong."}

    if correct_answer_index not in (0, 1, 2, 3):
        return {"success": False, "error": "Chi so dap an dung phai tu 0-3."}

    if difficulty not in (1, 2, 3, 4, 5):
        return {"success": False, "error": "Do kho phai tu 1-5."}

    # Map difficulty -> elo for quiz.py compatibility.
    diff_to_elo = {1: 900, 2: 950, 3: 1000, 4: 1050, 5: 1100}
    elo_value = diff_to_elo.get(difficulty, 1000)

    question_data = {
        "content": content.strip(),
        "options": [opt.strip() for opt in options],
        "correct_answer_index": correct_answer_index,
        "topic_id": topic_id,
        "subject_id": subject_id,
        "elo": elo_value,
    }

    result = add_question_to_pool(question_data, added_by="tutor")
    if result is None:
        return {"success": False, "error": "Khong the them cau hoi. Kiem tra topic/subject co ton tai."}

    return {"success": True, "question": result}


# Add many quiz questions in one call.
def tutor_add_questions_batch(questions: list[dict]) -> dict[str, Any]:
    if not questions:
        return {"success": False, "error": "Danh sach cau hoi rong."}

    inserted = add_questions_to_pool(questions=questions, added_by="tutor")
    return {"success": True, "count": len(inserted), "questions": inserted}


# Return statistics about the question bank.
def get_question_stats() -> dict[str, Any]:
    try:
        total_row = run_query("SELECT COUNT(*) AS cnt FROM questions")
        total = total_row[0]["cnt"] if total_row else 0

        by_topic = run_query(
            """
            SELECT t.name AS topic_name, COUNT(*) AS cnt
            FROM questions q
            JOIN topics t ON q.topic_id = t.topic_id
            GROUP BY t.name
            ORDER BY cnt DESC
            """
        )

        by_difficulty = run_query(
            """
            SELECT difficulty, COUNT(*) AS cnt
            FROM questions
            GROUP BY difficulty
            ORDER BY difficulty
            """
        )

        return {
            "success": True,
            "total_questions": total,
            "by_topic": [{"topic": r["topic_name"], "count": r["cnt"]} for r in by_topic],
            "by_difficulty": [{"difficulty": r["difficulty"], "count": r["cnt"]} for r in by_difficulty],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# Save uploaded file bytes to rag_documents directory.
def save_rag_document(file_bytes: bytes, filename: str) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return {"success": False, "error": f"Dinh dang '{suffix}' khong duoc ho tro. Chi chap nhan: {supported}"}

    rag_dir = _ensure_rag_dir()
    safe_name = filename.replace(" ", "_")
    target_path = rag_dir / safe_name

    # If file already exists, add timestamp suffix.
    if target_path.exists():
        stem = target_path.stem
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{stem}_{ts}{suffix}"
        target_path = rag_dir / safe_name

    target_path.write_bytes(file_bytes)

    return {
        "success": True,
        "filename": safe_name,
        "size_bytes": len(file_bytes),
        "path": str(target_path),
    }


# List all documents in rag_documents directory.
def list_rag_documents() -> list[dict]:
    rag_dir = _ensure_rag_dir()
    docs = []
    for fp in sorted(rag_dir.iterdir()):
        if fp.is_file() and fp.suffix.lower() in ALLOWED_EXTENSIONS:
            stat = fp.stat()
            docs.append(
                {
                    "filename": fp.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    return docs


# Delete a single document from rag_documents.
def delete_rag_document(filename: str) -> dict[str, Any]:
    rag_dir = _ensure_rag_dir()
    target = rag_dir / filename
    if not target.exists():
        return {"success": False, "error": f"File '{filename}' khong ton tai."}

    # Safety: ensure we're not escaping the directory.
    if not str(target.resolve()).startswith(str(rag_dir.resolve())):
        return {"success": False, "error": "Duong dan khong hop le."}

    target.unlink()
    return {"success": True, "deleted": filename}


# Reload chatbot FAISS index to include new documents.
def reload_chatbot_index() -> dict[str, Any]:
    try:
        from .chatbot_service import init_chatbot_runtime
    except ImportError:
        try:
            from chatbot_service import init_chatbot_runtime
        except ImportError:
            return {"success": False, "error": "Khong the import chatbot_service."}

    try:
        init_chatbot_runtime(force_reload=True)
        return {"success": True, "message": "Da reload chatbot thanh cong."}
    except Exception as exc:
        return {"success": False, "error": f"Loi reload: {exc}"}
