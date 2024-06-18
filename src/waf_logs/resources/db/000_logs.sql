CREATE TABLE
    IF NOT EXISTS cf_waf_logs_adaptive (
        rayName VARCHAR(64) PRIMARY KEY,
        "datetime" TIMESTAMP,
        data JSONB,
        UNIQUE (rayName, "datetime")
    );
