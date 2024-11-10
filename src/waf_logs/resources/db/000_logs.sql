create table
    if not exists cf_waf_logs_adaptive (
        rayname varchar(64) primary key,
        zone_id varchar(32),
        "datetime" timestamp,
        data jsonb,
        unique (rayname, "datetime")
    );

create index if not exists cf_waf_logs_adaptive_zone_datetime_idx on cf_waf_logs_adaptive (zone_id, "datetime");
