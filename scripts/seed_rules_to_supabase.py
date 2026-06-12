"""One-time script: creates global_rules table in Supabase and seeds it from YAML files.

Usage:
    1. Run the SQL below in Supabase SQL Editor first, OR let this script attempt auto-creation.
    2. python -m scripts.seed_rules_to_supabase

SQL to run manually in Supabase SQL Editor (https://supabase.com/dashboard/project/PROJECT_REF/sql/new):

    CREATE TABLE IF NOT EXISTS global_rules (
        review_type TEXT PRIMARY KEY,
        rules JSONB NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    ALTER TABLE global_rules ENABLE ROW LEVEL SECURITY;

    -- Allow service_role full access
    CREATE POLICY "Service role full access" ON global_rules
        FOR ALL TO service_role USING (true) WITH CHECK (true);

    -- Allow authenticated users to read rules
    CREATE POLICY "Authenticated users can read" ON global_rules
        FOR SELECT TO authenticated USING (true);
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from backend.services.supabase_service import get_service_client
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

REVIEW_TYPES = ["rtl", "sv", "uvm", "verilog_tb"]


def seed():
    svc = get_service_client()
    if not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_SERVICE_KEY is required to seed rules.")
        sys.exit(1)

    for rt in REVIEW_TYPES:
        path = f"rules/{rt}_rules.yaml"
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"  SKIP: {path} not found")
            continue

        rules = data.get("rules", [])
        svc.table("global_rules").upsert({
            "review_type": rt,
            "rules": rules,
        }, on_conflict="review_type").execute()
        print(f"  OK: {rt} — {len(rules)} rules seeded")

    print("\nDone! All rules migrated to Supabase.")


if __name__ == "__main__":
    print("Seeding global rules into Supabase...\n")
    seed()
