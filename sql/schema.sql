-- Agent Registry — Database Schema
-- Find AI Talent — Agent Registry

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,                    -- agt_<hex>
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    owner_email TEXT NOT NULL,
    owner_name TEXT,
    website_url TEXT,
    logo_url TEXT,
    manifest_json TEXT NOT NULL,            -- Full A2A-compliant agent card JSON
    verified INTEGER DEFAULT 0,             -- 0=unverified, 1=verified, 2=featured
    trust_score REAL DEFAULT 0,            -- 0-100, computed from success_rate + reviews
    total_calls INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0,
    monthly_calls INTEGER DEFAULT 0,
    category TEXT DEFAULT 'general',        -- verification, scraping, search, communication, data, tools
    tags TEXT DEFAULT '',                   -- comma-separated tags
    auth_method TEXT DEFAULT 'bearer',      -- bearer, api_key, oauth, none
    pricing_model TEXT DEFAULT 'per_call',  -- per_call, monthly, freemium, free
    pricing_details TEXT,                   -- JSON: {"per_call": 0.05, "monthly": 29, "free_tier": "100 calls/day"}
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    capability TEXT NOT NULL,              -- Human-readable: "verify business hours by phone"
    capability_slug TEXT,                   -- Machine-readable: "business_hours_verification"
    embedding BLOB,                         -- Vector embedding for semantic search (sha256 hash for MVP, real embeddings later)
    created_at REAL NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,               -- ar_<hex>
    agent_id TEXT,
    email TEXT NOT NULL,
    tier TEXT DEFAULT 'free',              -- free, verified, featured, enterprise
    stripe_customer_id TEXT,
    created_at REAL NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usage_counters (
    key_id TEXT NOT NULL,                  -- API key
    counter_type TEXT NOT NULL,            -- "discoveries", "calls", etc.
    month TEXT NOT NULL,                   -- "2026-05" format
    count INTEGER DEFAULT 0,
    PRIMARY KEY (key_id, counter_type, month)
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,                   -- txn_<hex>
    caller_agent_id TEXT,
    callee_agent_id TEXT NOT NULL,
    caller_key_id TEXT,                     -- API key used
    amount_cents INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',        -- initiated, completed, failed, refunded
    metadata TEXT,                          -- JSON: request details, latency, etc.
    created_at REAL NOT NULL,
    FOREIGN KEY (callee_agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,                   -- rev_<hex>
    agent_id TEXT NOT NULL,
    reviewer_key_id TEXT NOT NULL,
    rating INTEGER NOT NULL,               -- 1-5
    review_text TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    UNIQUE(agent_id, reviewer_key_id)      -- Prevent duplicate reviews
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_agents_category ON agents(category);
CREATE INDEX IF NOT EXISTS idx_agents_verified ON agents(verified);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(active);
CREATE INDEX IF NOT EXISTS idx_capabilities_agent ON capabilities(agent_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_slug ON capabilities(capability_slug);
CREATE INDEX IF NOT EXISTS idx_transactions_callee ON transactions(callee_agent_id);
CREATE INDEX IF NOT EXISTS idx_transactions_caller ON transactions(caller_agent_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_email ON api_keys(email);
CREATE INDEX IF NOT EXISTS idx_api_keys_tier ON api_keys(tier);
CREATE INDEX IF NOT EXISTS idx_reviews_agent ON reviews(agent_id);
CREATE INDEX IF NOT EXISTS idx_usage_counters_lookup ON usage_counters(key_id, counter_type, month);

-- Email verification tokens
CREATE TABLE IF NOT EXISTS email_verifications (
    token TEXT PRIMARY KEY,                -- Hex token for verification link
    key_id TEXT NOT NULL,                 -- API key to activate
    email TEXT NOT NULL,                  -- Email address being verified
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_key ON email_verifications(key_id);