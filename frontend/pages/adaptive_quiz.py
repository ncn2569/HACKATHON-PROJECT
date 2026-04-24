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

QUIZ_SIZE = 10


def bootstrap_user_state() -> None:
	db = load_db()
	base_user = get_default_user(db, "hs_01")

	if "quiz_user" not in st.session_state:
		st.session_state.quiz_user = {
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

	if "generated_count" not in st.session_state:
		st.session_state.generated_count = 0

	if "generation_errors" not in st.session_state:
		st.session_state.generation_errors = []


def create_new_quiz_set(all_questions: list[dict]) -> None:
	result = build_adaptive_quiz_set(
		user=st.session_state.quiz_user,
		quiz_size=QUIZ_SIZE,
		allow_generation=True,
	)
	quiz_set = result.get("questions", [])
	st.session_state.quiz_set_ids = [q.get("id") for q in quiz_set if q.get("id")]
	st.session_state.quiz_answers = {}
	st.session_state.quiz_report = result.get("report", {"weak_topics": [], "review_topics": []})
	st.session_state.generated_count = int(result.get("generated_count", 0))
	st.session_state.generation_errors = list(result.get("generation_errors", []))
	st.session_state.current_question_id = st.session_state.quiz_set_ids[0] if st.session_state.quiz_set_ids else None


def get_progress(quiz_ids: list[str], quiz_answers: dict) -> tuple[int, int]:
	answered_count = sum(1 for qid in quiz_ids if qid in quiz_answers)
	return answered_count, len(quiz_ids)


bootstrap_user_state()
db_data = load_db()
all_questions = db_data.get("questions", [])

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
	create_new_quiz_set(all_questions)

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

	st.subheader("Ket qua cuoi bo quiz")
	col1, col2 = st.columns(2)
	col1.metric("So cau dung", correct_total)
	col2.metric("So cau sai", wrong_total)

	next_quiz_choice = st.radio(
		"Ban co muon tao bo quiz tiep theo khong?",
		options=["Co", "Khong"],
		horizontal=True,
	)

	if next_quiz_choice == "Co" and st.button("Tao bo quiz tiep theo"):
		create_new_quiz_set(all_questions)
		if len(st.session_state.quiz_set_ids) < QUIZ_SIZE:
			st.warning("TODO: Kich hoat LLM API de sinh them cau hoi cho bo 10 cau moi")
		st.rerun()


