import os
from groq import Groq
import json
import httpx
import google.generativeai as genai
from . import vector_db

client = Groq(api_key=os.getenv("GROQ_API_KEY", "default-test-key"))
USE_OLLAMA = os.getenv("USE_OLLAMA", "True").lower() in ["true", "1", "yes"]
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Initialize Gemini
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def _call_llm(prompt: str, provider: str = None, model: str = None) -> str:
    """Wrapper to handle Groq vs Ollama seamlessly, with optional overrides."""
    active_provider = provider or ("ollama" if USE_OLLAMA else "groq")
    active_model = model or (OLLAMA_MODEL if active_provider == "ollama" else "llama-3.1-8b-instant")

    if active_provider == "ollama":
        response = httpx.post(
            "http://localhost:11434/api/chat",
            json={
                "model": active_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "options": {
                    "num_ctx": 2048,
                    "num_predict": 1024
                }
            },
            timeout=900.0
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    elif active_provider == "gemini":
        if not GEMINI_KEY:
            raise ValueError("GEMINI_API_KEY is not configured in .env")
        # Use selected model or default to flash
        gemini_model_name = active_model or "gemini-1.5-flash"
        try:
            model_instance = genai.GenerativeModel(gemini_model_name)
            response = model_instance.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=1024,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [DEBUG] Gemini API Error with model '{gemini_model_name}': {e}")
            raise e
    else:
        if client.api_key == "default-test-key":
            raise ValueError("GROQ_API_KEY is not configured in .env")
        response = client.chat.completions.create(
            model=active_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content

def get_rag_query_for_type(q_type: str) -> str:
    """Returns a synthetic search query to find the best chunks for a specific question type."""
    if q_type == "MCQ":
        return "important facts, definitions, core concepts, classifications, and principles"
    elif q_type == "FIB":
        return "key terms, definitions, specific dates, names, or factual statements"
    elif q_type == "T/F":
        return "absolute facts, true or false statements, definitive characteristics"
    elif q_type in ["SA", "LA"]:
        return "detailed explanations, mechanisms, processes, comparisons, and full descriptions"
    elif q_type == "CASE":
        return "real-world scenarios, applications, examples, case studies, and problems"
    return "key concepts and important information"

def generate_questions_rag(subject_id: int, types_config: list, difficulty: str = "Medium", provider: str = "groq", model: str = "llama-3.1-8b-instant") -> list:
    """
    Generates structured bilingual questions using optimized RAG context.
    Combines chunks into a single request per question type to save tokens.
    """
    all_qs = []
    import datetime
    import time
    
    MAX_BATCH_SIZE = 5
    SLEEP_TIME_SECONDS = 65

    # 1. Build a flat queue of manageable tasks to bypass rate limits
    tasks = []
    for tc in types_config:
        qt = tc.get("q_type", "Mixed")
        nq = int(tc.get("num_q", 0))
        
        while nq > 0:
            batch_q = min(nq, MAX_BATCH_SIZE)
            tasks.append({"q_type": qt, "num_q": batch_q})
            nq -= batch_q

    # 2. Process tasks sequentially
    for task_index, task in enumerate(tasks):
        qt = task["q_type"]
        target_q = task["num_q"]
        remaining_target = target_q
        MAX_RETRIES = 2
        
        synthetic_query = get_rag_query_for_type(qt)
        # Keep chunks low (3) to prevent hitting Groq's strict 6000 Tokens-Per-Minute limit
        n_chunks = 3 if target_q <= 5 else 5
        chunks = vector_db.retrieve_context(subject_id, synthetic_query, n_results=n_chunks)
        
        combined_context = "\n---\n".join(chunks) if chunks else "No specific context found."
        
        for attempt in range(MAX_RETRIES):
            if remaining_target <= 0:
                break
                
            if qt == "Mixed":
                counts = {"MCQ": 0, "FIB": 0, "T/F": 0, "SA": 0}
                types = list(counts.keys())
                for i in range(remaining_target):
                    counts[types[i % 4]] += 1
                mixed_instruction = f"You MUST generate EXACTLY {remaining_target} questions with this EXACT distribution: {counts['MCQ']} MCQs, {counts['FIB']} Fill in the Blanks, {counts['T/F']} True/False, and {counts['SA']} Short Answers."
                format_example = """{
  "questions": [
    { "q_type": "MCQ", "question_en": "...", "question_hi": "...", "answer_en": "...", "answer_hi": "...", "options": {"A": "Apple / सेब", "B": "Mango / आम", "C": "Banana / केला", "D": "Grape / अंगूर"}, "correct_option": "A" },
    { "q_type": "FIB", "question_en": "...", "question_hi": "...", "answer_en": "...", "answer_hi": "...", "options": null, "correct_option": null }
  ]
}"""
            else:
                mixed_instruction = ""
                format_example = f"""{{
  "questions": [
    {{ "q_type": "{qt}", "question_en": "...", "question_hi": "...", "answer_en": "...", "answer_hi": "...", "options": {{"A": "Apple / सेब", "B": "Mango / आम", "C": "Banana / केला", "D": "Grape / अंगूर"}}, "correct_option": "A" }}
  ]
}}"""

            prompt = f"""
ACT as a bilingual exam expert. Generate {remaining_target} questions in English & Hindi from the context.
DIFFICULTY: {difficulty}

CONTEXT:
{combined_context}

RULES:
1. Output ONLY a valid JSON object matching the exact schema below.
2. {mixed_instruction}
3. FORMAT EXAMPLE:
{format_example}
4. CRITICAL MCQ RULE: For MCQs, "options" MUST be a dictionary with keys A, B, C, D. Every option value MUST be bilingual using a slash (e.g. "English / Hindi"). English-only options are FORBIDDEN.
5. DIVERSITY RULE: The provided context contains distinct excerpts separated by '---'. You MUST generate questions that draw evenly from ALL the different excerpts. Do not focus all questions on just one topic or excerpt.
6. If the question is NOT an MCQ, set "options" to null.
7. TRANSLATION QUALITY: The Hindi translation MUST be natural, grammatically correct, and use appropriate academic vocabulary. Translate the entire sentence contextually—do NOT do a literal, word-by-word translation.
"""
            try:
                print(f"[{datetime.datetime.now()}]   -> Generating {remaining_target} {qt} questions using RAG (Task {task_index+1}/{len(tasks)}, Attempt {attempt+1}/{MAX_RETRIES})...")
                content = _call_llm(prompt, provider=provider, model=model)
                
                content = content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                content = content.strip()
                
                try:
                    data = json.loads(content)
                except:
                    if not content.endswith("}"):
                        content += "}"
                    if not content.endswith("]}"):
                        content += "]}"
                    data = json.loads(content)

                chunk_qs = []
                if "questions" in data and isinstance(data["questions"], list):
                    chunk_qs = data["questions"]
                elif isinstance(data, list):
                    chunk_qs = data
                    
                valid_qs = [q for q in chunk_qs if isinstance(q, dict)]
                
                for q in valid_qs:
                    actual_qt = q.get("q_type", qt)
                    
                    if isinstance(q.get("options"), list):
                        opts = q["options"]
                        keys = ["A", "B", "C", "D"]
                        q["options"] = {
                            keys[i]: opts[i] if "/" in str(opts[i]) else f"{opts[i]} / [Hindi Missing]" 
                            for i in range(min(len(opts), 4))
                        }
                        
                    if (actual_qt == qt or qt == "Mixed") and remaining_target > 0:
                        all_qs.append(q)
                        remaining_target -= 1
                
                print(f"[{datetime.datetime.now()}]   -> Successfully parsed {len(valid_qs)} questions. Remaining target for this task: {remaining_target}")
                
            except Exception as e:
                print(f"[{datetime.datetime.now()}]   -> Error processing chunk with LLM: {str(e)}")
                continue

        # 3. Rate Limit Sleep Logic
        if task_index < len(tasks) - 1:
            if provider.lower() == "groq":
                print(f"[{datetime.datetime.now()}] Sleeping for {SLEEP_TIME_SECONDS} seconds to clear Groq API rate limits...")
                time.sleep(SLEEP_TIME_SECONDS)
            else:
                print(f"[{datetime.datetime.now()}] Sleeping for 5 seconds between batches...")
                time.sleep(5)

    if not all_qs:
        raise ValueError("Token Limit Reached or Complete failure. No LLM questions generated successfully.")
        
    return all_qs