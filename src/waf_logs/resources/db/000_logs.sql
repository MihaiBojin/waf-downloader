create table
    if not exists cf_waf_logs_adaptive (
        rayname varchar(64) not null,
        zone_id varchar(32) not null,
        "datetime" timestamp
        with
            time zone not null,
            data jsonb,
            primary key (zone_id, "datetime", rayname)
    );
