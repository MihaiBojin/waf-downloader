CREATE TABLE
    IF NOT EXISTS events (
        name VARCHAR(64) PRIMARY KEY,
        "datetime" TIMESTAMP WITH time zone NOT NULL,
        UNIQUE (name)
    );
