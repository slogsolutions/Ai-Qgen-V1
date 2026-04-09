from sqlalchemy.orm import Session
from .. import models
import random

def build_paper(db: Session, subject_id: int, total_questions: int, q_type: str = "MCQ"):
    """
    Selects valid questions for a paper based on anti-repetition logic.
    Prioritizes questions with the lowest usage_count.
    Reshuffles (resets usage_count) if no questions are available with usage < 6.
    """
    from sqlalchemy.sql.expression import func

    # 1. Check if we have any questions with usage < 6
    query_base = db.query(models.Question).filter(models.Question.subject_id == subject_id)
    if q_type != "Mixed":
        query_base = query_base.filter(models.Question.q_type == q_type)
    
    available_fresh_count = query_base.filter(models.Question.usage_count < 6).count()

    # 2. Reshuffle Trigger: If all questions hit usage=6, reset the whole pool for this subject/type
    if available_fresh_count == 0:
        # Check if we have ANY questions at all before resetting
        if query_base.count() > 0:
            query_base.update({models.Question.usage_count: 0}, synchronize_session=False)
            db.commit()

    # 3. Selection Strategy:
    # We sort by usage_count (ascending) to pick the freshest questions.
    # We then sort by random() to ensure variety among questions with the same usage count.
    selected = query_base.order_by(
        models.Question.usage_count.asc(),
        func.random()
    ).limit(total_questions).all()

    # 4. Final verification/fallback
    if len(selected) < total_questions:
        # If we still don't have enough (database simply doesn't have enough questions), we take what we can get
        pass

    # 5. Update usage counters
    for q in selected:
        q.usage_count += 1
    
    db.commit()

    return selected
