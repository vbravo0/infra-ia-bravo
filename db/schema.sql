-- Script de inicializacion para la base de datos de test
CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL,
    engine TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence REAL,
    parse_error INTEGER NOT NULL DEFAULT 0,
    model_version TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    description TEXT NOT NULL,
    raw_llm TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_events (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL,
    actual_severity TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'human',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_history_cve_id ON history(cve_id);
CREATE INDEX IF NOT EXISTS idx_history_model_version ON history(model_version);
CREATE INDEX IF NOT EXISTS idx_history_prompt_hash ON history(prompt_hash);
CREATE INDEX IF NOT EXISTS idx_feedback_cve_id ON feedback_events(cve_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback_events(created_at);
