create table
    if not exists events (
        name varchar(64) not null,
        zone_id varchar(64) not null,
        "datetime" timestamp with time zone not null,
        primary key (zone_id, name)
    );
