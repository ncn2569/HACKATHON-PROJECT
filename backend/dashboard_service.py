# ==================================================
# FILE: .\backend\dashboard_service.py (TẠO MỚI)
# ==================================================
try:
    from .data_pool import run_query
except ImportError:
    from data_pool import run_query

def get_class_dashboard() -> dict:
    total_students = run_query("SELECT COUNT(*) as count FROM users WHERE role='student'")[0]['count']
    total_quizzes = run_query("SELECT COUNT(*) as count FROM quizzes")[0]['count']
    
    avg_score_res = run_query("SELECT AVG(correct_answers * 1.0 / NULLIF(total_questions, 0)) as avg FROM quizzes")
    avg_score = avg_score_res[0]['avg'] if avg_score_res and avg_score_res[0]['avg'] is not None else 0
    
    avg_elo_res = run_query("SELECT AVG(elo_score) as avg FROM user_skills")
    avg_elo = avg_elo_res[0]['avg'] if avg_elo_res and avg_elo_res[0]['avg'] is not None else 0

    dist_rows = run_query("""
        SELECT 
            CASE 
                WHEN correct_answers * 1.0 / NULLIF(total_questions, 0) >= 0.8 THEN 'Good'
                WHEN correct_answers * 1.0 / NULLIF(total_questions, 0) >= 0.5 THEN 'Medium'
                ELSE 'Weak'
            END as level,
            COUNT(*) as count
        FROM quizzes
        WHERE total_questions > 0
        GROUP BY level
    """)
    distribution = {row['level']: row['count'] for row in dist_rows}

    return {
        "total_students": total_students,
        "total_quizzes": total_quizzes,
        "avg_score": round(float(avg_score), 2),
        "avg_elo": round(float(avg_elo), 2),
        "score_distribution": distribution
    }

def get_student_dashboard(user_id: int) -> dict:
    # Basic stats
    basic_stats = run_query("""
        SELECT COUNT(*) as quiz_count,
               AVG(correct_answers * 1.0 / NULLIF(total_questions, 0)) as avg_score
        FROM quizzes
        WHERE user_id = %s
    """, (user_id,))
    quiz_count = basic_stats[0]['quiz_count']
    avg_score = basic_stats[0]['avg_score'] or 0

    # Elo
    elo_stats = run_query("SELECT AVG(elo_score) as avg_elo FROM user_skills WHERE user_id = %s", (user_id,))
    avg_elo = elo_stats[0]['avg_elo'] or 0

    # Accuracy
    acc_stats = run_query("""
        SELECT COUNT(*) as total_answers,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers
        FROM quiz_attempt_answers
        WHERE user_id = %s
    """, (user_id,))
    total_answers = acc_stats[0]['total_answers'] or 0
    correct_answers = acc_stats[0]['correct_answers'] or 0
    accuracy = float(correct_answers) / float(total_answers) if total_answers > 0 else 0.0

    # Weak/Strong Topics
    topic_stats = run_query("""
        SELECT t.name,
               COUNT(*) as total,
               SUM(CASE WHEN qa.is_correct THEN 1 ELSE 0 END) as correct
        FROM quiz_attempt_answers qa
        JOIN questions q ON qa.question_id = q.question_id
        JOIN topics t ON q.topic_id = t.topic_id
        WHERE qa.user_id = %s
        GROUP BY t.name
    """, (user_id,))

    weak_topics, strong_topics = [], []
    for row in topic_stats:
        total = row['total'] or 0
        correct = row['correct'] or 0
        acc = float(correct) / float(total) if total > 0 else 0.0
        topic_data = {"topic": row['name'], "accuracy": round(acc, 2)}
        if acc < 0.5:
            weak_topics.append(topic_data)
        else:
            strong_topics.append(topic_data)

    return {
        "user_id": user_id,
        "quiz_count": quiz_count,
        "avg_score": round(float(avg_score), 2),
        "avg_elo": round(float(avg_elo), 2),
        "accuracy": round(accuracy, 2),
        "weak_topics": weak_topics,
        "strong_topics": strong_topics
    }

def get_student_habit(user_id: int) -> dict:
    stats = run_query("""
        SELECT COUNT(*) as total_sessions,
               AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) as avg_time
        FROM quizzes
        WHERE user_id = %s
    """, (user_id,))
    total_sessions = stats[0]['total_sessions']
    avg_time = stats[0]['avg_time'] or 0
    return {
        "total_sessions": total_sessions,
        "avg_time_seconds": round(float(avg_time), 2)
    }

def get_at_risk_students() -> dict:
    rows = run_query("""
        SELECT u.user_id, u.email,
               AVG(q.correct_answers * 1.0 / NULLIF(q.total_questions, 0)) AS avg_score,
               AVG(us.elo_score) AS avg_elo,
               COALESCE(MAX(eh.old_elo - eh.new_elo), 0) as elo_drop
        FROM users u
        LEFT JOIN quizzes q ON u.user_id = q.user_id
        LEFT JOIN user_skills us ON u.user_id = us.user_id
        LEFT JOIN elo_history eh ON u.user_id = eh.user_id
        WHERE u.role = 'student'
        GROUP BY u.user_id, u.email
        HAVING 
            AVG(q.correct_answers * 1.0 / NULLIF(q.total_questions, 0)) < 0.5
            OR AVG(us.elo_score) < 900
            OR COALESCE(MAX(eh.old_elo - eh.new_elo), 0) > 0
    """)
    students = []
    for r in rows:
        students.append({
            "user_id": r['user_id'],
            "email": r['email'],
            "avg_score": round(float(r['avg_score'] or 0), 2),
            "avg_elo": round(float(r['avg_elo'] or 0), 2),
            "elo_drop": round(float(r['elo_drop'] or 0), 2)
        })
    return {"at_risk_students": students}