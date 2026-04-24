from pathlib import Path
import argparse
import json

from quiz import add_question_to_pool, add_questions_to_pool


# Payload format for add_question_to_pool:
# {
#   "topic": "algebra" | "geometry" | ...,
#   "elo": 1000,
#   "content": "question text",
#   "options": ["A", "B", "C", "D"],
#   "correct_answer_index": 0,
#   "explanation": "optional"
# }

def build_single_payload() -> dict:
    return {
        "topic": "algebra",
        "elo": 1000,
        "content": "Test insert: 12 + 8 bang bao nhieu?",
        "options": ["18", "19", "20", "21"],
        "correct_answer_index": 2,
        "explanation": "12 + 8 = 20",
    }


def build_batch_payload() -> list[dict]:
    return [
        {
            "topic": "geometry",
            "elo": 950,
            "content": "Test insert batch: Tam giac deu co may canh bang nhau?",
            "options": ["1", "2", "3", "4"],
            "correct_answer_index": 2,
            "explanation": "Tam giac deu co 3 canh bang nhau.",
        },
        {
            "topic": "grammar",
            "elo": 1000,
            "content": "Test insert batch: She ___ to school every day.",
            "options": ["go", "goes", "going", "gone"],
            "correct_answer_index": 1,
            "explanation": "Chu ngu so it o thi hien tai don dung 'goes'.",
        },
    ]


def run_single_test(db_path: str | None = None) -> None:
    payload = build_single_payload()
    inserted = add_question_to_pool(payload, added_by="tutor", db_path=db_path)

    print("=== SINGLE INSERT TEST ===")
    print("INPUT:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("OUTPUT:")
    print(json.dumps(inserted, ensure_ascii=False, indent=2) if inserted else "Insert failed")


def run_batch_test(db_path: str | None = None) -> None:
    payloads = build_batch_payload()
    inserted_list = add_questions_to_pool(payloads, added_by="llm", db_path=db_path)

    print("=== BATCH INSERT TEST ===")
    print("INPUT SIZE:", len(payloads))
    print("OUTPUT SIZE:", len(inserted_list))
    print(json.dumps(inserted_list, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual test for add_question_to_pool APIs")
    parser.add_argument("--mode", choices=["one", "batch", "all"], default="all")
    parser.add_argument(
        "--json-file",
        default="",
        help="Optional JSON file path fallback. Example: backend/mock_db.json",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = args.json_file.strip() or None

    if db_path:
        db_path = str(Path(db_path).resolve())

    if args.mode in ("one", "all"):
        run_single_test(db_path=db_path)
    if args.mode in ("batch", "all"):
        run_batch_test(db_path=db_path)


if __name__ == "__main__":
    main()
