import os
from backend.services import exporter

sections_data = {
    "Section A": [
        {"q_type": "T/F", "q": "Damper winding is used to prevent hunting.", "q_hi": "अवमंदन कुण्डलन का प्रयोग हंटिंग रोकने के लिए करते हैं।"},
        {"q_type": "T/F", "q": "Slip is always one at the time of starting.", "q_hi": "प्रारम्भ के समय स्लिप का मान सदैव एक होता है।"},
        {"q_type": "FIB", "q": "Hunting in a synchronous motor is prevented by using ___ winding.", "q_hi": "तुल्यकालिक मोटर में हंटिंग ___ कुण्डलन के प्रयोग करने से कम की जाती है।"},
        {"q_type": "FIB", "q": "Speed of induction motor ___ with the increase of load.", "q_hi": "प्रेरण मोटर की गति भार के बढ़ने पर ___ होती है।"}
    ],
    "Section B": [
        {"q_type": "SA", "q": "Explain the terms: (a) Crawling (b) Cogging", "q_hi": "निम्न को समझाइये: (a) रिंगण (b) जकड़न"},
        {"q_type": "SA", "q": "What is the need of capacitor in single phase induction motor?", "q_hi": "संधारित्र की आवश्यकता एकल कला प्रेरण मोटर में क्यों पड़ती है?"}
    ]
}

section_meta = {
    "Section A": {"attempt_any": 4, "marks_per_q": 1},
    "Section B": {"attempt_any": 2, "marks_per_q": 5}
}

subject_info = {
    "exam_title": "EXAMINATION, 2025",
    "branch": "Electrical Engineering",
    "branch_code": "08",
    "sem": "V Sem. / III Year",
    "subject_name": "A.C. Machines",
    "subject_code": "085001",
    "duration": "2:30 Hrs.",
    "total_marks": 50
}

try:
    filename = exporter.export_paper_docx(sections_data, section_meta, subject_info)
    print(f"Success! Saved to {filename}")
except Exception as e:
    import traceback
    traceback.print_exc()
