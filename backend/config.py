import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "vlsi-review-default-secret-change-me")
# SMTP no longer used — kept for reference only
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
