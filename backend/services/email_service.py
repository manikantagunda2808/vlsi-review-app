import json
import urllib.request
from backend.config import SMTP_EMAIL, SMTP_PASSWORD

BREVO_API = "https://api.brevo.com/v3/smtp/email"

def _send_via_api(to_emails: list, subject: str, content: str, content_type: str = "textContent", reply_to: str | None = None):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"\n=== SMTP not configured. Would send to {to_emails} ===\n")
        return

    payload = {
        "sender": {"email": SMTP_EMAIL},
        "to": [{"email": e} for e in to_emails],
        "subject": subject,
        content_type: content,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}

    req = urllib.request.Request(
        BREVO_API,
        data=json.dumps(payload).encode(),
        headers={
            "api-key": SMTP_PASSWORD,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        urllib.request.urlopen(req)
        print(f"Email sent to {to_emails}")
    except Exception as e:
        body = e.read().decode() if hasattr(e, "read") else ""
        print(f"\n=== Email failed. To: {to_emails} ===\n")
        print(f"Error: {e}\n{body}")

def send_otp_email(to_email: str, otp: str):
    _send_via_api(
        to_emails=[to_email],
        subject="Your VLSI Review OTP",
        content=f"Your OTP code is: {otp}\n\nThis code expires in 10 minutes.",
        content_type="textContent",
    )

def send_review_report(from_email: str, to_emails: list, user_name: str, result: dict):
    score = result.get("score", 0)
    violations = result.get("violations", [])
    warnings = result.get("warnings", [])
    passed = result.get("passed", [])
    summary = result.get("summary", "")

    violations_html = ""
    for v in violations:
        violations_html += f"<tr><td style='padding:6px 10px;border:1px solid #333;color:#ff6b6b'>{v.get('rule_id','')}</td><td style='padding:6px 10px;border:1px solid #333;color:#e0e0e0'>{v.get('message','')}</td><td style='padding:6px 10px;border:1px solid #333;color:#ff6b6b'>line {v.get('line','')}</td></tr>"

    warnings_html = ""
    for w in warnings:
        warnings_html += f"<tr><td style='padding:6px 10px;border:1px solid #333;color:#f5a623'>{w.get('rule_id','')}</td><td style='padding:6px 10px;border:1px solid #333;color:#e0e0e0'>{w.get('message','')}</td><td style='padding:6px 10px;border:1px solid #333;color:#f5a623'>line {w.get('line','')}</td></tr>"

    score_color = "#00c896" if score >= 7 else "#f5a623" if score >= 5 else "#ff6b6b"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',sans-serif;background:#0f1117;padding:20px">
<table cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#1a1d27;border:1px solid #2e3148;border-radius:10px">
<tr><td style="padding:20px">
<table cellpadding="0" cellspacing="0" width="100%">
<tr><td><h1 style="color:#ffffff;font-size:20px;margin:0">⚡ VLSI Code Review Report</h1></td>
<td align="right"><span style="font-size:13px;color:#7a7f9a">{user_name}</span></td></tr></table>
</td></tr>
<tr><td style="padding:0 20px">
<table cellpadding="0" cellspacing="0" width="100%">
<tr><td style="background:#0f1117;border:1px solid #2e3148;border-radius:8px;padding:14px;text-align:center">
<div style="display:inline-block;width:48px;height:48px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid {score_color};color:{score_color};font-size:20px;font-weight:700;line-height:48px;margin-bottom:6px">{score}</div>
<div style="font-size:13px;color:#7a7f9a"><strong style="color:#e0e0e0;display:block;margin-bottom:4px">Score: {score}/10</strong>{len(violations)} violations · {len(warnings)} warnings · {len(passed)} passed</div>
</td></tr></table>
</td></tr>
<tr><td style="padding:14px 20px">
<table cellpadding="0" cellspacing="0" width="100%">
<tr><td style="font-size:12px;color:#7a7f9a;padding:6px 0">Summary</td></tr>
<tr><td style="font-size:13px;color:#e0e0e0;line-height:1.6;background:#0f1117;border:1px solid #2e3148;border-radius:8px;padding:12px">{summary}</td></tr>
</table>
</td></tr>"""

    if violations:
        html += f"""<tr><td style="padding:0 20px">
<table cellpadding="0" cellspacing="0" width="100%">
<tr><td style="font-size:12px;color:#ff6b6b;padding:6px 0">Violations — must fix</td></tr>
<tr><td><table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px">
<tr style="background:#0f1117"><th style="padding:6px 10px;border:1px solid #333;color:#7a7f9a;text-align:left">Rule</th><th style="padding:6px 10px;border:1px solid #333;color:#7a7f9a;text-align:left">Message</th><th style="padding:6px 10px;border:1px solid #333;color:#7a7f9a;text-align:left">Line</th></tr>
{violations_html}
</table></td></tr></table>
</td></tr>"""

    if warnings:
        html += f"""<tr><td style="padding:0 20px">
<table cellpadding="0" cellspacing="0" width="100%">
<tr><td style="font-size:12px;color:#f5a623;padding:6px 0">Warnings</td></tr>
<tr><td><table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px">
<tr style="background:#0f1117"><th style="padding:6px 10px;border:1px solid #333;color:#7a7f9a;text-align:left">Rule</th><th style="padding:6px 10px;border:1px solid #333;color:#7a7f9a;text-align:left">Message</th><th style="padding:6px 10px;border:1px solid #333;color:#7a7f9a;text-align:left">Line</th></tr>
{warnings_html}
</table></td></tr></table>
</td></tr>"""

    html += """<tr><td style="padding:20px;text-align:center;font-size:11px;color:#5a6a85">VLSI Review App · Auto-generated email</td></tr>
</table></body></html>"""

    _send_via_api(
        to_emails=to_emails,
        subject=f"VLSI Code Review Report — {user_name}",
        content=html,
        content_type="htmlContent",
        reply_to=from_email,
    )
