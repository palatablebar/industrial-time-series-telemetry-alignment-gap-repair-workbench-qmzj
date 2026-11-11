-- TSALIGN initial schema (baseline reference; runtime uses SQLAlchemy create_all)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(160) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    display_name VARCHAR(80) NOT NULL,
    role VARCHAR(24) NOT NULL,
    unit VARCHAR(80) DEFAULT '',
    daily_job_quota INTEGER DEFAULT 40,
    quota_used INTEGER DEFAULT 0,
    quota_used_date DATE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE data_source (
    id SERIAL PRIMARY KEY,
    code VARCHAR(40) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    protocol VARCHAR(16) NOT NULL,
    sample_interval_s INTEGER NOT NULL,
    timezone VARCHAR(64) DEFAULT 'Asia/Shanghai',
    drift_hint_ms INTEGER DEFAULT 0,
    status VARCHAR(24) DEFAULT 'online',
    workshop VARCHAR(80) DEFAULT '',
    description TEXT DEFAULT '',
    last_capture_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE signal (
    id SERIAL PRIMARY KEY,
    code VARCHAR(60) UNIQUE NOT NULL,
    source_id INTEGER NOT NULL REFERENCES data_source(id),
    device_code VARCHAR(40) NOT NULL,
    device_name VARCHAR(80) DEFAULT '',
    measure_name VARCHAR(80) NOT NULL,
    tag_path VARCHAR(160) DEFAULT '',
    unit VARCHAR(24) DEFAULT '',
    sampling_interval_s INTEGER DEFAULT 5,
    scale_min DOUBLE PRECISION DEFAULT 0,
    scale_max DOUBLE PRECISION DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE raw_telemetry (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER NOT NULL REFERENCES signal(id),
    source_id INTEGER NOT NULL REFERENCES data_source(id),
    ts DOUBLE PRECISION NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    seq INTEGER DEFAULT 0,
    CONSTRAINT uq_raw_signal_ts UNIQUE (signal_id, ts)
);

CREATE TABLE alignment_job (
    id SERIAL PRIMARY KEY,
    name VARCHAR(140) UNIQUE NOT NULL,
    device_codes JSON DEFAULT '[]',
    signal_codes JSON DEFAULT '[]',
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    grid_s INTEGER NOT NULL,
    agg_strategy VARCHAR(16) NOT NULL,
    fill_strategy VARCHAR(24) NOT NULL,
    status VARCHAR(16) DEFAULT 'pending',
    error_reason VARCHAR(40) DEFAULT '',
    params_snapshot JSON DEFAULT '{}',
    note TEXT DEFAULT '',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE alignment_run (
    id SERIAL PRIMARY KEY,
    job_id INTEGER UNIQUE NOT NULL REFERENCES alignment_job(id),
    status VARCHAR(16) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT now(),
    finished_at TIMESTAMP,
    duration_ms INTEGER DEFAULT 0,
    coverage_pct DOUBLE PRECISION DEFAULT 0,
    drift_ms DOUBLE PRECISION DEFAULT 0,
    drift_confidence DOUBLE PRECISION DEFAULT 0,
    anomaly_rate DOUBLE PRECISION DEFAULT 0,
    quality_score DOUBLE PRECISION DEFAULT 0,
    gap_count INTEGER DEFAULT 0,
    gap_total_s DOUBLE PRECISION DEFAULT 0,
    point_count INTEGER DEFAULT 0,
    bucket_count INTEGER DEFAULT 0,
    failure_reason VARCHAR(40) DEFAULT '',
    result_json JSON DEFAULT '{}'
);

CREATE TABLE gap_event (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES alignment_run(id),
    signal_id INTEGER NOT NULL REFERENCES signal(id),
    start_ts TIMESTAMP NOT NULL,
    end_ts TIMESTAMP NOT NULL,
    duration_s DOUBLE PRECISION DEFAULT 0,
    bucket_length INTEGER DEFAULT 0,
    fill_strategy VARCHAR(24) DEFAULT 'linear',
    confidence DOUBLE PRECISION DEFAULT 0,
    severity VARCHAR(12) DEFAULT 'low',
    annotated BOOLEAN DEFAULT FALSE,
    annotation TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    actor_id INTEGER REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(48) DEFAULT '',
    entity_id INTEGER,
    before_json JSON,
    after_json JSON,
    ip VARCHAR(64) DEFAULT '',
    created_at TIMESTAMP DEFAULT now()
);
