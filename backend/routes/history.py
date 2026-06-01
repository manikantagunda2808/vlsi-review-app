from fastapi import APIRouter, HTTPException, Header
from backend.services.supabase_service import get_service_client
from backend.services.auth_utils import verify_token

router = APIRouter()

@router.get("/my")
def my_history(authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        user_id = payload["user_id"]

        result = svc.table("reviews")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()

        return result.data

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/all")
def all_history(authorization: str = Header(...)):
    try:
        svc = get_service_client()

        payload = verify_token(authorization)
        user_id = payload["user_id"]

        profile = svc.table("profiles")\
            .select("*")\
            .eq("id", user_id)\
            .single()\
            .execute()

        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can view all reviews")

        result = svc.table("reviews")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
