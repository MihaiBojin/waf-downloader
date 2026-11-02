-- Rebuilds the primary key of tables created with zone_id as the leading column,
-- so that the most recent records can be read straight from the index.
do $$
begin
    if (
        select a.attname
        from pg_index i
        join pg_attribute a on a.attrelid = i.indrelid and a.attnum = i.indkey[0]
        where i.indrelid = 'cf_waf_logs_adaptive'::regclass and i.indisprimary
    ) <> 'datetime' then
        alter table cf_waf_logs_adaptive
            drop constraint cf_waf_logs_adaptive_pkey,
            add primary key ("datetime", zone_id, rayname);
    end if;
end
$$;
