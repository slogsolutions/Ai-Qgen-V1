import requests
import json

payload = {
    "subject_id": 1,
    "exam_title": "Test Exam",
    "exam_type": "Main",
    "total_marks": 100,
    "sections_config": [
        {
            "name": "Section A",
            "total_q": 10,
            "attempt_any": 10,
            "marks_per_q": 1,
            "types_config": [
                {"q_type": "MCQ", "num_q": 10}
            ]
        }
    ]
}

try:
    res = requests.post("http://localhost:8000/api/v1/papers/generate/", json=payload)
    print("Status Code:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", str(e))
