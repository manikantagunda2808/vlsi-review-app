import sys
import yaml
from backend.services.supabase_service import get_service_client

RULES_DIR = "rules"


def _load_from_supabase(review_type: str) -> dict | None:
    try:
        svc = get_service_client()
        result = svc.table("global_rules").select("rules").eq("review_type", review_type).execute()
        if result.data and len(result.data) > 0:
            return {"rules": result.data[0]["rules"]}
    except Exception as e:
        print(f"[rules] Supabase read failed for {review_type}: {e}", file=sys.stderr)
    return None


def _load_from_yaml(review_type: str) -> dict | None:
    try:
        path = f"{RULES_DIR}/{review_type}_rules.yaml"
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _save_to_supabase(review_type: str, data: dict):
    svc = get_service_client()
    svc.table("global_rules").upsert({
        "review_type": review_type,
        "rules": data["rules"]
    }, on_conflict="review_type").execute()


def _save_to_yaml(review_type: str, data: dict):
    path = f"{RULES_DIR}/{review_type}_rules.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True)


def _seed_supabase_from_yaml(review_type: str):
    yaml_data = _load_from_yaml(review_type)
    if yaml_data:
        try:
            _save_to_supabase(review_type, yaml_data)
            print(f"[rules] Seeded {review_type} rules from YAML into Supabase", file=sys.stderr)
        except Exception as e:
            print(f"[rules] Failed to seed {review_type}: {e}", file=sys.stderr)


def load_rules(review_type: str) -> str:
    data = _load_from_supabase(review_type) or _load_from_yaml(review_type)
    if data is None:
        return ""
    rules_text = ""
    for r in data["rules"]:
        rules_text += f"- [{r['id']}] ({r['severity'].upper()}) {r['rule']}\n"
    return rules_text


def load_raw_rules(review_type: str) -> dict:
    yaml_data = _load_from_yaml(review_type)
    if yaml_data is not None:
        _seed_supabase_from_yaml(review_type)
        return yaml_data
    data = _load_from_supabase(review_type)
    if data is not None:
        return data
    return {"rules": []}


def save_rules(review_type: str, data: dict):
    _save_to_yaml(review_type, data)
    _save_to_supabase(review_type, data)


def _get_prefix(review_type: str) -> str:
    prefix_map = {
        "rtl": "RTL",
        "sv": "SV",
        "uvm": "UVM",
        "verilog_tb": "TB",
    }
    return prefix_map.get(review_type, review_type.upper())


def _max_rule_number(existing_rules: list, prefix: str) -> int:
    max_num = 0
    for r in existing_rules:
        rid = r.get("id", "")
        if rid.startswith(prefix):
            try:
                num = int(rid[len(prefix):])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return max_num


def bulk_add_rules(review_type: str, new_rules_data: list) -> dict:
    prefix = _get_prefix(review_type)
    data = load_raw_rules(review_type)
    existing = data["rules"]

    next_num = _max_rule_number(existing, prefix) + 1

    imported = []
    errors = []
    for i, item in enumerate(new_rules_data):
        severity = item.get("severity")
        rule = item.get("rule", "").strip()
        if severity not in ("violation", "warning"):
            errors.append({"index": i, "reason": f"Invalid severity '{severity}'. Must be 'violation' or 'warning'."})
            continue
        if not rule:
            errors.append({"index": i, "reason": "Rule text cannot be empty."})
            continue
        rule_id = f"{prefix}{next_num:03d}"
        next_num += 1
        imported.append({"id": rule_id, "severity": severity, "rule": rule, "check_type": "llm"})

    data["rules"] = existing + imported
    save_rules(review_type, data)

    return {"imported": imported, "errors": errors}


def update_rule_severity(review_type: str, rule_id: str, new_severity: str) -> bool:
    data = load_raw_rules(review_type)
    for rule in data["rules"]:
        if rule["id"] == rule_id:
            rule["severity"] = new_severity
            save_rules(review_type, data)
            return True
    return False


def update_rule_check_type(review_type: str, rule_id: str, new_check_type: str) -> bool:
    data = load_raw_rules(review_type)
    for rule in data["rules"]:
        if rule["id"] == rule_id:
            rule["check_type"] = new_check_type
            save_rules(review_type, data)
            return True
    return False


def delete_rule(review_type: str, rule_id: str) -> bool:
    data = load_raw_rules(review_type)
    initial_len = len(data["rules"])
    data["rules"] = [r for r in data["rules"] if r["id"] != rule_id]
    if len(data["rules"]) == initial_len:
        return False
    prefix_map = {
        "rtl": "RTL",
        "sv": "SV",
        "uvm": "UVM",
        "verilog_tb": "TB",
    }
    prefix = prefix_map.get(review_type, review_type.upper())
    for i, rule in enumerate(data["rules"], start=1):
        rule["id"] = f"{prefix}{i:03d}"
    save_rules(review_type, data)
    return True
