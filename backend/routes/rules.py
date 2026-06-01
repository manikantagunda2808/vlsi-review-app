import sys
from fastapi import APIRouter, HTTPException, Header
from backend.services.rules_service import load_raw_rules, save_rules, update_rule_severity, delete_rule as delete_rule_from_file
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

@router.patch("/{review_type}/{rule_id}")
def patch_rule(review_type: str, rule_id: str, body: dict, authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        profile = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can update rules")

        new_severity = body.get("severity")
        if new_severity not in ("violation", "warning"):
            raise HTTPException(status_code=400, detail="Invalid severity")

        updated = update_rule_severity(review_type, rule_id, new_severity)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        print(f"[rules] {review_type}/{rule_id} severity→{new_severity} by {payload['user_id']}", file=sys.stderr)
        return {"message": f"Rule {rule_id} updated to {new_severity}"}

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
