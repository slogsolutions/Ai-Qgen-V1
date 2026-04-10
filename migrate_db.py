import sys
import os

# Add backend directory to sys.path if not running from there
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.database import engine
from sqlalchemy import text

def add_exam_type_column():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE examinations ADD COLUMN exam_type VARCHAR"))
            print("Successfully added 'exam_type' column to 'examinations' table.")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("Column 'exam_type' already exists. Skipping.")
        else:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_exam_type_column()
