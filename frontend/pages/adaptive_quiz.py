from pathlib import Path
import sys

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
	sys.path.append(str(ROOT_DIR))

from backend.quiz import apply_quiz_result, build_adaptive_quiz_set, get_default_user, get_question_by_id, load_db


st.set_page_config(page_title="Adaptive Quiz", page_icon="🧠", layout="wide")
st.title("Adaptive Quiz")
st.write("De hon hop 10 cau tu dong tao tu nhieu chu de. Elo duoc tinh rieng o backend.")

session_token = st.session_state.get("session_token", "")
auth_user = st.session_state.get("auth_user")
if not session_token or not auth_user:
	st.warning("Ban can dang nhap o trang chinh truoc khi lam quiz.")
	st.stop()

AUTH_USER_ID = auth_user.get("user_id", 1)

QUIZ_SIZE = 10

MEME_DIR_CANDIDATES = [ROOT_DIR / "meme", ROOT_DIR / "meme" / "meme"]


@st.cache_data(ttl=45, show_spinner=False)
def _load_db_cached(user_id: int, refresh_key: int = 0) -> dict:
	return load_db(user_id=user_id)


def _get_meme_filename(score: int) -> str:
	if 1 <= score <= 2:
		return "1.jpg"
	if 3 <= score <= 4:
		return "2.jpg"
	if score == 5:
		return "3.jpg"
	if 6 <= score <= 7:
		return "4.jpg"
	if 8 <= score <= 9:
		return "5.jpg"
	if score == 10:
		return "6.jpg"
	return ""


def _resolve_meme_path(score: int) -> Path | None:
	filename = _get_meme_filename(score)
	if not filename:
		return None

	for meme_dir in MEME_DIR_CANDIDATES:
		candidate = meme_dir / filename
		if candidate.exists():
			return candidate
	return None


def bootstrap_user_state() -> None:
	if "quiz_db_refresh" not in st.session_state:
		st.session_state.quiz_db_refresh = 0

	db = _load_db_cached(int(AUTH_USER_ID), int(st.session_state.quiz_db_refresh))
	base_user = get_default_user(db, "hs_01")
	all_questions = db.get("questions", [])

	if "all_questions" not in st.session_state:
		st.session_state.all_questions = all_questions

	if "quiz_user" not in st.session_state:
		st.session_state.quiz_user = {
			"db_user_id": int(AUTH_USER_ID),
			"name": base_user.get("name", "Hoc sinh Demo"),
			"elos": dict(base_user.get("elos", {})),
			"answered_questions": list(base_user.get("answered_questions", [])),
		}

	if "current_question_id" not in st.session_state:
		st.session_state.current_question_id = None

	if "quiz_set_ids" not in st.session_state:
		st.session_state.quiz_set_ids = []

	if "quiz_answers" not in st.session_state:
		st.session_state.quiz_answers = {}

	if "quiz_report" not in st.session_state:
		st.session_state.quiz_report = {"weak_topics": [], "review_topics": []}

	if "quiz_question_map" not in st.session_state:
		st.session_state.quiz_question_map = {
			q.get("id"): q for q in st.session_state.get("all_questions", []) if q.get("id")
		}

	if "generated_count" not in st.session_state:
		st.session_state.generated_count = 0

	if "generation_errors" not in st.session_state:
		st.session_state.generation_errors = []


def create_new_quiz_set() -> None:
	result = build_adaptive_quiz_set(
		user=st.session_state.quiz_user,
		quiz_size=QUIZ_SIZE,
		allow_generation=True,
		db_user_id=AUTH_USER_ID,
	)
	quiz_set = result.get("questions", [])
	st.session_state.quiz_set_ids = [q.get("id") for q in quiz_set if q.get("id")]
	st.session_state.quiz_question_map = {q.get("id"): q for q in quiz_set if q.get("id")}

	bank_map = {q.get("id"): q for q in st.session_state.get("all_questions", []) if q.get("id")}
	for question in quiz_set:
		qid = question.get("id")
		if qid:
			bank_map[qid] = question
	st.session_state.all_questions = list(bank_map.values())

	st.session_state.quiz_answers = {}
	st.session_state.quiz_report = result.get("report", {"weak_topics": [], "review_topics": []})
	st.session_state.generated_count = int(result.get("generated_count", 0))
	st.session_state.generation_errors = list(result.get("generation_errors", []))
	st.session_state.current_question_id = st.session_state.quiz_set_ids[0] if st.session_state.quiz_set_ids else None


def get_progress(quiz_ids: list[str], quiz_answers: dict) -> tuple[int, int]:
	answered_count = sum(1 for qid in quiz_ids if qid in quiz_answers)
	return answered_count, len(quiz_ids)


bootstrap_user_state()
all_questions = st.session_state.get("all_questions", [])

user_state = st.session_state.quiz_user
st.caption("Dang lam de hon hop da chu de")

report = st.session_state.quiz_report
if report.get("weak_topics") or report.get("review_topics"):
	st.caption(
		"Topic yeu: "
		+ ", ".join(report.get("weak_topics", []))
		+ " | Topic on tap: "
		+ ", ".join(report.get("review_topics", []))
	)
if st.session_state.generated_count > 0:
	st.info(f"Da bo sung {st.session_state.generated_count} cau hoi moi tu Gemini cho bo de nay.")
elif st.session_state.generation_errors:
	st.warning("Khong the tu sinh cau hoi bo sung. Chi tiet: " + " | ".join(st.session_state.generation_errors))

if not st.session_state.quiz_set_ids:
	create_new_quiz_set()

quiz_ids = st.session_state.quiz_set_ids
if len(quiz_ids) < QUIZ_SIZE:
	st.warning(
		f"Ngan hang hien tai chi con {len(quiz_ids)} cau chua lam, chua du {QUIZ_SIZE} cau cho mot bo quiz moi."
	)
	st.stop()

if st.session_state.current_question_id not in quiz_ids:
	st.session_state.current_question_id = quiz_ids[0]

answered_count, total_count = get_progress(quiz_ids, st.session_state.quiz_answers)
current_index = quiz_ids.index(st.session_state.current_question_id)

st.progress(answered_count / total_count)
st.markdown(f"**Tien do:** Cau {current_index + 1}/{total_count} | Da tra loi {answered_count}/{total_count}")

question_labels = []
for i, qid in enumerate(quiz_ids, start=1):
	status = "Da tra loi" if qid in st.session_state.quiz_answers else "Chua tra loi"
	question_labels.append(f"Cau {i} - {status}")

selected_label = st.selectbox(
	"Chon cau trong bo de",
	options=question_labels,
	index=current_index,
)
selected_index = question_labels.index(selected_label)
st.session_state.current_question_id = quiz_ids[selected_index]

current_question = None
if st.session_state.current_question_id:
	question_map = st.session_state.get("quiz_question_map", {})
	current_question = question_map.get(st.session_state.current_question_id)
	if not current_question:
		current_question = get_question_by_id(all_questions, st.session_state.current_question_id)

if not current_question:
	st.warning("TODO: Kich hoat LLM API sinh cau hoi moi cho bo de tiep theo")
else:
	st.subheader("Câu hỏi hiện tại")
	st.write(current_question.get("content", ""))
	st.caption(f"Chu de: {current_question.get('topic', 'N/A')}")

	options = current_question.get("options", [])
	letters = ["A", "B", "C", "D"]
	question_id = current_question.get("id", "")
	radio_key = f"choice_{question_id}"
	if radio_key not in st.session_state:
		st.session_state[radio_key] = 0

	choice_index = st.radio(
		"Chọn đáp án",
		options=list(range(len(options))),
		format_func=lambda idx: f"{letters[idx]}. {options[idx]}",
		key=radio_key,
		horizontal=False,
	)

	if st.button("Tra loi cau nay", type="primary"):
		if question_id in st.session_state.quiz_answers:
			st.info("Cau nay da duoc nop. Ban co the chuyen sang cau khac.")
			st.stop()

		result = apply_quiz_result(user_state, current_question, int(choice_index))
		is_correct = int(result["is_correct"])
		st.session_state.quiz_answers[question_id] = {
			"selected_index": int(choice_index),
			"is_correct": is_correct,
		}

		if is_correct:
			st.success("Chính xác! " + current_question.get("explanation", ""))
		else:
			st.error("Chưa đúng. " + current_question.get("explanation", ""))

	if st.button("Cau tiep theo chua lam"):
		remaining = [qid for qid in quiz_ids if qid not in st.session_state.quiz_answers]
		if remaining:
			st.session_state.current_question_id = remaining[0]
			st.rerun()
		st.info("Ban da tra loi het bo de hien tai.")

if answered_count == total_count and total_count > 0:
	correct_total = sum(item.get("is_correct", 0) for item in st.session_state.quiz_answers.values())
	wrong_total = total_count - correct_total
	score_ratio = (correct_total / total_count) if total_count else 0.0

	st.subheader("Ket qua cuoi bo quiz")
	col1, col2, col3 = st.columns(3)
	col1.metric("So cau dung", correct_total)
	col2.metric("So cau sai", wrong_total)
	col3.metric("Ty le dung", f"{score_ratio * 100:.0f}%")

	meme_path = _resolve_meme_path(correct_total)
	if meme_path:
		st.image(str(meme_path), caption=f"Meme theo diem: {correct_total}/{total_count}", width="stretch")
	elif 1 <= correct_total <= 10:
		st.info("Khong tim thay file meme tuong ung trong folder meme.")

	next_quiz_choice = st.radio(
		"Ban co muon tao bo quiz tiep theo khong?",
		options=["Co", "Khong"],
		horizontal=True,
	)

	if next_quiz_choice == "Co" and st.button("Tao bo quiz tiep theo"):
		create_new_quiz_set()
		if len(st.session_state.quiz_set_ids) < QUIZ_SIZE:
			st.warning("TODO: Kich hoat LLM API de sinh them cau hoi cho bo 10 cau moi")
		st.rerun()


