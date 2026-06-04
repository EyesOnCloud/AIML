CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    question TEXT,
    answer TEXT,
    risk_score FLOAT,
    risk_flag VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_queue (
    id SERIAL PRIMARY KEY,
    question TEXT,
    ai_answer TEXT,
    confidence FLOAT,
    status VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER
);

CREATE TABLE IF NOT EXISTS approved_answers (
    id SERIAL PRIMARY KEY,
    question_pattern TEXT,
    answer TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username,password_hash,role)
VALUES ('admin','admin123','admin')
ON CONFLICT (username) DO NOTHING;

INSERT INTO users (username,password_hash,role)
VALUES ('user1','user123','user')
ON CONFLICT (username) DO NOTHING;
