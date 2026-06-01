import secrets
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from backend.services.supabase_service import get_service_client
from backend.services.auth_utils import create_token, verify_token
from backend.services.email_service import send_otp_email

router = APIRouter()

otp_store = {}

def generate_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))

class SendOTPRequest(BaseModel):
    email: str
    name: str | None = None

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

def find_auth_user_id(email: str) -> str | None:
    svc = get_service_client()
    try:
        page = svc.auth.admin.list_users()
        for user in page:
            if user.email == email:
                return user.id
    except Exception:
        pass
    return None

def create_auth_user(email: str) -> str:
    svc = get_service_client()
    password = secrets.token_urlsafe(16)
    result = svc.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    return result.user.id

@router.post("/send-otp")
def send_otp(req: SendOTPRequest):
    if not req.email.lower().endswith("@vaaluka.com"):
        raise HTTPException(status_code=400, detail="Only @vaaluka.com emails allowed")

    email = req.email.lower()
    code = generate_otp()

    otp_store[email] = {
        "otp": code,
        "name": req.name.strip() if req.name else None,
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }

    send_otp_email(email, code)

    return {"message": "OTP sent to your email"}

@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    if not req.email.lower().endswith("@vaaluka.com"):
        raise HTTPException(status_code=400, detail="Only @vaaluka.com emails allowed")

    email = req.email.lower()
    entry = otp_store.pop(email, None)

    if not entry:
        raise HTTPException(status_code=400, detail="No OTP requested. Please send OTP first.")
    if entry["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired. Request a new one.")
    if entry["otp"] != req.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP. Try again.")

    svc = get_service_client()

    user_id = find_auth_user_id(email)

    if user_id:
        profile_resp = svc.table("profiles").select("*").eq("id", user_id).execute()
        has_profile = bool(profile_resp.data)
    else:
        has_profile = False
        if not entry["name"]:
            raise HTTPException(status_code=400, detail="Email not registered. Please sign up first.")
        user_id = create_auth_user(email)

    if not has_profile:
        svc.table("profiles").insert({
            "id": user_id,
            "name": entry["name"],
            "role": "junior"
        }).execute()

    profile = svc.table("profiles").select("*").eq("id", user_id).single().execute()
    token = create_token(user_id, profile.data["role"])

    return {
        "access_token": token,
        "user_id": user_id,
        "name": profile.data["name"],
        "role": profile.data["role"]
    }

@router.get("/me")
def get_me(authorization: str = Header(...)):
    payload = verify_token(authorization)
    svc = get_service_client()
    profile = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
    return {
        "user_id": profile.data["id"],
        "name": profile.data["name"],
        "role": profile.data["role"]
    }

@router.get("/users")
def list_users(authorization: str = Header(...)):
    payload = verify_token(authorization)
    svc = get_service_client()

    caller = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
    if caller.data["role"] != "senior":
        raise HTTPException(status_code=403, detail="Only seniors can manage users")

    profiles = svc.table("profiles").select("*").execute()
    auth_page = svc.auth.admin.list_users()
    auth_map = {u.id: u.email for u in auth_page}

    result = []
    for p in profiles.data:
        result.append({
            "user_id": p["id"],
            "name": p["name"],
            "role": p["role"],
            "email": auth_map.get(p["id"], "")
        })

    return result

@router.delete("/users/{user_id}")
def delete_user(user_id: str, authorization: str = Header(...)):
    payload = verify_token(authorization)
    svc = get_service_client()

    if payload["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    caller = svc.table("profiles").select("*").eq("id", payload["user_id"]).single().execute()
    if caller.data["role"] != "senior":
        raise HTTPException(status_code=403, detail="Only seniors can manage users")

    svc.table("reviews").delete().eq("user_id", user_id).execute()
    svc.table("profiles").delete().eq("id", user_id).execute()
    svc.auth.admin.delete_user(user_id)

    return {"message": "User deleted successfully"}
