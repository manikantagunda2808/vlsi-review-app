from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List
from backend.services.auth_utils import verify_token
from backend.config import GROQ_API_KEY
from groq import Groq

router = APIRouter()

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a VLSI expert assistant. Help engineers with:
- Verilog and SystemVerilog coding and debugging
- UVM testbench architecture and methodology
- RTL design best practices
- PCIe, AXI, and other protocols
- Code review feedback explanations
- Verification concepts and coverage
Keep answers concise, technical, and practical."""

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@router.post("/")
def chat(req: ChatRequest, authorization: str = Header(...)):
    try:
        verify_token(authorization)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": m.role, "content": m.content} for m in req.messages]

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4
        )

        return {"reply": response.choices[0].message.content}

    except Exception as e:
        print(f"CHAT ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))
