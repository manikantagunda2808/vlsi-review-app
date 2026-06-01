import json
from groq import Groq
from backend.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def review_code(code: str, rules: str, review_type: str) -> dict:
    system_prompt = f"""You are a strict VLSI code reviewer for {review_type.upper()} code.
Review the submitted code against the rules below and return ONLY a JSON object.

Rules:
{rules}

Return this exact JSON format:
{{
  "score": <number 0-10>,
  "violations": [
    {{"rule_id": "XXXXX", "message": "...", "file": "submitted code", "line": "approx line or N/A"}}
  ],
  "warnings": [
    {{"rule_id": "XXXXX", "message": "...", "file": "submitted code", "line": "approx line or N/A"}}
  ],
  "passed": ["brief description of what passed"],
  "summary": "2-3 sentence overall summary"
}}

Be specific. Reference actual code. Do not add any text outside the JSON."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Review this code:\n{code}"}
        ],
        temperature=0.1
    )

    raw = response.choices[0].message.content
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean)
