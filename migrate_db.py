import sys
import os

# Add backend directory to sys.path if not running from there
sys.path.append(os.path.join(os.path.dirname(__file__)))

from backend.database import engine
from sqlalchemy import text

def run_fixes():
    """
    Manual fix script for users who encounter schema errors 
    (especially 'exam_type' column missing)
    """
    try:
        with engine.begin() as conn:
            # 1. Add exam_type to examinations
            try:
                conn.execute(text("ALTER TABLE examinations ADD COLUMN exam_type VARCHAR"))
                print("[SUCCESS] Added 'exam_type' column to 'examinations' table.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("[SKIP] Column 'exam_type' already exists in 'examinations'.")
                else:
                    print(f"[ERROR] examinations table fix failed: {e}")

            # 2. Ensure exam_code exists in questions (from previous updates)
            try:
                conn.execute(text("ALTER TABLE questions ADD COLUMN exam_code VARCHAR"))
                print("[SUCCESS] Added 'exam_code' column to 'questions' table.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("[SKIP] Column 'exam_code' already exists in 'questions'.")
                else:
                    print(f"[ERROR] questions table fix failed: {e}")

    except Exception as e:
        print(f"Main Error: {e}")

if __name__ == "__main__":
    print("AI_Qgen Manual DB Fix Utility")
    print("----------------------------")
    run_fixes()
    print("----------------------------")
    print("Process Finished.")
