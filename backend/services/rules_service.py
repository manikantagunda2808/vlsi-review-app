import yaml

def load_rules(review_type: str) -> str:
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    rules_text = ""
    for r in data["rules"]:
        rules_text += f"- [{r['id']}] ({r['severity'].upper()}) {r['rule']}\n"
    return rules_text

def load_raw_rules(review_type: str) -> dict:
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

def save_rules(review_type: str, data: dict):
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True)

def update_rule_severity(review_type: str, rule_id: str, new_severity: str) -> bool:
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    for rule in data["rules"]:
        if rule["id"] == rule_id:
            rule["severity"] = new_severity
            with open(path, "w") as f:
                yaml.dump(data, f, allow_unicode=True)
            return True
    return False

def delete_rule(review_type: str, rule_id: str) -> bool:
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    initial_len = len(data["rules"])
    data["rules"] = [r for r in data["rules"] if r["id"] != rule_id]
    if len(data["rules"]) == initial_len:
        return False
    # Map review_type to rule ID prefix
    prefix_map = {
        "rtl": "RTL",
        "sv": "SV",
        "uvm": "UVM",
        "verilog_tb": "TB",
    }
    prefix = prefix_map.get(review_type, review_type.upper())
    for i, rule in enumerate(data["rules"], start=1):
        rule["id"] = f"{prefix}{i:03d}"
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True)
    return True
