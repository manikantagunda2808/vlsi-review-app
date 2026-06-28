import sys
from fastapi import APIRouter, HTTPException, Header
from backend.services.rules_service import load_raw_rules, save_rules, update_rule_severity, update_rule_check_type, delete_rule as delete_rule_from_file, bulk_add_rules
from backend.services.supabase_service import get_service_client
from backend.services.auth_utils import verify_token

router = APIRouter()

@router.get("/{review_type}")
def get_rules(review_type: str):
    try:
        rules = load_raw_rules(review_type)
        return rules
    except Exception as e:
        print(f"[rules] GET error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{review_type}")
def update_rules(review_type: str, data: dict, authorization: str = Header(...)):
    try:
        svc = get_service_client()

        payload = verify_token(authorization)
        profile = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()

        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can update rules")

        save_rules(review_type, data)
        print(f"[rules] {review_type} rules updated by {payload['user_id']}", file=sys.stderr)
        return {"message": f"{review_type} rules updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[rules] PUT error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{review_type}/bulk")
def bulk_add_rules_endpoint(review_type: str, body: dict, authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        profile = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can add bulk rules")

        new_rules = body.get("rules", [])
        if not new_rules or not isinstance(new_rules, list):
            raise HTTPException(status_code=400, detail="Request body must contain a 'rules' array")

        result = bulk_add_rules(review_type, new_rules)
        imported_count = len(result["imported"])
        errors_count = len(result["errors"])
        print(f"[rules] Bulk added {imported_count} rules to {review_type} by {payload['user_id']} ({errors_count} errors)", file=sys.stderr)
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[rules] POST bulk error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{review_type}/{rule_id}")
def patch_rule(review_type: str, rule_id: str, body: dict, authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        profile = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can update rules")

        updated = False
        messages = []

        new_severity = body.get("severity")
        if new_severity:
            if new_severity not in ("violation", "warning"):
                raise HTTPException(status_code=400, detail="Invalid severity")
            updated = update_rule_severity(review_type, rule_id, new_severity)
            messages.append(f"severity→{new_severity}")

        new_check_type = body.get("check_type")
        if new_check_type:
            if new_check_type not in ("static", "llm"):
                raise HTTPException(status_code=400, detail="Invalid check_type")
            updated = update_rule_check_type(review_type, rule_id, new_check_type) or updated
            messages.append(f"check_type→{new_check_type}")

        if not updated:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        msg = ", ".join(messages)
        print(f"[rules] {review_type}/{rule_id} {msg} by {payload['user_id']}", file=sys.stderr)
        return {"message": f"Rule {rule_id} updated: {msg}"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[rules] PATCH error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{review_type}/{rule_id}")
def delete_rule_endpoint(review_type: str, rule_id: str, authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        profile = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can delete rules")
        deleted = delete_rule_from_file(review_type, rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        print(f"[rules] {review_type}/{rule_id} deleted by {payload['user_id']}", file=sys.stderr)
        return {"message": f"Rule {rule_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[rules] DELETE error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))
