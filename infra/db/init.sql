CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(50),
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('SENIOR', 'GUARDIAN', 'FAMILY_MEMBER', 'ADMIN')),
    password_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS family_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    relation VARCHAR(50),
    phone_number VARCHAR(50),
    phone_number_hash TEXT,
    phone_number_last4 VARCHAR(4),
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seniors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(50),
    phone_number_hash TEXT,
    phone_number_last4 VARCHAR(4),
    birth_year INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS guardians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_id UUID NOT NULL REFERENCES seniors(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    relation VARCHAR(50),
    priority INT NOT NULL DEFAULT 1,
    notify_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS safe_words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    word_hash TEXT NOT NULL,
    hint VARCHAR(255),
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL,
    version VARCHAR(30) NOT NULL,
    accepted BOOLEAN NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address VARCHAR(100),
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_member_id UUID NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'ENROLLED', 'FAILED', 'DELETED')),
    consent_id UUID REFERENCES consent_logs(id),
    embedding TEXT,
    embedding_model VARCHAR(100),
    embedding_version VARCHAR(50),
    quality_score INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    enrolled_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS voice_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_profile_id UUID NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    object_key TEXT,
    audio_ref TEXT,
    duration_ms INT,
    sample_rate INT,
    mime_type VARCHAR(100),
    purpose VARCHAR(30) NOT NULL CHECK (purpose IN ('ENROLLMENT', 'ANALYSIS')),
    retained BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS call_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_id UUID NOT NULL REFERENCES seniors(id) ON DELETE CASCADE,
    phone_number_hash TEXT NOT NULL,
    phone_number_last4 VARCHAR(4),
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('INCOMING', 'OUTGOING')),
    caller_type VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (caller_type IN ('FAMILY', 'UNKNOWN', 'RISK_NUMBER', 'BLOCKED')),
    risk_score INT NOT NULL DEFAULT 0,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW'
        CHECK (risk_level IN ('LOW', 'CAUTION', 'HIGH', 'CRITICAL')),
    action_taken VARCHAR(50),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_id UUID NOT NULL REFERENCES seniors(id) ON DELETE CASCADE,
    call_event_id UUID REFERENCES call_events(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    risk_score INT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    reason_codes TEXT NOT NULL DEFAULT '',
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number_hash TEXT NOT NULL,
    phone_number_last4 VARCHAR(4) NOT NULL,
    label VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'MANUAL',
    risk_score INT NOT NULL DEFAULT 80,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS emergency_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_event_id UUID NOT NULL REFERENCES risk_events(id) ON DELETE CASCADE,
    guardian_id UUID NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'RESPONDED')),
    response VARCHAR(30)
        CHECK (response IN ('REAL_CALL', 'NOT_ME', 'UNKNOWN')),
    message TEXT,
    sent_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
