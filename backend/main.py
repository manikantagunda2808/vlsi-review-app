from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import auth, review, rules, history, assignments, chat

app = FastAPI(title="VLSI Review App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(review.router, prefix="/review")
app.include_router(rules.router, prefix="/rules")
app.include_router(history.router, prefix="/history")
app.include_router(assignments.router, prefix="/assignments")
app.include_router(chat.router, prefix="/chat")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
