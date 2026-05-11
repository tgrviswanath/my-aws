-- init.sql — Runs once when MySQL container first starts

CREATE TABLE IF NOT EXISTS items (
    id          VARCHAR(36)  PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id         VARCHAR(36)  PRIMARY KEY,
    username   VARCHAR(100) NOT NULL UNIQUE,
    email      VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- Seed data
INSERT IGNORE INTO items (id, name, description) VALUES
    ('item-001', 'Widget A', 'First test item'),
    ('item-002', 'Widget B', 'Second test item');
