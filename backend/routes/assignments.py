from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from backend.services.supabase_service import get_service_client
from backend.services.auth_utils import verify_token

router = APIRouter()

class AssignmentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    rtl_rules: Optional[list] = []
    sv_rules: Optional[list] = []
    uvm_rules: Optional[list] = []
    verilog_tb_rules: Optional[list] = []

def verify_senior(authorization: str):
    svc = get_service_client()
    payload = verify_token(authorization)
    user_id = payload["user_id"]
    profile = svc.table("profiles").select("*").eq("id", user_id).single().execute()
    if profile.data["role"] != "senior":
        raise HTTPException(status_code=403, detail="Only seniors allowed")
    return user_id

@router.get("/")
def get_assignments():
    try:
        svc = get_service_client()
        result = svc.table("assignments").select("*").order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/")
def create_assignment(req: AssignmentCreate, authorization: str = Header(...)):
    try:
        user_id = verify_senior(authorization)
        svc = get_service_client()
        result = svc.table("assignments").insert({
            "name": req.name,
            "description": req.description,
            "rtl_rules": req.rtl_rules,
            "sv_rules": req.sv_rules,
            "uvm_rules": req.uvm_rules,
            "verilog_tb_rules": req.verilog_tb_rules,
            "created_by": user_id
        }).execute()
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{assignment_id}")
def update_assignment(assignment_id: str, req: AssignmentCreate, authorization: str = Header(...)):
    try:
        verify_senior(authorization)
        svc = get_service_client()
        result = svc.table("assignments").update({
            "name": req.name,
            "description": req.description,
            "rtl_rules": req.rtl_rules,
            "sv_rules": req.sv_rules,
            "uvm_rules": req.uvm_rules,
            "verilog_tb_rules": req.verilog_tb_rules
        }).eq("id", assignment_id).execute()
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{assignment_id}")
def delete_assignment(assignment_id: str, authorization: str = Header(...)):
    try:
        verify_senior(authorization)
        svc = get_service_client()
        svc.table("assignments").delete().eq("id", assignment_id).execute()
        return {"message": "Assignment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
