create table
    if not exists cf_waf_logs_adaptive (
        rayname varchar(64),
        zone_id varchar(32),
        "datetime" timestamp,
        data jsonb,
        primary key (zone_id, "datetime", rayname)
    );
