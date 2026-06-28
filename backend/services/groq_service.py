import json
import hashlib
import re
import logging
from groq import Groq
from groq import APIError as GroqAPIError
from backend.config import GROQ_API_KEY
from backend.services.static_checks import run_static_checks
from backend.services.supabase_service import get_service_client

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)
BATCH_SIZE = 8
MAX_RETRIES_PER_BATCH = 3


def _cache_key(code: str, rules: str, review_type: str) -> str:
    raw = f"{code}:::{rules}:::{review_type}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _check_cache(key: str) -> dict | None:
    try:
        svc = get_service_client()
        result = svc.table("review_cache").select("result").eq("hash", key).maybe_single().execute()
        if result.data:
            return result.data["result"]
    except Exception:
        pass
    return None


def _write_cache(key: str, result: dict):
    try:
        svc = get_service_client()
        svc.table("review_cache").upsert({"hash": key, "result": result}, on_conflict="hash").execute()
    except Exception:
        pass


def _parse_rule_ids(rules_text: str) -> list[dict]:
    rules = []
    for line in rules_text.strip().split("\n"):
        line = line.strip()
        m = re.match(r"^\- \[(\w+)\] \((\w+)\) (.+)$", line)
        if m:
            rules.append({
                "id": m.group(1),
                "severity": m.group(2).lower(),
                "text": m.group(3)
            })
    return rules


def _build_batch_prompt(batch: list[dict], review_type: str, code: str) -> str:
    rules_lines = "\n".join(
        f"- [{r['id']}] ({r['severity'].upper()}) {r['text']}" for r in batch
    )
    rule_ids_json = ", ".join(f'"{r["id"]}": {{...}}' for r in batch)
    return f"""You are a strict VLSI code reviewer for {review_type.upper()} code.
Review the submitted code against the specific rules below.

For each rule, determine: does the code PASS or VIOLATE it?
If the issue is minor (a warning), set verdict to "warning".

Return ONLY this JSON (no extra text):
{{
  "verdicts": {{{rule_ids_json}}},
  "summary": "1-2 sentence batch summary"
}}

Rules:
{rules_lines}

Code to review:
{code}"""


def _review_batch(code: str, batch: list[dict], review_type: str) -> tuple[dict, str]:
    prompt = _build_batch_prompt(batch, review_type, code)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a strict VLSI code reviewer. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=1024
        )

        raw = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        clean = raw.strip().replace("```json", "").replace("```", "").strip()

        if finish_reason == "length":
            raise ValueError("Response truncated (finish_reason=length)")

        parsed = json.loads(clean)
        verdicts = parsed.get("verdicts", {})
        summary = parsed.get("summary", "")
        return verdicts, summary
    except GroqAPIError as e:
        logger.warning(f"Groq API error (batch of {len(batch)} rules): {e}")
        return {}, "LLM review unavailable (API error)"
    except Exception as e:
        logger.warning(f"Unexpected error in LLM batch: {e}")
        return {}, "LLM review unavailable (processing error)"


def review_code(code: str, rules: str, review_type: str) -> dict:
    # 1. Cache check — identical resubmission returns cached result instantly
    key = _cache_key(code, rules, review_type)
    cached = _check_cache(key)
    if cached is not None:
        return cached

    # 2. Parse all rule IDs from the rules text
    all_rules = _parse_rule_ids(rules)

    # 3. Run static checks — deterministic, zero variance
    static_verdicts = run_static_checks(code, review_type)
    static_done = set(static_verdicts.keys())

    # 4. Rules the LLM can't reliably evaluate — send to needs_manual_review
    SKIP_LLM_IDS = {"RTL007"}
    skip_llm = {r["id"] for r in all_rules if r["id"] in SKIP_LLM_IDS}

    # 5. LLM-only rules (static didn't cover and not in skip list)
    llm_rules = [r for r in all_rules if r["id"] not in static_done and r["id"] not in skip_llm]

    # 6. Batch-process LLM rules with retry for missing verdicts
    llm_verdicts = {}
    unchecked = set()

    for i in range(0, len(llm_rules), BATCH_SIZE):
        batch = llm_rules[i:i + BATCH_SIZE]
        batch_ids = {r["id"] for r in batch}
        merged = {}

        for attempt in range(1, MAX_RETRIES_PER_BATCH + 1):
            missing = batch_ids - set(merged.keys())
            if not missing:
                break
            missing_batch = [r for r in batch if r["id"] in missing]
            try:
                verdicts, _ = _review_batch(code, missing_batch, review_type)
                if verdicts:
                    merged.update(verdicts)
            except (json.JSONDecodeError, ValueError, KeyError):
                if attempt == MAX_RETRIES_PER_BATCH:
                    unchecked.update(missing)

        still_missing = batch_ids - set(merged.keys())
        unchecked.update(still_missing)
        llm_verdicts.update(merged)

    # 6. Merge static + LLM verdicts into violations / warnings / passed
    violations = []
    warnings = []
    passed = []
    needs_manual = sorted(unchecked) if unchecked else []

    for r in all_rules:
        rid = r["id"]
        rtext = r["text"]

        if rid in static_verdicts:
            sv = static_verdicts[rid]
            if sv["result"] == "fail":
                entry = {
                    "rule_id": rid,
                    "rule": rtext,
                    "message": sv["evidence"],
                    "file": "submitted code",
                    "line": str(sv.get("line", "N/A"))
                }
                if sv.get("severity") == "warning":
                    warnings.append(entry)
                else:
                    violations.append(entry)
            else:
                passed.append(f"{rid} — {rtext}: {sv['evidence']}")

        elif rid in llm_verdicts:
            lv = llm_verdicts[rid]
            verdict = lv.get("verdict", "pass")
            msg = lv.get("message", "")
            entry = {
                "rule_id": rid,
                "rule": rtext,
                "message": msg,
                "file": lv.get("file", "submitted code"),
                "line": str(lv.get("line", "N/A"))
            }
            if verdict == "violation":
                violations.append(entry)
            elif verdict == "warning":
                warnings.append(entry)
            else:
                passed.append(f"{rid} — {rtext}: {msg}")

        elif rid not in needs_manual:
            needs_manual.append(rid)

    # 7. Compute score: (rules passed / total rules checked) * 10
    total_checked = len(all_rules) - len(needs_manual)
    score = round((len(passed) / total_checked) * 10, 1) if total_checked > 0 else 0

    # 8. Build summary
    v_count = len(violations)
    w_count = len(warnings)
    p_count = len(passed)
    parts = [f"{v_count} violation(s), {w_count} warning(s), {p_count} passed"]
    if needs_manual:
        parts.append(f"Rules unchecked: {', '.join(needs_manual)}")
    summary = "Review complete. " + ". ".join(parts)

    result = {
        "score": score,
        "violations": violations,
        "warnings": warnings,
        "passed": passed,
        "summary": summary.strip(),
        "needs_manual_review": needs_manual
    }

    # 9. Write to cache and return
    _write_cache(key, result)
    return result
