-- Alternative query with more detailed information
-- PostgreSQL 17: Comprehensive view of partitioned parent tables

SELECT 
    n.nspname AS schema_name,
    c.relname AS table_name,
    c.oid::regclass AS table_oid,
    CASE pt.partstrat
        WHEN 'l' THEN 'LIST'
        WHEN 'r' THEN 'RANGE'
        WHEN 'h' THEN 'HASH'
    END AS partition_type,
    pg_get_partkeydef(c.oid) AS partition_key_definition,
    (SELECT count(*) 
     FROM pg_inherits i 
     WHERE i.inhparent = c.oid) AS direct_partition_count,
    pg_size_pretty(pg_table_size(c.oid)) AS table_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size_with_partitions,
    obj_description(c.oid, 'pg_class') AS table_comment
FROM 
    pg_class c
    INNER JOIN pg_namespace n ON n.oid = c.relnamespace
    INNER JOIN pg_partitioned_table pt ON pt.partrelid = c.oid
WHERE 
    c.relkind = 'p'  -- Only partitioned tables (parent tables)
    AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
ORDER BY 
    pg_total_relation_size(c.oid) DESC,
    n.nspname,
    c.relname;
