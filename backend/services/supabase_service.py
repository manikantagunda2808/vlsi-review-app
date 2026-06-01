from supabase import create_client
from backend.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
service_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else supabase

def get_client():
    return supabase

def get_service_client():
    return service_client
