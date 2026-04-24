import argparse
import json
import random
from pathlib import Path


DEFAULT_USER_ID = "hs_01"
DB_FILE = Path(__file__).with_name("mock_db.json")


def load_db(db_path: str | None = None) -> dict:
    """Load temporary quiz data from JSON; easy to swap for real DB later."""
    target_path = Path(db_path) if db_path else DB_FILE
    with target_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_default_user(db: dict, user_id: str = DEFAULT_USER_ID) -> dict:
    users = db.get("users", {})
    return users.get(user_id, {"name": "Unknown", "elos": {}, "answered_questions": []})


def get_next_question(user: dict, questions: list[dict], topic: str | None = None) -> dict | None:
    """Pick unanswered question with closest Elo.

    If topic is provided, questions are filtered by that topic.
    If topic is None, build a mixed quiz across all topics.
    """
    answered_ids = set(user.get("answered_questions", []))

    candidates = [
        question
        for question in questions
        if (topic is None or question.get("topic") == topic)
        and question.get("id") not in answered_ids
    ]

    return pick_closest_question_random(user, candidates)


def pick_closest_question_random(user: dict, candidates: list[dict]) -> dict | None:
    """Pick one closest question; randomize when many have same Elo distance."""
    if not candidates:
        return None

    distances = [
        abs(question.get("elo", 500) - get_user_topic_elo(user, question.get("topic", "")))
        for question in candidates
    ]
    min_distance = min(distances)

    tied_candidates = [
        question
        for question in candidates
        if abs(question.get("elo", 500) - get_user_topic_elo(user, question.get("topic", "")))
        == min_distance
    ]
    return random.choice(tied_candidates)


def build_mixed_quiz_set(user: dict, questions: list[dict], quiz_size: int = 10) -> list[dict]:
    """Create one mixed quiz set with a fixed number of questions.

    Selection rule: unanswered questions closest to user's Elo in each question topic.
    """
    answered_ids = set(user.get("answered_questions", []))
    remaining_questions = [q for q in questions if q.get("id") not in answered_ids]

    selected_questions = []
    pool = list(remaining_questions)

    while pool and len(selected_questions) < quiz_size:
        picked = pick_closest_question_random(user, pool)
        if not picked:
            break
        selected_questions.append(picked)
        pool = [question for question in pool if question.get("id") != picked.get("id")]

    return selected_questions


def get_question_by_id(questions: list[dict], question_id: str) -> dict | None:
    for question in questions:
        if question.get("id") == question_id:
            return question
    return None


def get_user_topic_elo(user: dict, topic: str, default_elo: float = 500) -> float:
    return float(user.get("elos", {}).get(topic, default_elo))


def update_elo(current_elo: float, question_elo: float, is_correct: int) -> float:
    expected_score = 1 / (1 + 10 ** ((question_elo - current_elo) / 400))
    return current_elo + 32 * (is_correct - expected_score)


def explain_elo_calculation(current_elo: float, question_elo: float, is_correct: int) -> dict:
    """Return detailed Elo terms so you can tune K/Elo buckets easier."""
    expected_score = 1 / (1 + 10 ** ((question_elo - current_elo) / 400))
    k_factor = 32
    new_elo = current_elo + k_factor * (is_correct - expected_score)
    return {
        "current_elo": current_elo,
        "question_elo": question_elo,
        "is_correct": is_correct,
        "expected_score": expected_score,
        "k_factor": k_factor,
        "new_elo": new_elo,
    }


def print_elo_calculation(current_elo: float, question_elo: float, is_correct: int) -> None:
    """Print Elo calculation in terminal for quick debugging/tuning."""
    detail = explain_elo_calculation(current_elo, question_elo, is_correct)
    print("=== ELO CALCULATION DEBUG ===")
    print(f"Current Elo (R_u): {detail['current_elo']}")
    print(f"Question Elo (R_q): {detail['question_elo']}")
    print(f"Result (is_correct): {detail['is_correct']}")
    print(
        "Expected E = 1 / (1 + 10 ** ((R_q - R_u) / 400)) "
        f"= {detail['expected_score']:.6f}"
    )
    print(
        "New Elo = R_u + K * (is_correct - E) "
        f"= {detail['new_elo']:.6f} (K={detail['k_factor']})"
    )


def grade_answer(question: dict, selected_answer_index: int) -> int:
    return int(selected_answer_index == int(question.get("correct_answer_index", -1)))


def apply_quiz_result(user: dict, question: dict, selected_answer_index: int) -> dict:
    """Update per-topic Elo and answered list for mixed quiz flow."""
    topic = question.get("topic", "")
    current_topic_elo = get_user_topic_elo(user, topic)
    question_elo = float(question.get("elo", 500))
    is_correct = grade_answer(question, selected_answer_index)

    new_topic_elo = update_elo(current_topic_elo, question_elo, is_correct)
    user.setdefault("elos", {})[topic] = new_topic_elo

    question_id = question.get("id")
    user.setdefault("answered_questions", [])
    if question_id and question_id not in user["answered_questions"]:
        user["answered_questions"].append(question_id)

    return {
        "is_correct": is_correct,
        "new_topic_elo": new_topic_elo,
        "topic": topic,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print Elo calculation detail in terminal")
    parser.add_argument("--current", type=float, default=500.0, help="Current user Elo")
    parser.add_argument("--question", type=float, default=500.0, help="Question Elo")
    parser.add_argument(
        "--correct",
        type=int,
        choices=[0, 1],
        default=1,
        help="1 if correct, 0 if wrong",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    print_elo_calculation(args.current, args.question, args.correct)
