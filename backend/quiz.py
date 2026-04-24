import argparse
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any

try:
    from .llm_client import call_gemini_chat_api
except ImportError:
    from llm_client import call_gemini_chat_api


DEFAULT_USER_ID = "hs_01"
DB_FILE = Path(__file__).with_name("mock_db.json")
DEFAULT_ELO = 500.0
DEFAULT_ELO_BAND = 50


# Load quiz database from local JSON mock store.
def load_db(db_path: str | None = None) -> dict:
    """Load quiz data from JSON.

    This is the temporary persistence layer and can be replaced later
    by PostgreSQL/MongoDB without changing call sites.
    """
    target_path = Path(db_path) if db_path else DB_FILE
    with target_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# Save updated quiz database (including generated questions).
def save_db(db_data: dict, db_path: str | None = None) -> None:
    """Persist current DB state back to disk."""
    target_path = Path(db_path) if db_path else DB_FILE
    with target_path.open("w", encoding="utf-8") as file:
        json.dump(db_data, file, ensure_ascii=False, indent=2)


# Return demo user profile (defaults to hs_01).
def get_default_user(db: dict, user_id: str = DEFAULT_USER_ID) -> dict:
    """Return default demo user from DB."""
    users = db.get("users", {})
    return users.get(user_id, {"name": "Unknown", "elos": {}, "answered_questions": []})


# Get Elo for one topic; fallback avoids missing-key crashes.
def get_user_topic_elo(user: dict, topic: str, default_elo: float = DEFAULT_ELO) -> float:
    """Read user's Elo for one topic; fallback to default Elo if missing."""
    return float(user.get("elos", {}).get(topic, default_elo))


# Find question object by id in a question list.
def get_question_by_id(questions: list[dict], question_id: str) -> dict | None:
    """Locate one question object by id."""
    for question in questions:
        if question.get("id") == question_id:
            return question
    return None


# Pick next unanswered question near learner skill level.
def get_next_question(user: dict, questions: list[dict], topic: str | None = None) -> dict | None:
    """Pick one unanswered question nearest to user Elo.

    Tie-breaker behavior: if many questions share the same Elo distance,
    pick one random question among those ties.
    """
    answered_ids = set(user.get("answered_questions", []))

    candidates = [
        question
        for question in questions
        if (topic is None or question.get("topic") == topic)
        and question.get("id") not in answered_ids
    ]

    return pick_closest_question_random(user, candidates)


# Tie-break selector: random among questions with equal Elo distance.
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


# Build a mixed-topic quiz deck from remaining unanswered questions.
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


# Core Elo update formula applied after each answer.
def update_elo(current_elo: float, question_elo: float, is_correct: int) -> float:
    """Apply Elo update formula after one answer submission."""
    expected_score = 1 / (1 + 10 ** ((question_elo - current_elo) / 400))
    return current_elo + 32 * (is_correct - expected_score)


# Return all intermediate Elo values for debugging/tuning.
def explain_elo_calculation(current_elo: float, question_elo: float, is_correct: int) -> dict:
    """Return full Elo math terms for debugging and tuning."""
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


# Print a readable Elo formula breakdown in terminal.
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


# Convert selected option into binary correctness label.
def grade_answer(question: dict, selected_answer_index: int) -> int:
    """Return 1 if answer is correct, 0 otherwise."""
    return int(selected_answer_index == int(question.get("correct_answer_index", -1)))


# Persist answer outcome to user state (per-topic Elo + answered ids).
def apply_quiz_result(user: dict, question: dict, selected_answer_index: int) -> dict:
    """Update user state after one answer.

    - Elo is updated only for the question's topic.
    - Question id is appended into answered_questions once.
    """
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


# Report phase: classify topics into weak/review buckets.
def assess_user_topic_status(user: dict, questions: list[dict]) -> dict:
    """Report user topic status: weak topics vs review topics.

    Heuristic:
    - weak topic: Elo < 500 OR answered_count < 2
    - review topic: otherwise
    """
    answered_ids = set(user.get("answered_questions", []))
    topics_in_db = sorted({question.get("topic", "") for question in questions if question.get("topic")})
    user_topics = sorted(user.get("elos", {}).keys())
    all_topics = sorted(set(topics_in_db + user_topics))

    topic_answered_count = {topic: 0 for topic in all_topics}
    for question in questions:
        if question.get("id") in answered_ids:
            topic = question.get("topic", "")
            if topic in topic_answered_count:
                topic_answered_count[topic] += 1

    weak_topics = []
    review_topics = []
    topic_report: dict[str, dict[str, Any]] = {}

    for topic in all_topics:
        topic_elo = get_user_topic_elo(user, topic, default_elo=DEFAULT_ELO)
        answered_count = topic_answered_count.get(topic, 0)
        is_weak = topic_elo < DEFAULT_ELO or answered_count < 2

        topic_report[topic] = {
            "elo": topic_elo,
            "answered_count": answered_count,
            "status": "weak" if is_weak else "review",
        }
        if is_weak:
            weak_topics.append(topic)
        else:
            review_topics.append(topic)

    return {
        "weak_topics": weak_topics,
        "review_topics": review_topics,
        "topic_report": topic_report,
    }


# Fetching phase: query DB with topic + unanswered + Elo-band constraints.
def fetch_questions_for_topic(
    user: dict,
    topic: str,
    questions: list[dict],
    required_count: int,
    elo_band: int = DEFAULT_ELO_BAND,
    exclude_ids: set[str] | None = None,
) -> list[dict]:
    """Fetch DB questions that satisfy all constraints in Fetching Phase.

    Constraints:
    - question.topic == target topic
    - question.id not in user.answered_questions
    - question.id not in exclude_ids (already reserved in current quiz)
    - abs(question.elo - user_topic_elo) <= elo_band
    """
    answered_ids = set(user.get("answered_questions", []))
    blocked_ids = exclude_ids or set()
    user_elo = get_user_topic_elo(user, topic, default_elo=DEFAULT_ELO)

    candidates = [
        question
        for question in questions
        if question.get("topic") == topic
        and question.get("id") not in answered_ids
        and question.get("id") not in blocked_ids
        and abs(float(question.get("elo", DEFAULT_ELO)) - user_elo) <= elo_band
    ]

    random.shuffle(candidates)
    return candidates[:required_count]


# Generation phase helper: sample nearby questions for few-shot context.
def sample_context_questions(
    questions: list[dict],
    topic: str,
    target_elo: float,
    sample_size: int = 2,
) -> list[dict]:
    """Pick 1-2 sample questions for few-shot prompting.

    Priority: same topic and closest Elo to target_elo.
    """
    same_topic = [question for question in questions if question.get("topic") == topic]
    if not same_topic:
        return []

    sorted_samples = sorted(
        same_topic,
        key=lambda question: abs(float(question.get("elo", DEFAULT_ELO)) - target_elo),
    )
    return sorted_samples[:sample_size]


# Build Gemini prompt pair from sampled questions and requested target.
def build_generation_prompts(topic: str, target_elo: float, missing_count: int, samples: list[dict]) -> tuple[str, str]:
    """Build system/user prompts for LLM generation in strict JSON schema."""
    sample_json = json.dumps(samples, ensure_ascii=False, indent=2)
    system_prompt = (
        "Bạn là AI tạo câu hỏi trắc nghiệm cho hệ thống LMS. "
        "Bắt buộc trả về JSON hợp lệ, không thêm markdown, không thêm text ngoài JSON."
    )
    user_prompt = (
        f"Dựa vào định dạng, chủ đề và độ khó của các câu hỏi mẫu sau, "
        f"hãy tạo thêm {missing_count} câu hỏi mới trắc nghiệm 4 đáp án. "
        "Trả về đúng JSON array với mỗi phần tử có các field: "
        "id (random string), topic, elo, content, options, correct_answer_index, explanation. "
        f"Topic bắt buộc: {topic}. Elo bắt buộc: {int(target_elo)}. "
        "correct_answer_index phải thuộc [0,1,2,3]. options phải có đúng 4 phần tử string. "
        f"\n\nCâu hỏi mẫu:\n{sample_json}"
    )
    return system_prompt, user_prompt


# Strip markdown fences and keep raw JSON payload text.
def _extract_json_payload(raw_text: str) -> str:
    """Extract likely JSON payload from raw LLM output."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


# Parse and validate generated JSON into canonical question objects.
def parse_generated_questions_json(raw_text: str, topic: str, target_elo: float) -> list[dict]:
    """Parse and normalize generated questions returned by LLM."""
    payload = _extract_json_payload(raw_text)
    data = json.loads(payload)
    if isinstance(data, dict):
        data = data.get("questions", [])
    if not isinstance(data, list):
        return []

    normalized_questions: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        options = item.get("options", [])
        if not isinstance(options, list) or len(options) != 4:
            continue

        correct_answer_index = item.get("correct_answer_index", 0)
        if correct_answer_index not in [0, 1, 2, 3]:
            continue

        question_id = str(item.get("id") or f"gen_{topic}_{uuid.uuid4().hex[:8]}")
        normalized_questions.append(
            {
                "id": question_id,
                "topic": topic,
                "elo": int(item.get("elo", target_elo)),
                "content": str(item.get("content", "")).strip(),
                "options": [str(option) for option in options],
                "correct_answer_index": int(correct_answer_index),
                "explanation": str(item.get("explanation", "Generated by LLM")).strip(),
            }
        )

    return [question for question in normalized_questions if question.get("content")]


# Update phase: append newly generated unique questions into mock DB.
def append_questions_to_db(new_questions: list[dict], db_path: str | None = None) -> int:
    """Append generated questions into DB for future reuse."""
    if not new_questions:
        return 0

    db_data = load_db(db_path)
    existing_ids = {question.get("id") for question in db_data.get("questions", [])}

    accepted_questions = [
        question for question in new_questions if question.get("id") and question.get("id") not in existing_ids
    ]
    if not accepted_questions:
        return 0

    db_data.setdefault("questions", []).extend(accepted_questions)
    save_db(db_data, db_path)
    return len(accepted_questions)


# Call Gemini to create missing questions when DB supply is insufficient.
def generate_questions_with_llm(topic: str, target_elo: float, missing_count: int, questions: list[dict]) -> list[dict]:
    """Call LLM API to generate missing questions (Generation Phase)."""
    if missing_count <= 0:
        return []

    samples = sample_context_questions(questions, topic, target_elo, sample_size=2)
    system_prompt, user_prompt = build_generation_prompts(topic, target_elo, missing_count, samples)

    raw_response = call_gemini_chat_api(system_prompt=system_prompt, user_prompt=user_prompt)
    return parse_generated_questions_json(raw_response, topic=topic, target_elo=target_elo)


# Split quiz quota across weak vs review topic groups.
def _distribute_quiz_count(weak_topics: list[str], review_topics: list[str], quiz_size: int) -> dict[str, int]:
    """Split requested quiz size across weak/review topics.

    Strategy:
    - 70% slots for weak topics
    - 30% slots for review topics
    - if one group is empty, assign all slots to the other group
    """
    distribution: dict[str, int] = {}
    if not weak_topics and not review_topics:
        return distribution

    if not weak_topics:
        weak_quota = 0
        review_quota = quiz_size
    elif not review_topics:
        weak_quota = quiz_size
        review_quota = 0
    else:
        weak_quota = max(1, round(quiz_size * 0.7))
        review_quota = quiz_size - weak_quota

    if weak_topics:
        base = weak_quota // len(weak_topics)
        remainder = weak_quota % len(weak_topics)
        for index, topic in enumerate(weak_topics):
            distribution[topic] = base + (1 if index < remainder else 0)

    if review_topics:
        base = review_quota // len(review_topics)
        remainder = review_quota % len(review_topics)
        for index, topic in enumerate(review_topics):
            distribution[topic] = distribution.get(topic, 0) + base + (1 if index < remainder else 0)

    return distribution


# Orchestrate full 4-phase adaptive quiz pipeline.
def build_adaptive_quiz_set(
    user: dict,
    quiz_size: int = 10,
    elo_band: int = DEFAULT_ELO_BAND,
    db_path: str | None = None,
    allow_generation: bool = True,
) -> dict:
    """End-to-end pipeline for adaptive quiz generation.

    Report Phase:
        - assess weak vs review topics.
    Fetching Phase:
        - fetch matching questions from DB by topic, answered, and Elo band.
    Generation Phase:
        - if topic pool is short, call LLM to generate missing questions.
    Update Phase:
        - append generated questions to DB and include them in current quiz set.
    """
    db_data = load_db(db_path)
    all_questions = db_data.get("questions", [])
    topic_status = assess_user_topic_status(user, all_questions)

    weak_topics = topic_status.get("weak_topics", [])
    review_topics = topic_status.get("review_topics", [])
    topic_quota = _distribute_quiz_count(weak_topics, review_topics, quiz_size)

    selected_questions: list[dict] = []
    selected_ids: set[str] = set()
    generated_questions_total: list[dict] = []
    generation_errors: list[str] = []

    for topic, required_count in topic_quota.items():
        if required_count <= 0:
            continue

        fetched = fetch_questions_for_topic(
            user=user,
            topic=topic,
            questions=all_questions,
            required_count=required_count,
            elo_band=elo_band,
            exclude_ids=selected_ids,
        )

        if len(fetched) < required_count and allow_generation:
            missing_count = required_count - len(fetched)
            target_elo = get_user_topic_elo(user, topic, default_elo=DEFAULT_ELO)
            generated = []
            try:
                generated = generate_questions_with_llm(topic, target_elo, missing_count, all_questions)
            except Exception as exc:
                generation_errors.append(f"{topic}: {exc}")

            if generated:
                appended_count = append_questions_to_db(generated, db_path=db_path)
                if appended_count > 0:
                    generated_questions_total.extend(generated)
                    all_questions.extend(generated)

                refetch = fetch_questions_for_topic(
                    user=user,
                    topic=topic,
                    questions=all_questions,
                    required_count=required_count,
                    elo_band=elo_band,
                    exclude_ids=selected_ids,
                )
                fetched = refetch

        for question in fetched:
            question_id = question.get("id")
            if question_id and question_id not in selected_ids:
                selected_questions.append(question)
                selected_ids.add(question_id)

    if len(selected_questions) < quiz_size:
        remaining_pool = [
            question
            for question in all_questions
            if question.get("id") not in selected_ids
            and question.get("id") not in set(user.get("answered_questions", []))
        ]
        random.shuffle(remaining_pool)
        for question in remaining_pool:
            if len(selected_questions) >= quiz_size:
                break
            question_id = question.get("id")
            if question_id and question_id not in selected_ids:
                selected_questions.append(question)
                selected_ids.add(question_id)

    return {
        "questions": selected_questions[:quiz_size],
        "report": topic_status,
        "generated_count": len(generated_questions_total),
        "generation_errors": generation_errors,
    }


# Build CLI arguments for quick local backend debugging.
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Debug Elo math and adaptive quiz backend")
    parser.add_argument("--current", type=float, default=500.0, help="Current user Elo")
    parser.add_argument("--question", type=float, default=500.0, help="Question Elo")
    parser.add_argument(
        "--correct",
        type=int,
        choices=[0, 1],
        default=1,
        help="1 if correct, 0 if wrong",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print topic weak/review report for default user",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    if args.report:
        db = load_db()
        user = get_default_user(db, DEFAULT_USER_ID)
        print(json.dumps(assess_user_topic_status(user, db.get("questions", [])), ensure_ascii=False, indent=2))
    else:
        print_elo_calculation(args.current, args.question, args.correct)
