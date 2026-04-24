import argparse

from quiz import (
    build_mixed_quiz_set,
    explain_elo_calculation,
    get_default_user,
    get_next_question,
    load_db,
    print_elo_calculation,
)


def run_elo_demo(current_elo: float, question_elo: float, is_correct: int) -> None:
    print("\n[DEMO] Elo formula detail")
    print_elo_calculation(current_elo, question_elo, is_correct)


def run_tie_random_demo(topic: str = "giai_tich", runs: int = 6) -> None:
    print("\n[DEMO] Random tie-break when same Elo distance")
    db = load_db()
    user = get_default_user(db, "hs_01")
    questions = db.get("questions", [])

    print(f"Topic: {topic}")
    picked_ids = []
    for _ in range(runs):
        picked = get_next_question(user, questions, topic=topic)
        picked_id = picked.get("id") if picked else "NONE"
        picked_ids.append(picked_id)
    print("Picked sequence:", picked_ids)


def run_quiz_set_preview(quiz_size: int = 10) -> None:
    print("\n[DEMO] Build mixed quiz set")
    db = load_db()
    user = get_default_user(db, "hs_01")
    questions = db.get("questions", [])

    quiz_set = build_mixed_quiz_set(user, questions, quiz_size=quiz_size)
    print(f"Quiz size requested: {quiz_size}")
    print(f"Quiz size built: {len(quiz_set)}")

    for index, question in enumerate(quiz_set, start=1):
        print(
            f"{index:02d}. id={question.get('id')} | "
            f"topic={question.get('topic')} | elo={question.get('elo')}"
        )


def run_formula_table() -> None:
    print("\n[DEMO] Quick Elo table for tuning")
    scenarios = [
        (500, 450, 1),
        (500, 500, 1),
        (500, 550, 1),
        (500, 450, 0),
        (500, 500, 0),
        (500, 550, 0),
    ]

    for current_elo, question_elo, is_correct in scenarios:
        detail = explain_elo_calculation(current_elo, question_elo, is_correct)
        print(
            "R_u={current} | R_q={question} | correct={correct} | E={expected:.4f} | new={new:.2f}".format(
                current=current_elo,
                question=question_elo,
                correct=is_correct,
                expected=detail["expected_score"],
                new=detail["new_elo"],
            )
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual test utility for Adaptive Quiz Elo")
    parser.add_argument(
        "--mode",
        choices=["all", "elo", "tie", "set", "table"],
        default="all",
        help="What demo to run",
    )
    parser.add_argument("--current", type=float, default=500.0, help="Current Elo")
    parser.add_argument("--question", type=float, default=550.0, help="Question Elo")
    parser.add_argument("--correct", type=int, choices=[0, 1], default=1, help="1=correct, 0=wrong")
    parser.add_argument("--topic", type=str, default="giai_tich", help="Topic for tie random demo")
    parser.add_argument("--runs", type=int, default=6, help="How many picks for tie random demo")
    parser.add_argument("--size", type=int, default=10, help="Quiz size for set preview")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    if args.mode in ("all", "elo"):
        run_elo_demo(args.current, args.question, args.correct)
    if args.mode in ("all", "tie"):
        run_tie_random_demo(args.topic, args.runs)
    if args.mode in ("all", "set"):
        run_quiz_set_preview(args.size)
    if args.mode in ("all", "table"):
        run_formula_table()


if __name__ == "__main__":
    main()


# Quick use guide (uncomment to run in IDE one-click):
# run_elo_demo(500, 550, 1)
# run_tie_random_demo(topic="giai_tich", runs=10)
# run_quiz_set_preview(quiz_size=10)
# run_formula_table()
