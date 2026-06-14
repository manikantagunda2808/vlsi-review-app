import json
import urllib.request
from urllib.error import HTTPError
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from backend.config import SUPABASE_URL, SUPABASE_ANON_KEY
from backend.services.supabase_service import get_service_client
from backend.services.auth_utils import create_token, verify_token

router = APIRouter()

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/signup")
def signup(req: SignupRequest):
    if not req.email.lower().endswith("@vaaluka.com"):
        raise HTTPException(status_code=400, detail="Only @vaaluka.com emails allowed")

    email = req.email.lower()
    svc = get_service_client()

    try:
        result = svc.auth.admin.create_user({
            "email": email,
            "password": req.password,
            "email_confirm": True
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

    user_id = result.user.id

    svc.table("profiles").insert({
        "id": user_id,
        "name": req.name.strip(),
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

@router.post("/login")
def login(req: LoginRequest):
    if not req.email.lower().endswith("@vaaluka.com"):
        raise HTTPException(status_code=400, detail="Only @vaaluka.com emails allowed")

    email = req.email.lower()

    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    payload = json.dumps({"email": email, "password": req.password}).encode()

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        response = urllib.request.urlopen(request)
        body = json.loads(response.read().decode())
        user_id = body["user"]["id"]
    except HTTPError as e:
        if e.code == 400:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        raise HTTPException(status_code=400, detail="Login failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")

    svc = get_service_client()
    profile = svc.table("profiles").select("*").eq("id", user_id).single().execute()

    if not profile.data:
        raise HTTPException(status_code=400, detail="Profile not found. Please sign up.")

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