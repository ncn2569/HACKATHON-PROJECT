try:
	from .quiz import (
		apply_quiz_result,
		build_mixed_quiz_set,
		explain_elo_calculation,
		get_default_user,
		get_next_question,
		get_question_by_id,
		get_user_topic_elo,
		grade_answer,
		load_db,
		pick_closest_question_random,
		print_elo_calculation,
		update_elo,
	)
except ImportError:
	from quiz import (
		apply_quiz_result,
		build_mixed_quiz_set,
		explain_elo_calculation,
		get_default_user,
		get_next_question,
		get_question_by_id,
		get_user_topic_elo,
		grade_answer,
		load_db,
		pick_closest_question_random,
		print_elo_calculation,
		update_elo,
	)


__all__ = [
	"load_db",
	"get_default_user",
	"get_next_question",
	"build_mixed_quiz_set",
	"pick_closest_question_random",
	"get_question_by_id",
	"get_user_topic_elo",
	"update_elo",
	"explain_elo_calculation",
	"print_elo_calculation",
	"grade_answer",
	"apply_quiz_result",
]
