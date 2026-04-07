import os
from groq import Groq
import json
import httpx

client = Groq(api_key=os.getenv("GROQ_API_KEY", "default-test-key"))
USE_OLLAMA = os.getenv("USE_OLLAMA", "False").lower() in ["true", "1", "yes"]
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

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
                    "num_ctx": 4096,
                    "num_predict": 2048
                }
            },
            timeout=600.0
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    else:
        response = client.chat.completions.create(
            model=active_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=6000,
        )
        return response.choices[0].message.content

def generate_questions(subject_context: str, types_config: list, difficulty: str = "Medium", provider: str = None, model: str = None) -> list:
    """
    Generates structured bilingual questions using an iterative chunking approach over the full context.
    Supports dynamic provider/model selection, difficulty, and exact question quantities per type.
    """
    # 1. Chunking Logic
    chunk_size = 4000
    chunks = [subject_context[i:i+chunk_size] for i in range(0, len(subject_context), chunk_size)]
    if not chunks:
        chunks = [""] # Fallback for completely empty PDF
        
    num_chunks = len(chunks)
    all_qs = []
    
    remaining_targets = {}
    for tc in types_config:
        qt = tc.get("q_type", "Mixed")
        nq = int(tc.get("num_q", 0))
        if nq > 0:
            remaining_targets[qt] = remaining_targets.get(qt, 0) + nq
            
    for i, chunk in enumerate(chunks):
        chunk_types = []
        chunks_left = num_chunks - i
        
        for qt, nq in remaining_targets.items():
            if nq <= 0: continue
            
            base_q = nq // chunks_left
            rem_q = nq % chunks_left
            target_q = base_q + (1 if rem_q > 0 else 0)
            target_q = min(target_q, 15) # Avoid breaking LLM output limits
            
            if target_q > 0:
                chunk_types.append(f"- {target_q} {qt} questions")
                
        if not chunk_types:
            continue
            
        requested_types_str = "\n".join(chunk_types)
        
        prompt = f"""
You are an expert educational content creator. Based on the provided context chunk, generate EXACTLY these quantities of questions:
{requested_types_str}

Requested Difficulty: {difficulty} (Ensure the complexity of the questions aligns with this level).

### SUPPORTED TYPES:
- MCQ: Multiple Choice Question (Include 4 options: A, B, C, D)
- FIB: Fill in the Blanks (Show as sentence with '___')
- T/F: True or False Questions
- SA: Short Answer (Detailed 1-2 sentence answers)
- LA: Long Answer (Comprehensive explanations)
- CASE: Case-based/Scenario Questions (Provide a small context first)

### STRICT RULES:
1. CONTEXT-BOUND GENERATION:
- Use ONLY the provided content.
- Do NOT use any external knowledge.
- If information is insufficient for a question, SKIP that question.

2. NO HALLUCINATION:
- Do NOT guess or fabricate any information.
- Every question MUST be directly supported by the content.

3. CONTENT FILTERING:
- DO NOT create questions about:
  • Author names
  • Book titles
  • Page numbers or metadata
- Focus ONLY on concepts, facts, and applications.

4. UNIQUENESS:
- Each question MUST test a different concept.
- No duplicate or similar questions.
- Avoid rewording the same idea.

5. STRICT BILINGUAL OUTPUT:
- Every sentence MUST be written in BOTH:
  (a) English (EN)
  (b) Hindi (HI)
- Hindi MUST be in Devanagari script.
- Each English line MUST be immediately followed by its Hindi translation.
- NEVER skip either language.
- NEVER output any third language (NO Spanish, French, Hinglish, etc.).

Correct format:
Question in English.
प्रश्न हिंदी में।

6. MCQ OPTIONS FORMAT ENFORCEMENT (STRICT)

You MUST generate ALL MCQ options in a strictly bilingual format.

MANDATORY FORMAT:
Each option MUST be written in ONE line as:
English / Hindi

STRICT RULES:
1. Use EXACTLY one forward slash "/"
2. English text MUST appear BEFORE "/"
3. Hindi text MUST appear AFTER "/"
4. Hindi MUST be in Devanagari script
5. Both English and Hindi MUST have the SAME meaning

EXAMPLE (CORRECT):
A. Apple / सेब
B. Mango / आम
C. Banana / केला
D. Orange / संतरा

FORBIDDEN OUTPUT (AUTO-INVALID)

- Missing Hindi:
  Apple

- Missing English:
  सेब

- Wrong separator:
  Apple - सेब
  Apple | सेब

- Multiple slashes:
  Apple / सेब / fruit

- Meaning mismatch:
  Apple / आम

- Mixed compliance:
  (Some options bilingual, others not)

CRITICAL ENFORCEMENT

- ALL options MUST be correctly formatted.
- If EVEN ONE option violates the rule:
  → The ENTIRE MCQ is INVALID
  → You MUST regenerate ALL options

SELF-VALIDATION (MANDATORY)

Before output, you MUST verify for EACH option:
- Contains exactly one "/"
- English before "/"
- Hindi after "/"
- Correct translation   

If ANY check fails:
- REGENERATE internally
- DO NOT output invalid content

FINAL INSTRUCTION

Do NOT output partially correct MCQs.
ONLY output when ALL options are 100% compliant.

Correct example:
A. Apple / सेब

Invalid formats (STRICTLY FORBIDDEN):
- Apple
- सेब
- Apple - सेब
- Apple / Mango

7. TRUE/FALSE FORMAT (MANDATORY):

- A True/False question MUST be a factual, testable statement.
- It MUST test a concept, definition, property, or principle — NOT:
"Chapter names"
"Topic listings"
"Meta descriptions"
"is covered in" type sentences

- The statement MUST allow clear evaluation as True or False.

GOOD examples:
"Light travels faster in vacuum than in optical fibre."
"Optical fibres use total internal reflection to transmit light."

BAD examples (STRICTLY FORBIDDEN):
"Optical Fibre is covered in this chapter."
"This topic belongs to physics."

- EVERY T/F question MUST end EXACTLY with:
  True / False:
  सही / गलत:

- If the statement is not clearly testable → REGENERATE.
- Every True/False question MUST end EXACTLY with:

True / False:
सही / गलत:

EXAMPLE: The Sun rises in the East. True / False:
सूर्य पूर्व दिशा में उगता है। सही / गलत:

- These MUST appear at the END.
- NO variations allowed.


### JSON FORMAT:
Return ONLY a valid JSON object with a "questions" key:
{{
    "questions": [
        {{
            "q_type": "MCQ",
            "question_en": "... (in English) ...",
            "question_hi": "... (in Hindi) ...",
            "options": {{"A": "... (English) / ... (Hindi)", "B": "... (English) / ... (Hindi)", "C": "... (English) / ... (Hindi)", "D": "... (English) / ... (Hindi)"}},
            "answer_en": "... (in English) ...",
            "answer_hi": "... (in Hindi) ..."
        }},
        {{
            "q_type": "FIB",
            "question_en": "... ___ ... (in English) ...",
            "question_hi": "... ___ ... (in Hindi) ...",
            "options": null,
            "answer_en": "... (in English) ...",
            "answer_hi": "... (in Hindi) ..."
        }},
        {{
            "q_type": "T/F",
            "question_en": "... (in English) ...",
            "question_hi": "... (in Hindi) ...",
            "options": null,
            "answer_en": "... (in English) ...",
            "answer_hi": "... (in Hindi) ..."
        }}
    ]
}}

Context Chunk:
{chunk}
"""
        try:
            content = _call_llm(prompt, provider=provider, model=model)
            
            # Clean markdown backticks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                data = json.loads(content)
            except json.decoder.JSONDecodeError as decode_err:
                # Salvage incomplete JSON if model token limit reached
                last_brace = content.rfind("}")
                if last_brace != -1:
                    salvaged = content[:last_brace+1] + "]}"
                    try:
                        data = json.loads(salvaged)
                    except Exception:
                        print(f"Chunk {i+1} parsing failed. Error: {decode_err}")
                        continue
                else:
                    print(f"Chunk {i+1} Decode Error: {decode_err}")
                    continue

            # Extract lists
            chunk_qs = []
            if "questions" in data and isinstance(data["questions"], list):
                chunk_qs = data["questions"]
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        chunk_qs = v
                        break
                        
            # Filter safely
            valid_qs = [q for q in chunk_qs if isinstance(q, dict)]
            
            all_qs.extend(valid_qs)
            
            # Dynamically deduct successfully extracted questions to fix under-generation
            for q in valid_qs:
                qt = q.get("q_type", "Mixed")
                if qt in remaining_targets:
                    remaining_targets[qt] -= 1
                
        except Exception as e:
            print(f"Error processing chunk {i+1} with LLM: {str(e)}")
            continue

    if not all_qs:
        raise ValueError("Complete failure across all PDF chunks. No LLM questions generated successfully.")
        
    return all_qs
