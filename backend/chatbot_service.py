from collections import deque
from pathlib import Path
import json
import os
import re

from dotenv import load_dotenv
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = ROOT_DIR / "12.docx"
MAX_HISTORY = 3

LOADER_MAP = {
    ".txt": lambda p: TextLoader(p, encoding="utf-8"),
    ".pdf": lambda p: PyPDFLoader(p),
    ".docx": lambda p: Docx2txtLoader(p),
}

STYLE_MAP = {
    "Tiêu chuẩn": "Giọng điệu chuẩn mực, rõ ràng, mang tính sư phạm, thân thiện và lịch sự.",
    "Gen Z": "Năng động, hài hước. Dùng từ lóng của Gen Z Việt Nam (như 'khum', 'bất ổn', 'flex', 'slay'). Hay dùng emoji và so sánh bài học với trà sữa, idol, game.",
    "Holmes": "Đóng vai thám tử Sherlock Holmes. Gọi học sinh là 'cộng sự'. Coi bài tập là một 'vụ án' và các dữ kiện là 'manh mối'. Giọng điệu bí ẩn, thông minh.",
    "Quân đội": "Đóng vai huấn luyện viên quân đội. Nghiêm khắc, dứt khoát, dùng câu mệnh lệnh. Khích lệ tinh thần thép, không chấp nhận sự lười biếng.",
}

session_store: dict[str, deque] = {}
_runtime: dict = {"ready": False}


# Load all supported files from a list of paths/files.
def load_all_documents(paths: list[Path]) -> list:
    all_docs = []
    for path in paths:
        if not path.exists():
            continue

        if path.is_file():
            candidate_files = [path]
        else:
            candidate_files = [file for file in path.rglob("*") if file.is_file()]

        for file_path in candidate_files:
            suffix = file_path.suffix.lower()
            if suffix not in LOADER_MAP:
                continue
            loader = LOADER_MAP[suffix](str(file_path))
            docs = loader.load()
            for doc in docs:
                doc.metadata["source_file"] = file_path.name
            all_docs.extend(docs)

    return all_docs


# Convert document chunks into one context block for prompt injection.
def format_docs(docs: list) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


# Build retriever + LLM pipeline once and keep in memory.
def init_chatbot_runtime(force_reload: bool = False) -> None:
    if _runtime.get("ready") and not force_reload:
        return

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY chưa được set trong biến môi trường")

    data_inputs = [DEFAULT_DATA_FILE]
    raw_documents = load_all_documents(data_inputs)
    if not raw_documents:
        raise ValueError("Không tìm thấy dữ liệu cho chatbot. Kiểm tra file 12.docx")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.split_documents(raw_documents)

    embedding = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
    )
    vector_db = FAISS.from_documents(docs, embedding)
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_GEMINI_MODEL"),
        temperature=0.3,
        google_api_key=api_key,
    )

    prompt = PromptTemplate(
        template="""
Bạn là AI giáo dục trong hệ thống LMS thông minh.
PHONG CÁCH TRÌNH BÀY BẮT BUỘC: {style}
(Hãy điều chỉnh giọng điệu, từ vựng và cách ví von sao cho đậm chất phong cách trên. Tuy nhiên, BẮT BUỘC VẪN PHẢI TUÂN THỦ LUẬT BÊN DƯỚI).

MỤC TIÊU:
- KHÔNG trả lời trực tiếp nếu học sinh hỏi đáp án.
- Dựa vào LỊCH SỬ TRÒ CHUYỆN để biết học sinh đã làm được đến đâu.
- Luôn kích thích tư duy, hỏi ngược lại.
- Nếu học sinh bế tắc ("không biết", "chịu") -> EXPLAIN (đưa lời giải).
- NẾU HỌC SINH TRẢ LỜI SAI -> ASK_BACK (Chỉ ra điểm vô lý để họ tự nhận ra).

LUẬT:
- Luôn trả về JSON hợp lệ (action, value, text).
- Action EXPLAIN: Dùng khi giải thích kiến thức hoặc cung cấp lời giải chi tiết khi học sinh bỏ cuộc.

QUY TẮC:
- Nếu hỏi đáp án lần đầu -> ASK_BACK (hỏi về hướng làm).
- Nếu học sinh bế tắc ("không biết", "chịu") -> EXPLAIN (đưa lời giải).
- NẾU HỌC SINH TRẢ LỜI SAI -> ASK_BACK (Tuyệt đối KHÔNG đưa đáp án đúng ngay. Khuyến khích học sinh, chỉ ra điểm mâu thuẫn trong kết quả của họ hoặc gợi ý họ kiểm tra lại một bước cụ thể).
- Nếu hỏi "học sao" -> SUGGEST_PATH.
- Nếu cần kiểm tra -> QUIZ.
--------------------------------
LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY:
{chat_history}

--------------------------------
DỮ LIỆU RAG (Tài liệu):
{context}

--------------------------------
CÂU HỎI HIỆN TẠI:
{question}

--------------------------------
Trả lời JSON:
{{
    "action": "EXPLAIN",
    "value": "<chủ đề bài tập>",
    "text": "<Nếu học sinh không biết làm: Trình bày lời giải chi tiết. Nếu không: Tiếp tục hỏi gợi mở>"
}}
""",
        input_variables=["chat_history", "context", "question", "style"],
    )

    _runtime.update(
        {
            "retriever": retriever,
            "llm": llm,
            "prompt": prompt,
            "ready": True,
        }
    )


# Read limited chat history from in-memory session store.
def get_chat_history(session_id: str) -> str:
    if session_id not in session_store or not session_store[session_id]:
        return "Chưa có lịch sử trò chuyện."

    lines = []
    for msg in session_store[session_id]:
        lines.append(f"- Học sinh: {msg['user']}\n- AI: {msg['ai']}")
    return "\n".join(lines)


# Push one user/ai turn to memory queue.
def update_chat_history(session_id: str, user_msg: str, ai_response: str) -> None:
    if session_id not in session_store:
        session_store[session_id] = deque(maxlen=MAX_HISTORY)
    session_store[session_id].append({"user": user_msg, "ai": ai_response})


# Clean model output to strict JSON object.
def clean_json_response(text: str | list) -> dict | None:
    if isinstance(text, list):
        text = "".join([
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in text
        ])

    if not isinstance(text, str):
        text = str(text)

    text = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group())
    except Exception:
        return None


# Fallback payload when model output cannot be parsed.
def fallback_response() -> dict:
    return {
        "action": "ASK_BACK",
        "value": "",
        "text": "Bạn đã thử cách nào để giải bài này chưa?",
    }


# Main chatbot inference preserving ask-back/explain control logic.
def chat_with_memory(question: str, session_id: str = "default_student_1", style: str = "Holmes") -> dict:
    init_chatbot_runtime()

    detailed_style = STYLE_MAP.get(style, STYLE_MAP["Tiêu chuẩn"])
    stuck_keywords = ["không biết", "chịu", "giải hộ", "đáp án là gì", "không hiểu", "khó quá"]
    is_stuck = any(keyword in question.lower() for keyword in stuck_keywords)
    has_history = session_id in session_store and len(session_store[session_id]) > 0

    actual_question = question
    if is_stuck and has_history:
        actual_question += (
            "\n\n[LỆNH TỪ HỆ THỐNG: Học sinh đã bế tắc và đã qua ít nhất 1 lượt gợi ý. "
            "BẮT BUỘC sử dụng action EXPLAIN và hiển thị ĐÁP ÁN, LỜI GIẢI CHI TIẾT từ context. "
            "KHÔNG hỏi ngược nữa.]"
        )

    history_str = get_chat_history(session_id)
    retriever = _runtime["retriever"]
    prompt = _runtime["prompt"]
    llm = _runtime["llm"]

    retrieved_docs = retriever.invoke(actual_question)
    context = format_docs(retrieved_docs)
    rendered_prompt = prompt.format(
        chat_history=history_str,
        context=context,
        question=actual_question,
        style=detailed_style,
    )

    result = llm.invoke(rendered_prompt)
    parsed = clean_json_response(result.content)
    used_fallback = parsed is None
    if not parsed:
        parsed = fallback_response()

    parsed.setdefault("action", "")
    parsed.setdefault("value", "")
    parsed.setdefault("text", "")

    if not used_fallback:
        update_chat_history(session_id, question, parsed["text"])

    return parsed
