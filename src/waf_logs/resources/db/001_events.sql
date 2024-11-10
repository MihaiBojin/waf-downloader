create table
    if not exists events (
        name varchar(64) primary key,
        "datetime" timestamp
        with
            time zone not null,
            unique (name)
    );
