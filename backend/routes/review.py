from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
from backend.services.groq_service import review_code
from backend.services.rules_service import load_rules
from backend.services.supabase_service import get_service_client
from backend.services.auth_utils import verify_token
import zipfile
import io

router = APIRouter()

def detect_file_type_from_path(path: str) -> str | None:
    """Detect file type based on ZIP folder path.
    - Files in RTL/rtl/ → rtl
    - Files in TB/tb/ → tb (mapped to sv, uvm, or verilog_tb rules based on user's dropdown)
    - Other files → None (skipped)
    """
    normalized = path.replace("\\", "/").lower()
    segments = normalized.split("/")
    if "rtl" in segments:
        return "rtl"
    if "tb" in segments:
        return "tb"
    return None

def load_assignment_rules(assignment: dict, rule_type: str) -> str:
    # always load global rules first
    global_rules = load_rules(rule_type)
    
    # check if assignment has specific rules
    rules_data = assignment.get(f"{rule_type}_rules", [])
    if not rules_data:
        # no assignment rules — global only
        return global_rules
    
    # combine global + assignment rules
    assignment_rules = ""
    for r in rules_data:
        assignment_rules += f"- [{r['id']}] ({r['severity'].upper()}) {r['rule']}\n"
    
    return global_rules + "\n# Assignment Specific Rules\n" + assignment_rules

@router.post("/run")
async def run_review(
    assignment_id: str = Form(...),
    user_name: str = Form(...),
    file: UploadFile = File(...),
    tb_type: str = Form("sv"),  # Options: "sv", "uvm", "verilog_tb"
    authorization: str = Header(...)
):
    try:
        svc = get_service_client()

        payload = verify_token(authorization)
        user_id = payload["user_id"]

        # get assignment
        assignment = svc.table("assignments").select("*").eq("id", assignment_id).single().execute()
        assignment_data = assignment.data

        # extract zip
        content = await file.read()
        zip_file = zipfile.ZipFile(io.BytesIO(content))

        # determine which rules to use for TB folder files
        tb_type_lower = tb_type.lower()
        if tb_type_lower == "uvm":
            tb_rule_type = "uvm"
        elif tb_type_lower == "verilog_tb":
            tb_rule_type = "verilog_tb"
        else:
            tb_rule_type = "sv"

        # group files by type based on folder path
        files_by_type = {"rtl": [], "tb": []}
        for name in zip_file.namelist():
            if name.endswith((".v", ".sv", ".uvm")) and not name.startswith("__"):
                file_type = detect_file_type_from_path(name)
                if file_type is None:
                    continue  # skip files not in recognized folders
                code = zip_file.read(name).decode("utf-8", errors="ignore")
                files_by_type[file_type].append({"name": name, "code": code})

        # review each group
        all_violations = []
        all_warnings = []
        all_passed = []
        total_score = 0
        reviewed_count = 0
        combined_summary = []

        for ftype, files in files_by_type.items():
            if not files:
                continue
            combined_code = "\n\n".join([f"### {f['name']}\n{f['code']}" for f in files])
            # map tb folder to the user's chosen rule type
            actual_rule_type = tb_rule_type if ftype == "tb" else ftype
            rules = load_assignment_rules(assignment_data, actual_rule_type)
            result = review_code(combined_code, rules, actual_rule_type)

            all_violations.extend(result.get("violations", []))
            all_warnings.extend(result.get("warnings", []))
            all_passed.extend(result.get("passed", []))
            total_score += result.get("score", 0)
            reviewed_count += 1
            combined_summary.append(f"[{actual_rule_type.upper()}] {result.get('summary', '')}")

        final_score = round(total_score / reviewed_count, 1) if reviewed_count else 0
        final_summary = " | ".join(combined_summary)

        # save to supabase
        svc.table("reviews").insert({
            "user_id": user_id,
            "user_name": user_name,
            "review_type": "mixed",
            "code": f"ZIP upload — {assignment_data['name']}",
            "score": final_score,
            "violations": all_violations,
            "warnings": all_warnings,
            "passed": all_passed,
            "summary": final_summary
        }).execute()

        return {
            "score": final_score,
            "violations": all_violations,
            "warnings": all_warnings,
            "passed": all_passed,
            "summary": final_summary
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/email-report")
def email_report(req: EmailReportRequest, authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        user_id = payload["user_id"]

        auth_page = svc.auth.admin.list_users()
        auth_map = {u.id: u.email for u in auth_page}
        sender_email = auth_map.get(user_id, "")

        from backend.services.email_service import send_review_report
        send_review_report(
            from_email=sender_email,
            to_emails=req.recipients,
            user_name=req.user_name,
            result=req.review_result,
            repo_url=req.repo_url
        )
        return {"message": "Report emailed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"EMAIL REPORT ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))

class EmailReportRequest(BaseModel):
    recipients: list[str]
    review_result: dict
    user_name: str
    repo_url: str = ""

class PasteReviewRequest(BaseModel):
    review_type: str
    code: str
    user_name: str

@router.post("/paste")
async def paste_review(req: PasteReviewRequest, authorization: str = Header(...)):
    try:
        svc = get_service_client()
        payload = verify_token(authorization)
        user_id = payload["user_id"]

        rules = load_rules(req.review_type)
        result = review_code(req.code, rules, req.review_type)

        svc.table("reviews").insert({
            "user_id": user_id,
            "user_name": req.user_name,
            "review_type": req.review_type,
            "code": req.code,
            "score": result["score"],
            "violations": result["violations"],
            "warnings": result["warnings"],
            "passed": result["passed"],
            "summary": result["summary"]
        }).execute()

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
