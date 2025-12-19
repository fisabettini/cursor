-- Simplified query to list just the names
-- PostgreSQL 17: Simple list of partitioned parent tables

SELECT 
    schemaname,
    tablename
FROM 
    pg_tables
WHERE 
    schemaname NOT IN ('pg_catalog', 'information_schema')
    AND tablename IN (
        SELECT c.relname
        FROM pg_class c
        WHERE c.relkind = 'p'
    )
ORDER BY 
    schemaname, 
    tablename;
