CREATE TABLE IF NOT EXISTS review_cache (
    hash TEXT PRIMARY KEY,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE review_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_access" ON review_cache
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
