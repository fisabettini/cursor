#!/usr/bin/env python3
"""
PostgreSQL DDL Generator Script
Supports PostgreSQL 18
Generates DDL for:
- Tables (partitioned and non-partitioned)
- Columns with user types
- Primary Keys and Foreign Keys (with dependency management)
- Sequences (converts to serial/bigserial)
- Triggers and Functions
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
import argparse
import sys
from typing import List, Dict, Set, Tuple


class PostgresDDLGenerator:
    def __init__(self, connection_params: Dict[str, str], schema: str = 'public'):
        """
        Initialize the DDL generator.
        
        Args:
            connection_params: Dictionary with connection parameters (host, database, user, password, port)
            schema: Schema name to generate DDL for (default: 'public')
        """
        self.conn_params = connection_params
        self.schema = schema
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print(f"Connected to database: {self.conn_params['database']}", file=sys.stderr)
        except Exception as e:
            print(f"Error connecting to database: {e}", file=sys.stderr)
            sys.exit(1)
    
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_tables(self) -> List[Dict]:
        """Get all tables in the schema."""
        query = """
            SELECT 
                c.relname AS table_name,
                c.relkind AS table_type,
                pg_catalog.obj_description(c.oid, 'pg_class') AS comment,
                CASE 
                    WHEN c.relkind = 'p' THEN TRUE 
                    ELSE FALSE 
                END AS is_partitioned,
                CASE 
                    WHEN c.relispartition THEN TRUE 
                    ELSE FALSE 
                END AS is_partition,
                inh.inhparent::regclass::text AS parent_table
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_catalog.pg_inherits inh ON inh.inhrelid = c.oid
            WHERE n.nspname = %s
                AND c.relkind IN ('r', 'p')  -- regular tables and partitioned tables
            ORDER BY 
                CASE WHEN c.relispartition THEN 1 ELSE 0 END,
                c.relname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_columns(self, table_name: str) -> List[Dict]:
        """Get columns for a specific table."""
        query = """
            SELECT 
                a.attnum AS ordinal_position,
                a.attname AS column_name,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                a.attnotnull AS is_not_null,
                pg_catalog.pg_get_expr(ad.adbin, ad.adrelid) AS column_default,
                col_description(a.attrelid, a.attnum) AS comment,
                a.attidentity AS identity_generation,
                t.typname AS base_type_name,
                CASE 
                    WHEN t.typtype = 'e' THEN TRUE 
                    ELSE FALSE 
                END AS is_enum,
                CASE 
                    WHEN t.typtype = 'c' THEN TRUE 
                    ELSE FALSE 
                END AS is_composite,
                ns.nspname AS type_schema
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_catalog.pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
            LEFT JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
            LEFT JOIN pg_catalog.pg_namespace ns ON ns.oid = t.typnamespace
            WHERE n.nspname = %s
                AND c.relname = %s
                AND a.attnum > 0
                AND NOT a.attisdropped
            ORDER BY a.attnum;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()
    
    def get_sequence_info(self, table_name: str, column_name: str) -> Dict:
        """Get sequence information for a column."""
        query = """
            SELECT 
                seq.relname AS sequence_name,
                seq_ns.nspname AS sequence_schema,
                d.refobjid::regclass::text AS table_ref,
                pg_sequence.seqtypid::regtype::text AS sequence_type
            FROM pg_catalog.pg_depend d
            JOIN pg_catalog.pg_class seq ON seq.oid = d.objid
            JOIN pg_catalog.pg_namespace seq_ns ON seq_ns.oid = seq.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
            LEFT JOIN pg_catalog.pg_sequence ON pg_sequence.seqrelid = seq.oid
            WHERE d.refobjid = (SELECT c.oid FROM pg_catalog.pg_class c 
                               JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                               WHERE n.nspname = %s AND c.relname = %s)
                AND a.attname = %s
                AND seq.relkind = 'S'
                AND d.deptype = 'a';  -- auto dependency
        """
        self.cursor.execute(query, (self.schema, table_name, column_name))
        result = self.cursor.fetchone()
        return result if result else {}
    
    def get_primary_keys(self, table_name: str) -> Dict:
        """Get primary key constraints for a table."""
        query = """
            SELECT 
                con.conname AS constraint_name,
                array_agg(a.attname ORDER BY array_position(con.conkey, a.attnum)) AS column_names
            FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class c ON c.oid = con.conrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(con.conkey)
            WHERE n.nspname = %s
                AND c.relname = %s
                AND con.contype = 'p'
            GROUP BY con.conname;
        """
        self.cursor.execute(query, (self.schema, table_name))
        result = self.cursor.fetchone()
        return result if result else {}
    
    def get_foreign_keys(self, table_name: str = None) -> List[Dict]:
        """Get foreign key constraints."""
        if table_name:
            query = """
                SELECT 
                    con.conname AS constraint_name,
                    c.relname AS table_name,
                    array_agg(a.attname ORDER BY array_position(con.conkey, a.attnum)) AS column_names,
                    fc.relname AS foreign_table_name,
                    fn.nspname AS foreign_schema,
                    array_agg(fa.attname ORDER BY array_position(con.confkey, fa.attnum)) AS foreign_column_names,
                    CASE con.confupdtype
                        WHEN 'a' THEN 'NO ACTION'
                        WHEN 'r' THEN 'RESTRICT'
                        WHEN 'c' THEN 'CASCADE'
                        WHEN 'n' THEN 'SET NULL'
                        WHEN 'd' THEN 'SET DEFAULT'
                    END AS on_update,
                    CASE con.confdeltype
                        WHEN 'a' THEN 'NO ACTION'
                        WHEN 'r' THEN 'RESTRICT'
                        WHEN 'c' THEN 'CASCADE'
                        WHEN 'n' THEN 'SET NULL'
                        WHEN 'd' THEN 'SET DEFAULT'
                    END AS on_delete
                FROM pg_catalog.pg_constraint con
                JOIN pg_catalog.pg_class c ON c.oid = con.conrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(con.conkey)
                JOIN pg_catalog.pg_class fc ON fc.oid = con.confrelid
                JOIN pg_catalog.pg_namespace fn ON fn.oid = fc.relnamespace
                JOIN pg_catalog.pg_attribute fa ON fa.attrelid = fc.oid AND fa.attnum = ANY(con.confkey)
                WHERE n.nspname = %s
                    AND c.relname = %s
                    AND con.contype = 'f'
                GROUP BY con.conname, c.relname, fc.relname, fn.nspname, 
                         con.confupdtype, con.confdeltype;
            """
            self.cursor.execute(query, (self.schema, table_name))
        else:
            query = """
                SELECT 
                    con.conname AS constraint_name,
                    c.relname AS table_name,
                    n.nspname AS schema_name,
                    array_agg(a.attname ORDER BY array_position(con.conkey, a.attnum)) AS column_names,
                    fc.relname AS foreign_table_name,
                    fn.nspname AS foreign_schema,
                    array_agg(fa.attname ORDER BY array_position(con.confkey, fa.attnum)) AS foreign_column_names,
                    CASE con.confupdtype
                        WHEN 'a' THEN 'NO ACTION'
                        WHEN 'r' THEN 'RESTRICT'
                        WHEN 'c' THEN 'CASCADE'
                        WHEN 'n' THEN 'SET NULL'
                        WHEN 'd' THEN 'SET DEFAULT'
                    END AS on_update,
                    CASE con.confdeltype
                        WHEN 'a' THEN 'NO ACTION'
                        WHEN 'r' THEN 'RESTRICT'
                        WHEN 'c' THEN 'CASCADE'
                        WHEN 'n' THEN 'SET NULL'
                        WHEN 'd' THEN 'SET DEFAULT'
                    END AS on_delete
                FROM pg_catalog.pg_constraint con
                JOIN pg_catalog.pg_class c ON c.oid = con.conrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(con.conkey)
                JOIN pg_catalog.pg_class fc ON fc.oid = con.confrelid
                JOIN pg_catalog.pg_namespace fn ON fn.oid = fc.relnamespace
                JOIN pg_catalog.pg_attribute fa ON fa.attrelid = fc.oid AND fa.attnum = ANY(con.confkey)
                WHERE n.nspname = %s
                    AND con.contype = 'f'
                GROUP BY con.conname, c.relname, n.nspname, fc.relname, fn.nspname, 
                         con.confupdtype, con.confdeltype;
            """
            self.cursor.execute(query, (self.schema,))
        
        return self.cursor.fetchall()
    
    def get_partition_info(self, table_name: str) -> Dict:
        """Get partition information for a partitioned table."""
        query = """
            SELECT 
                pg_get_partkeydef(c.oid) AS partition_strategy
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
                AND c.relname = %s
                AND c.relkind = 'p';
        """
        self.cursor.execute(query, (self.schema, table_name))
        result = self.cursor.fetchone()
        return result if result else {}
    
    def get_partition_details(self, table_name: str) -> Dict:
        """Get partition details for a partition."""
        query = """
            SELECT 
                pg_get_expr(c.relpartbound, c.oid, true) AS partition_bound
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
                AND c.relname = %s
                AND c.relispartition = true;
        """
        self.cursor.execute(query, (self.schema, table_name))
        result = self.cursor.fetchone()
        return result if result else {}
    
    def get_functions(self) -> List[Dict]:
        """Get all functions in the schema."""
        query = """
            SELECT 
                p.proname AS function_name,
                pg_catalog.pg_get_function_arguments(p.oid) AS arguments,
                pg_catalog.pg_get_function_result(p.oid) AS return_type,
                pg_catalog.pg_get_functiondef(p.oid) AS function_definition,
                l.lanname AS language,
                CASE p.provolatile
                    WHEN 'i' THEN 'IMMUTABLE'
                    WHEN 's' THEN 'STABLE'
                    WHEN 'v' THEN 'VOLATILE'
                END AS volatility,
                pg_catalog.obj_description(p.oid, 'pg_proc') AS comment
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid = p.prolang
            WHERE n.nspname = %s
                AND p.prokind = 'f'  -- functions only, not procedures
            ORDER BY p.proname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_procedures(self) -> List[Dict]:
        """Get all procedures in the schema."""
        query = """
            SELECT 
                p.proname AS procedure_name,
                pg_catalog.pg_get_function_arguments(p.oid) AS arguments,
                pg_catalog.pg_get_functiondef(p.oid) AS procedure_definition,
                l.lanname AS language,
                pg_catalog.obj_description(p.oid, 'pg_proc') AS comment
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid = p.prolang
            WHERE n.nspname = %s
                AND p.prokind = 'p'  -- procedures only
            ORDER BY p.proname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_views(self) -> List[Dict]:
        """Get all views in the schema."""
        query = """
            SELECT 
                c.relname AS view_name,
                pg_catalog.pg_get_viewdef(c.oid, true) AS view_definition,
                pg_catalog.obj_description(c.oid, 'pg_class') AS comment
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
                AND c.relkind = 'v'  -- views only (not materialized views)
            ORDER BY c.relname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_materialized_views(self) -> List[Dict]:
        """Get all materialized views in the schema."""
        query = """
            SELECT 
                c.relname AS matview_name,
                pg_catalog.pg_get_viewdef(c.oid, true) AS matview_definition,
                pg_catalog.obj_description(c.oid, 'pg_class') AS comment
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
                AND c.relkind = 'm'  -- materialized views only
            ORDER BY c.relname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_triggers(self, table_name: str = None) -> List[Dict]:
        """Get triggers for a table or all tables."""
        if table_name:
            query = """
                SELECT 
                    t.tgname AS trigger_name,
                    c.relname AS table_name,
                    p.proname AS function_name,
                    CASE t.tgtype & 2
                        WHEN 2 THEN 'BEFORE'
                        ELSE 'AFTER'
                    END AS timing,
                    CASE 
                        WHEN t.tgtype & 4 = 4 THEN 'INSERT'
                        WHEN t.tgtype & 8 = 8 THEN 'DELETE'
                        WHEN t.tgtype & 16 = 16 THEN 'UPDATE'
                        ELSE 'UNKNOWN'
                    END AS event,
                    CASE t.tgtype & 1
                        WHEN 1 THEN 'ROW'
                        ELSE 'STATEMENT'
                    END AS level,
                    pg_catalog.pg_get_triggerdef(t.oid, true) AS trigger_definition
                FROM pg_catalog.pg_trigger t
                JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
                WHERE n.nspname = %s
                    AND c.relname = %s
                    AND NOT t.tgisinternal
                ORDER BY t.tgname;
            """
            self.cursor.execute(query, (self.schema, table_name))
        else:
            query = """
                SELECT 
                    t.tgname AS trigger_name,
                    c.relname AS table_name,
                    n.nspname AS schema_name,
                    p.proname AS function_name,
                    pg_catalog.pg_get_triggerdef(t.oid, true) AS trigger_definition
                FROM pg_catalog.pg_trigger t
                JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
                WHERE n.nspname = %s
                    AND NOT t.tgisinternal
                ORDER BY c.relname, t.tgname;
            """
            self.cursor.execute(query, (self.schema,))
        
        return self.cursor.fetchall()
    
    def get_indexes(self) -> List[Dict]:
        """Get all indexes (excluding PK/FK)."""
        query = """
            SELECT 
                i.relname AS index_name,
                t.relname AS table_name,
                pg_catalog.pg_get_indexdef(i.oid, 0, true) AS index_definition,
                ix.indisunique AS is_unique,
                ix.indisprimary AS is_primary,
                am.amname AS index_type,
                pg_catalog.obj_description(i.oid, 'pg_class') AS comment
            FROM pg_catalog.pg_index ix
            JOIN pg_catalog.pg_class i ON i.oid = ix.indexrelid
            JOIN pg_catalog.pg_class t ON t.oid = ix.indrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
            LEFT JOIN pg_catalog.pg_am am ON am.oid = i.relam
            WHERE n.nspname = %s
                AND NOT ix.indisprimary  -- Exclude primary keys
                AND NOT EXISTS (  -- Exclude foreign key indexes
                    SELECT 1 FROM pg_catalog.pg_constraint c
                    WHERE c.contype = 'f' AND c.conindid = i.oid
                )
            ORDER BY t.relname, i.relname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_sequences(self) -> List[Dict]:
        """Get all standalone sequences (not auto-generated by serial)."""
        query = """
            SELECT 
                c.relname AS sequence_name,
                pg_catalog.format_type(s.seqtypid, NULL) AS data_type,
                s.seqstart AS start_value,
                s.seqincrement AS increment_by,
                s.seqmin AS min_value,
                s.seqmax AS max_value,
                s.seqcache AS cache_value,
                s.seqcycle AS is_cycle,
                pg_catalog.obj_description(c.oid, 'pg_class') AS comment
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_catalog.pg_sequence s ON s.seqrelid = c.oid
            WHERE n.nspname = %s
                AND c.relkind = 'S'
                AND NOT EXISTS (  -- Exclude sequences owned by serial columns
                    SELECT 1 FROM pg_catalog.pg_depend d
                    WHERE d.objid = c.oid
                        AND d.deptype = 'a'  -- auto dependency
                        AND d.classid = 'pg_class'::regclass
                )
            ORDER BY c.relname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_foreign_tables(self) -> List[Dict]:
        """Get all foreign tables."""
        query = """
            SELECT 
                c.relname AS foreign_table_name,
                fs.srvname AS server_name,
                array_agg(a.attname ORDER BY a.attnum) AS column_names,
                array_agg(pg_catalog.format_type(a.atttypid, a.atttypmod) ORDER BY a.attnum) AS column_types,
                pg_catalog.obj_description(c.oid, 'pg_class') AS comment
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_catalog.pg_foreign_table ft ON ft.ftrelid = c.oid
            JOIN pg_catalog.pg_foreign_server fs ON fs.oid = ft.ftserver
            LEFT JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid 
                AND a.attnum > 0 AND NOT a.attisdropped
            WHERE n.nspname = %s
                AND c.relkind = 'f'
            GROUP BY c.relname, fs.srvname, c.oid
            ORDER BY c.relname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_foreign_table_options(self, foreign_table_name: str) -> List[Dict]:
        """Get options for a specific foreign table."""
        query = """
            SELECT 
                (pg_catalog.pg_options_to_table(ft.ftoptions)).*
            FROM pg_catalog.pg_foreign_table ft
            JOIN pg_catalog.pg_class c ON c.oid = ft.ftrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s 
                AND c.relname = %s;
        """
        try:
            self.cursor.execute(query, (self.schema, foreign_table_name))
            return self.cursor.fetchall()
        except Exception as e:
            # Fallback: parse options array directly if pg_options_to_table doesn't work
            query_fallback = """
                SELECT 
                    ft.ftoptions
                FROM pg_catalog.pg_foreign_table ft
                JOIN pg_catalog.pg_class c ON c.oid = ft.ftrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s 
                    AND c.relname = %s;
            """
            self.cursor.execute(query_fallback, (self.schema, foreign_table_name))
            result = self.cursor.fetchone()
            
            # Parse the options array manually
            options = []
            if result and result.get('ftoptions'):
                for opt_str in result['ftoptions']:
                    # Format is 'key=value'
                    if '=' in opt_str:
                        key, value = opt_str.split('=', 1)
                        options.append({'option_name': key, 'option_value': value})
            
            return options
    
    def get_extensions(self) -> List[Dict]:
        """Get all extensions."""
        query = """
            SELECT 
                e.extname AS extension_name,
                e.extversion AS version,
                n.nspname AS schema,
                pg_catalog.obj_description(e.oid, 'pg_extension') AS comment
            FROM pg_catalog.pg_extension e
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
            ORDER BY e.extname;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def get_table_grants(self, table_name: str = None) -> List[Dict]:
        """Get grants/permissions for tables and views."""
        if table_name:
            query = """
                SELECT 
                    n.nspname AS schema_name,
                    c.relname AS object_name,
                    CASE c.relkind
                        WHEN 'r' THEN 'table'
                        WHEN 'v' THEN 'view'
                        WHEN 'm' THEN 'materialized view'
                        WHEN 'f' THEN 'foreign table'
                        WHEN 'p' THEN 'partitioned table'
                    END AS object_type,
                    pg_catalog.pg_get_userbyid(c.relowner) AS owner,
                    (aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner)))).grantee::regrole::text AS grantee,
                    (aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner)))).privilege_type AS privilege_type,
                    (aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner)))).is_grantable AS is_grantable
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                    AND c.relname = %s
                    AND c.relkind IN ('r', 'v', 'm', 'f', 'p')
                ORDER BY c.relname, grantee, privilege_type;
            """
            self.cursor.execute(query, (self.schema, table_name))
        else:
            query = """
                SELECT 
                    n.nspname AS schema_name,
                    c.relname AS object_name,
                    CASE c.relkind
                        WHEN 'r' THEN 'table'
                        WHEN 'v' THEN 'view'
                        WHEN 'm' THEN 'materialized view'
                        WHEN 'f' THEN 'foreign table'
                        WHEN 'p' THEN 'partitioned table'
                    END AS object_type,
                    pg_catalog.pg_get_userbyid(c.relowner) AS owner,
                    (aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner)))).grantee::regrole::text AS grantee,
                    (aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner)))).privilege_type AS privilege_type,
                    (aclexplode(COALESCE(c.relacl, acldefault('r', c.relowner)))).is_grantable AS is_grantable
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                    AND c.relkind IN ('r', 'v', 'm', 'f', 'p')
                ORDER BY c.relname, grantee, privilege_type;
            """
            self.cursor.execute(query, (self.schema,))
        
        return self.cursor.fetchall()
    
    def get_sequence_grants(self) -> List[Dict]:
        """Get grants/permissions for sequences."""
        query = """
            SELECT 
                n.nspname AS schema_name,
                c.relname AS sequence_name,
                pg_catalog.pg_get_userbyid(c.relowner) AS owner,
                (aclexplode(COALESCE(c.relacl, acldefault('S', c.relowner)))).grantee::regrole::text AS grantee,
                (aclexplode(COALESCE(c.relacl, acldefault('S', c.relowner)))).privilege_type AS privilege_type,
                (aclexplode(COALESCE(c.relacl, acldefault('S', c.relowner)))).is_grantable AS is_grantable
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
                AND c.relkind = 'S'
            ORDER BY c.relname, grantee, privilege_type;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_user_types(self) -> List[Dict]:
        """Get user-defined types (enums, composite types, etc.)."""
        query = """
            SELECT 
                t.typname AS type_name,
                n.nspname AS type_schema,
                CASE t.typtype
                    WHEN 'e' THEN 'enum'
                    WHEN 'c' THEN 'composite'
                    WHEN 'd' THEN 'domain'
                    ELSE 'other'
                END AS type_kind,
                pg_catalog.obj_description(t.oid, 'pg_type') AS comment
            FROM pg_catalog.pg_type t
            JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = %s
                AND t.typtype IN ('e', 'c', 'd')
            ORDER BY 
                CASE t.typtype
                    WHEN 'e' THEN 1
                    WHEN 'd' THEN 2
                    WHEN 'c' THEN 3
                END,
                t.typname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()
    
    def get_enum_values(self, type_name: str) -> List[str]:
        """Get enum values for an enum type."""
        query = """
            SELECT enumlabel
            FROM pg_catalog.pg_enum
            WHERE enumtypid = (
                SELECT t.oid
                FROM pg_catalog.pg_type t
                JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = %s AND t.typname = %s
            )
            ORDER BY enumsortorder;
        """
        self.cursor.execute(query, (self.schema, type_name))
        return [row['enumlabel'] for row in self.cursor.fetchall()]
    
    def get_composite_type_attributes(self, type_name: str) -> List[Dict]:
        """Get attributes for a composite type."""
        query = """
            SELECT 
                a.attname AS attribute_name,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_type t ON t.typrelid = a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = %s
                AND t.typname = %s
                AND a.attnum > 0
                AND NOT a.attisdropped
            ORDER BY a.attnum;
        """
        self.cursor.execute(query, (self.schema, type_name))
        return self.cursor.fetchall()
    
    def get_domain_info(self, type_name: str) -> Dict:
        """Get domain information."""
        query = """
            SELECT 
                pg_catalog.format_type(t.typbasetype, t.typtypmod) AS base_type,
                t.typnotnull AS is_not_null,
                t.typdefault AS default_value,
                pg_catalog.pg_get_constraintdef(c.oid, true) AS check_constraint
            FROM pg_catalog.pg_type t
            JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            LEFT JOIN pg_catalog.pg_constraint c ON c.contypid = t.oid
            WHERE n.nspname = %s
                AND t.typname = %s
                AND t.typtype = 'd';
        """
        self.cursor.execute(query, (self.schema, type_name))
        result = self.cursor.fetchone()
        return result if result else {}
    
    def convert_sequence_to_serial(self, data_type: str, seq_info: Dict) -> str:
        """
        Convert integer types with sequences to serial/bigserial.
        
        Args:
            data_type: Original data type
            seq_info: Sequence information dictionary
            
        Returns:
            Serial type if applicable, otherwise original data type
        """
        if not seq_info:
            return data_type
        
        # Check if the sequence type matches the column type
        seq_type = seq_info.get('sequence_type', '')
        
        if 'integer' in data_type.lower() or data_type.lower() == 'int4':
            return 'serial'
        elif 'bigint' in data_type.lower() or data_type.lower() == 'int8':
            return 'bigserial'
        elif 'smallint' in data_type.lower() or data_type.lower() == 'int2':
            return 'smallserial'
        
        return data_type
    
    def generate_column_ddl(self, column: Dict, seq_info: Dict = None) -> str:
        """Generate DDL for a single column."""
        col_name = column['column_name']
        data_type = column['data_type']
        
        # Check if we should use serial type
        if seq_info:
            data_type = self.convert_sequence_to_serial(data_type, seq_info)
            # If converted to serial, skip the default clause
            if 'serial' in data_type:
                col_def = f'"{col_name}" {data_type}'
            else:
                col_def = f'"{col_name}" {data_type}'
                if column['column_default']:
                    col_def += f" DEFAULT {column['column_default']}"
        else:
            col_def = f'"{col_name}" {data_type}'
            
            # Add default if present and not using serial
            if column['column_default'] and 'serial' not in data_type:
                col_def += f" DEFAULT {column['column_default']}"
        
        # Add NOT NULL constraint
        if column['is_not_null']:
            col_def += ' NOT NULL'
        
        return col_def
    
    def generate_table_ddl(self, table: Dict) -> str:
        """Generate DDL for a table."""
        table_name = table['table_name']
        is_partitioned = table['is_partitioned']
        is_partition = table['is_partition']
        
        ddl = []
        
        # Skip partitions for now, we'll handle them separately
        if is_partition:
            parent_table = table['parent_table'].split('.')[-1] if table['parent_table'] else None
            partition_details = self.get_partition_details(table_name)
            
            if partition_details:
                ddl.append(f"-- Partition of {parent_table}")
                # Partitions don't support IF NOT EXISTS in CREATE, use DROP IF EXISTS
                ddl.append(f'DROP TABLE IF EXISTS "{self.schema}"."{table_name}" CASCADE;')
                ddl.append(f'CREATE TABLE "{self.schema}"."{table_name}" PARTITION OF "{self.schema}"."{parent_table}"')
                ddl.append(f"    {partition_details['partition_bound']};")
            
            return '\n'.join(ddl)
        
        # Get columns
        columns = self.get_columns(table_name)
        
        # Build CREATE TABLE statement with IF NOT EXISTS
        ddl.append(f'CREATE TABLE IF NOT EXISTS "{self.schema}"."{table_name}" (')
        
        column_defs = []
        for column in columns:
            # Check if column uses a sequence
            seq_info = self.get_sequence_info(table_name, column['column_name'])
            col_ddl = self.generate_column_ddl(column, seq_info)
            column_defs.append(f"    {col_ddl}")
        
        # Add primary key constraint inline if exists
        pk_info = self.get_primary_keys(table_name)
        if pk_info:
            pk_cols = ', '.join([f'"{col}"' for col in pk_info['column_names']])
            column_defs.append(f'    CONSTRAINT "{pk_info["constraint_name"]}" PRIMARY KEY ({pk_cols})')
        
        ddl.append(',\n'.join(column_defs))
        ddl.append(')')
        
        # Add partition clause if partitioned
        if is_partitioned:
            partition_info = self.get_partition_info(table_name)
            if partition_info and partition_info['partition_strategy']:
                ddl.append(f" PARTITION BY {partition_info['partition_strategy']}")
        
        ddl.append(';')
        
        # Add table comment if exists
        if table.get('comment'):
            comment_ddl = f"COMMENT ON TABLE \"{self.schema}\".\"{table_name}\" IS '{table['comment']}';"
            ddl.append('\n' + comment_ddl)
        
        # Add column comments
        for column in columns:
            if column.get('comment'):
                comment_ddl = f"COMMENT ON COLUMN \"{self.schema}\".\"{table_name}\".\"{column['column_name']}\" IS '{column['comment']}';"
                ddl.append(comment_ddl)
        
        return '\n'.join(ddl)
    
    def generate_foreign_key_ddl(self, fk: Dict) -> str:
        """Generate DDL for a foreign key constraint."""
        table_name = fk['table_name']
        constraint_name = fk['constraint_name']
        columns = ', '.join([f'"{col}"' for col in fk['column_names']])
        ref_table = fk['foreign_table_name']
        ref_schema = fk['foreign_schema']
        ref_columns = ', '.join([f'"{col}"' for col in fk['foreign_column_names']])
        
        # ALTER TABLE ADD CONSTRAINT doesn't support IF NOT EXISTS
        # Use DO block to check if constraint exists
        ddl = f'DO $$ BEGIN\n'
        ddl += f'    IF NOT EXISTS (\n'
        ddl += f'        SELECT 1 FROM pg_constraint\n'
        ddl += f'        WHERE conname = \'{constraint_name}\'\n'
        ddl += f'        AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = \'{self.schema}\')\n'
        ddl += f'    ) THEN\n'
        ddl += f'        ALTER TABLE "{self.schema}"."{table_name}"\n'
        ddl += f'        ADD CONSTRAINT "{constraint_name}" FOREIGN KEY ({columns})\n'
        ddl += f'        REFERENCES "{ref_schema}"."{ref_table}" ({ref_columns})'
        
        if fk['on_update'] != 'NO ACTION':
            ddl += f"\n        ON UPDATE {fk['on_update']}"
        
        if fk['on_delete'] != 'NO ACTION':
            ddl += f"\n        ON DELETE {fk['on_delete']}"
        
        ddl += ';\n'
        ddl += f'    END IF;\n'
        ddl += f'END $$;'
        
        return ddl
    
    def generate_user_type_ddl(self, user_type: Dict) -> str:
        """Generate DDL for user-defined types."""
        type_name = user_type['type_name']
        type_kind = user_type['type_kind']
        
        ddl = []
        
        if type_kind == 'enum':
            enum_values = self.get_enum_values(type_name)
            values_str = ', '.join([f"'{val}'" for val in enum_values])
            # ENUMs don't support CREATE OR REPLACE, use DROP IF EXISTS
            ddl.append(f'DROP TYPE IF EXISTS "{self.schema}"."{type_name}" CASCADE;')
            ddl.append(f'CREATE TYPE "{self.schema}"."{type_name}" AS ENUM ({values_str});')
        
        elif type_kind == 'composite':
            attributes = self.get_composite_type_attributes(type_name)
            # Composite types don't support CREATE OR REPLACE
            ddl.append(f'DROP TYPE IF EXISTS "{self.schema}"."{type_name}" CASCADE;')
            ddl.append(f'CREATE TYPE "{self.schema}"."{type_name}" AS (')
            attr_defs = []
            for attr in attributes:
                attr_defs.append(f'    "{attr["attribute_name"]}" {attr["data_type"]}')
            ddl.append(',\n'.join(attr_defs))
            ddl.append(');')
        
        elif type_kind == 'domain':
            domain_info = self.get_domain_info(type_name)
            # Domains don't support CREATE OR REPLACE
            ddl.append(f'DROP DOMAIN IF EXISTS "{self.schema}"."{type_name}" CASCADE;')
            domain_ddl = f'CREATE DOMAIN "{self.schema}"."{type_name}" AS {domain_info["base_type"]}'
            
            if domain_info['is_not_null']:
                domain_ddl += ' NOT NULL'
            
            if domain_info['default_value']:
                domain_ddl += f" DEFAULT {domain_info['default_value']}"
            
            if domain_info.get('check_constraint'):
                domain_ddl += f" {domain_info['check_constraint']}"
            
            ddl.append(domain_ddl + ';')
        
        # Add comment if exists
        if user_type.get('comment'):
            ddl.append(f"COMMENT ON TYPE \"{self.schema}\".\"{type_name}\" IS '{user_type['comment']}';")
        
        return '\n'.join(ddl)
    
    def generate_index_ddl(self, index: Dict) -> str:
        """Generate DDL for an index."""
        index_name = index['index_name']
        index_def = index['index_definition']
        
        # Add IF NOT EXISTS to the index definition
        # Replace "CREATE INDEX" or "CREATE UNIQUE INDEX" with IF NOT EXISTS version
        if index_def.startswith('CREATE UNIQUE INDEX'):
            ddl = index_def.replace('CREATE UNIQUE INDEX', 'CREATE UNIQUE INDEX IF NOT EXISTS', 1)
        elif index_def.startswith('CREATE INDEX'):
            ddl = index_def.replace('CREATE INDEX', 'CREATE INDEX IF NOT EXISTS', 1)
        else:
            ddl = index_def
        
        ddl += ';'
        
        if index.get('comment'):
            ddl += f"\nCOMMENT ON INDEX \"{self.schema}\".\"{index_name}\" IS '{index['comment']}';"
        
        return ddl
    
    def generate_sequence_ddl(self, sequence: Dict) -> str:
        """Generate DDL for a standalone sequence."""
        seq_name = sequence['sequence_name']
        
        ddl = f'CREATE SEQUENCE IF NOT EXISTS "{self.schema}"."{seq_name}"'
        
        if sequence.get('data_type') and sequence['data_type'] != 'bigint':
            ddl += f" AS {sequence['data_type']}"
        
        if sequence.get('increment_by') and sequence['increment_by'] != 1:
            ddl += f" INCREMENT BY {sequence['increment_by']}"
        
        if sequence.get('min_value'):
            ddl += f" MINVALUE {sequence['min_value']}"
        
        if sequence.get('max_value'):
            ddl += f" MAXVALUE {sequence['max_value']}"
        
        if sequence.get('start_value') and sequence['start_value'] != 1:
            ddl += f" START WITH {sequence['start_value']}"
        
        if sequence.get('cache_value') and sequence['cache_value'] != 1:
            ddl += f" CACHE {sequence['cache_value']}"
        
        if sequence.get('is_cycle'):
            ddl += " CYCLE"
        
        ddl += ';'
        
        if sequence.get('comment'):
            ddl += f"\nCOMMENT ON SEQUENCE \"{self.schema}\".\"{seq_name}\" IS '{sequence['comment']}';"
        
        return ddl
    
    def generate_foreign_table_ddl(self, ftable: Dict) -> str:
        """Generate DDL for a foreign table."""
        table_name = ftable['foreign_table_name']
        server_name = ftable['server_name']
        
        # Foreign tables don't support IF NOT EXISTS, use DROP IF EXISTS
        ddl = f'DROP FOREIGN TABLE IF EXISTS "{self.schema}"."{table_name}" CASCADE;\n'
        ddl += f'CREATE FOREIGN TABLE "{self.schema}"."{table_name}" (\n'
        
        column_defs = []
        if ftable['column_names'] and ftable['column_types']:
            for col_name, col_type in zip(ftable['column_names'], ftable['column_types']):
                column_defs.append(f'    "{col_name}" {col_type}')
        
        ddl += ',\n'.join(column_defs)
        ddl += f'\n) SERVER "{server_name}"'
        
        # Add foreign table options (with error handling)
        try:
            options = self.get_foreign_table_options(table_name)
            if options:
                option_strs = [f"{opt['option_name']} '{opt['option_value']}'" for opt in options]
                ddl += '\nOPTIONS (' + ', '.join(option_strs) + ')'
        except Exception as e:
            # If options can't be retrieved, continue without them
            print(f"Warning: Could not retrieve options for foreign table {table_name}: {e}", file=sys.stderr)
        
        ddl += ';'
        
        if ftable.get('comment'):
            ddl += f"\nCOMMENT ON FOREIGN TABLE \"{self.schema}\".\"{table_name}\" IS '{ftable['comment']}';"
        
        return ddl
    
    def generate_extension_ddl(self, extension: Dict) -> str:
        """Generate DDL for an extension."""
        ext_name = extension['extension_name']
        
        ddl = f'CREATE EXTENSION IF NOT EXISTS "{ext_name}"'
        
        if extension.get('schema') and extension['schema'] != 'public':
            ddl += f' SCHEMA "{extension["schema"]}"'
        
        if extension.get('version'):
            ddl += f" VERSION '{extension['version']}'"
        
        ddl += ';'
        
        if extension.get('comment'):
            ddl += f"\nCOMMENT ON EXTENSION \"{ext_name}\" IS '{extension['comment']}';"
        
        return ddl
    
    def generate_grant_ddl(self, grants: List[Dict], object_type: str = 'table') -> List[str]:
        """Generate GRANT statements for objects."""
        ddl_list = []
        
        # Group grants by object and grantee
        grant_groups = defaultdict(lambda: defaultdict(list))
        
        for grant in grants:
            obj_name = grant.get('object_name') or grant.get('sequence_name')
            grantee = grant['grantee']
            privilege = grant['privilege_type']
            
            # Skip default public grants to avoid clutter
            if grantee == 'public' and privilege in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                continue
            
            grant_groups[obj_name][grantee].append({
                'privilege': privilege,
                'is_grantable': grant.get('is_grantable', False),
                'object_type': grant.get('object_type', object_type)
            })
        
        # Generate GRANT statements
        for obj_name, grantees in grant_groups.items():
            for grantee, privileges in grantees.items():
                # Group privileges
                privs = [p['privilege'] for p in privileges]
                is_grantable = any(p['is_grantable'] for p in privileges)
                obj_type = privileges[0]['object_type'] if privileges else object_type
                
                privs_str = ', '.join(sorted(set(privs)))
                
                if obj_type == 'sequence':
                    ddl = f'GRANT {privs_str} ON SEQUENCE "{self.schema}"."{obj_name}" TO {grantee}'
                else:
                    ddl = f'GRANT {privs_str} ON {obj_type.upper()} "{self.schema}"."{obj_name}" TO {grantee}'
                
                if is_grantable:
                    ddl += ' WITH GRANT OPTION'
                
                ddl += ';'
                ddl_list.append(ddl)
        
        return ddl_list
    
    def sort_tables_by_dependencies(self, tables: List[Dict]) -> List[Dict]:
        """
        Sort tables by foreign key dependencies.
        Tables with no dependencies come first.
        """
        # Build dependency graph
        table_names = {t['table_name'] for t in tables if not t['is_partition']}
        dependencies = defaultdict(set)
        
        # Get all foreign keys
        all_fks = self.get_foreign_keys()
        
        for fk in all_fks:
            table = fk['table_name']
            ref_table = fk['foreign_table_name']
            
            # Only track dependencies within our table set
            if table in table_names and ref_table in table_names and table != ref_table:
                dependencies[table].add(ref_table)
        
        # Topological sort
        sorted_tables = []
        visited = set()
        temp_mark = set()
        
        def visit(table_name):
            if table_name in temp_mark:
                # Circular dependency detected
                return
            if table_name in visited:
                return
            
            temp_mark.add(table_name)
            
            for dep in dependencies.get(table_name, []):
                visit(dep)
            
            temp_mark.remove(table_name)
            visited.add(table_name)
            sorted_tables.append(table_name)
        
        # Visit all tables
        for table in tables:
            if not table['is_partition']:
                visit(table['table_name'])
        
        # Create ordered list
        table_dict = {t['table_name']: t for t in tables}
        ordered_tables = []
        
        # First add non-partitions in dependency order
        for table_name in sorted_tables:
            if table_name in table_dict:
                ordered_tables.append(table_dict[table_name])
        
        # Then add partitions after their parent tables
        for table in tables:
            if table['is_partition']:
                ordered_tables.append(table)
        
        return ordered_tables
    
    def generate_ddl(self) -> str:
        """Generate complete DDL for the schema."""
        ddl_parts = []
        
        # Header
        ddl_parts.append("-- PostgreSQL DDL Generator")
        ddl_parts.append(f"-- Schema: {self.schema}")
        ddl_parts.append(f"-- Generated for PostgreSQL 18")
        ddl_parts.append("")
        
        # Extensions first
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Extensions")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        extensions = self.get_extensions()
        for extension in extensions:
            ddl_parts.append(self.generate_extension_ddl(extension))
            ddl_parts.append("")
        
        # User-defined types
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- User-Defined Types")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        user_types = self.get_user_types()
        for user_type in user_types:
            ddl_parts.append(self.generate_user_type_ddl(user_type))
            ddl_parts.append("")
        
        # Sequences (standalone)
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Sequences")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        sequences = self.get_sequences()
        for sequence in sequences:
            ddl_parts.append(self.generate_sequence_ddl(sequence))
            ddl_parts.append("")
        
        # Functions (before triggers)
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Functions")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        functions = self.get_functions()
        for function in functions:
            if function.get('function_definition'):
                ddl_parts.append(function['function_definition'] + ';')
                
                if function.get('comment'):
                    func_args = function.get('arguments', '')
                    comment_ddl = f"COMMENT ON FUNCTION \"{self.schema}\".\"{function['function_name']}\"({func_args}) IS '{function['comment']}';"
                    ddl_parts.append(comment_ddl)
                
                ddl_parts.append("")
        
        # Procedures
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Procedures")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        procedures = self.get_procedures()
        for procedure in procedures:
            if procedure.get('procedure_definition'):
                ddl_parts.append(procedure['procedure_definition'] + ';')
                
                if procedure.get('comment'):
                    proc_args = procedure.get('arguments', '')
                    comment_ddl = f"COMMENT ON PROCEDURE \"{self.schema}\".\"{procedure['procedure_name']}\"({proc_args}) IS '{procedure['comment']}';"
                    ddl_parts.append(comment_ddl)
                
                ddl_parts.append("")
        
        # Tables
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Tables")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        tables = self.get_tables()
        sorted_tables = self.sort_tables_by_dependencies(tables)
        
        for table in sorted_tables:
            ddl_parts.append(self.generate_table_ddl(table))
            ddl_parts.append("")
        
        # Foreign Tables
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Foreign Tables")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        try:
            foreign_tables = self.get_foreign_tables()
            for ftable in foreign_tables:
                try:
                    ddl_parts.append(self.generate_foreign_table_ddl(ftable))
                    ddl_parts.append("")
                except Exception as e:
                    print(f"Warning: Could not generate DDL for foreign table {ftable.get('foreign_table_name', 'unknown')}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not retrieve foreign tables: {e}", file=sys.stderr)
        
        # Indexes
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Indexes")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        indexes = self.get_indexes()
        for index in indexes:
            ddl_parts.append(self.generate_index_ddl(index))
            ddl_parts.append("")
        
        # Foreign Keys
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Foreign Keys")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        all_fks = self.get_foreign_keys()
        for fk in all_fks:
            ddl_parts.append(self.generate_foreign_key_ddl(fk))
            ddl_parts.append("")
        
        # Triggers
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Triggers")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        all_triggers = self.get_triggers()
        for trigger in all_triggers:
            if trigger.get('trigger_definition'):
                # Triggers don't support IF NOT EXISTS, use CREATE OR REPLACE or DROP IF EXISTS
                trigger_def = trigger['trigger_definition']
                trigger_name = trigger.get('trigger_name', '')
                table_name_in_trigger = trigger.get('table_name', '')
                
                # Add DROP IF EXISTS before CREATE TRIGGER
                if trigger_name and table_name_in_trigger:
                    ddl_parts.append(f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{self.schema}"."{table_name_in_trigger}" CASCADE;')
                
                ddl_parts.append(trigger_def + ';')
                ddl_parts.append("")
        
        # Views
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Views")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        views = self.get_views()
        for view in views:
            if view.get('view_definition'):
                # Use CREATE OR REPLACE VIEW
                ddl_parts.append(f'CREATE OR REPLACE VIEW "{self.schema}"."{view["view_name"]}" AS')
                ddl_parts.append(view['view_definition'])
                
                if view.get('comment'):
                    comment_ddl = f"COMMENT ON VIEW \"{self.schema}\".\"{view['view_name']}\" IS '{view['comment']}';"
                    ddl_parts.append(comment_ddl)
                
                ddl_parts.append("")
        
        # Materialized Views
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Materialized Views")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        matviews = self.get_materialized_views()
        for matview in matviews:
            if matview.get('matview_definition'):
                # Materialized views don't support CREATE OR REPLACE, use DROP IF EXISTS
                ddl_parts.append(f'DROP MATERIALIZED VIEW IF EXISTS "{self.schema}"."{matview["matview_name"]}" CASCADE;')
                ddl_parts.append(f'CREATE MATERIALIZED VIEW "{self.schema}"."{matview["matview_name"]}" AS')
                ddl_parts.append(matview['matview_definition'])
                
                if matview.get('comment'):
                    comment_ddl = f"COMMENT ON MATERIALIZED VIEW \"{self.schema}\".\"{matview['matview_name']}\" IS '{matview['comment']}';"
                    ddl_parts.append(comment_ddl)
                
                ddl_parts.append("")
        
        # Grants/Permissions
        ddl_parts.append("-- ========================================")
        ddl_parts.append("-- Grants and Permissions")
        ddl_parts.append("-- ========================================")
        ddl_parts.append("")
        
        try:
            # Table/View grants
            table_grants = self.get_table_grants()
            grant_ddls = self.generate_grant_ddl(table_grants, 'table')
            for grant_ddl in grant_ddls:
                ddl_parts.append(grant_ddl)
            
            if grant_ddls:
                ddl_parts.append("")
        except Exception as e:
            print(f"Warning: Could not retrieve table grants: {e}", file=sys.stderr)
        
        try:
            # Sequence grants
            seq_grants = self.get_sequence_grants()
            seq_grant_ddls = self.generate_grant_ddl(seq_grants, 'sequence')
            for grant_ddl in seq_grant_ddls:
                ddl_parts.append(grant_ddl)
            
            if seq_grant_ddls:
                ddl_parts.append("")
        except Exception as e:
            print(f"Warning: Could not retrieve sequence grants: {e}", file=sys.stderr)
        
        return '\n'.join(ddl_parts)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Generate DDL for PostgreSQL 18 database schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate DDL for public schema
  %(prog)s -H localhost -d mydb -U postgres -s public
  
  # Generate DDL and save to file
  %(prog)s -H localhost -d mydb -U postgres -s public -o schema.sql
  
  # Use environment variables for password
  export PGPASSWORD=mypassword
  %(prog)s -H localhost -d mydb -U postgres
        """
    )
    
    parser.add_argument('-H', '--host', default='localhost',
                        help='PostgreSQL host (default: localhost)')
    parser.add_argument('-p', '--port', default='5432',
                        help='PostgreSQL port (default: 5432)')
    parser.add_argument('-d', '--database', required=True,
                        help='Database name')
    parser.add_argument('-U', '--user', required=True,
                        help='Database user')
    parser.add_argument('-W', '--password', 
                        help='Database password (or use PGPASSWORD env var)')
    parser.add_argument('-s', '--schema', default='public',
                        help='Schema name (default: public)')
    parser.add_argument('-o', '--output',
                        help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Get password from args or environment
    import os
    password = args.password or os.environ.get('PGPASSWORD')
    
    if not password:
        import getpass
        password = getpass.getpass('Password: ')
    
    # Connection parameters
    conn_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': password
    }
    
    # Generate DDL
    generator = PostgresDDLGenerator(conn_params, args.schema)
    
    try:
        generator.connect()
        ddl = generator.generate_ddl()
        
        # Output DDL
        if args.output:
            with open(args.output, 'w') as f:
                f.write(ddl)
            print(f"DDL written to {args.output}", file=sys.stderr)
        else:
            print(ddl)
    
    except Exception as e:
        print(f"Error generating DDL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        generator.disconnect()


if __name__ == '__main__':
    main()
