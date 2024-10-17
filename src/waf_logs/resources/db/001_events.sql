CREATE TABLE
    IF NOT EXISTS events (
        name VARCHAR(64) PRIMARY KEY,
        "datetime" TIMESTAMP NOT NULL,
        UNIQUE (name)
    );
