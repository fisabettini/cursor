-- PostgreSQL 17: Select all parent tables that are partitioned
-- This query retrieves information about partitioned parent tables

SELECT 
    n.nspname AS schema_name,
    c.relname AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pt.partstrat AS partition_strategy,
    CASE pt.partstrat
        WHEN 'l' THEN 'LIST'
        WHEN 'r' THEN 'RANGE'
        WHEN 'h' THEN 'HASH'
    END AS partition_strategy_name,
    pg_get_partkeydef(c.oid) AS partition_key,
    (SELECT count(*) 
     FROM pg_inherits i 
     WHERE i.inhparent = c.oid) AS partition_count
FROM 
    pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_partitioned_table pt ON pt.partrelid = c.oid
WHERE 
    c.relkind = 'p'  -- 'p' indicates a partitioned table
    AND n.nspname NOT IN ('pg_catalog', 'information_schema')  -- Exclude system schemas
ORDER BY 
    n.nspname, 
    c.relname;
