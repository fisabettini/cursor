#!/usr/bin/env python3
"""
PostgreSQL DDL Generator
Generates DDL statements for tables and related objects (constraints, indexes, triggers, trigger functions)
from a specific schema.
"""

import argparse
import sys
import psycopg2
from psycopg2.extras import RealDictCursor


class PostgreSQLDDLGenerator:
    def __init__(self, host, port, database, user, password, schema):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print(f"Connected to database: {self.database}", file=sys.stderr)
        except Exception as e:
            print(f"Error connecting to database: {e}", file=sys.stderr)
            sys.exit(1)

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_tables(self):
        """Get all tables in the specified schema."""
        query = """
            SELECT 
                table_name,
                obj_description((quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass, 'pg_class') as table_comment
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()

    def get_table_columns(self, table_name):
        """Get columns for a specific table."""
        query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.is_nullable,
                c.column_default,
                c.udt_name,
                pgd.description as column_comment
            FROM information_schema.columns c
            LEFT JOIN pg_catalog.pg_statio_all_tables st 
                ON c.table_schema = st.schemaname 
                AND c.table_name = st.relname
            LEFT JOIN pg_catalog.pg_description pgd 
                ON pgd.objoid = st.relid
                AND pgd.objsubid = c.ordinal_position
            WHERE c.table_schema = %s
            AND c.table_name = %s
            ORDER BY c.ordinal_position;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def format_column_type(self, col):
        """Format column data type with proper precision/length."""
        data_type = col['data_type']
        
        # Check if this is a SERIAL or BIGSERIAL type
        # (integer/bigint with nextval default)
        if col['column_default'] and 'nextval(' in col['column_default'].lower():
            if data_type == 'integer':
                return 'SERIAL'
            elif data_type == 'bigint':
                return 'BIGSERIAL'
            elif data_type == 'smallint':
                return 'SMALLSERIAL'
        
        if data_type == 'character varying':
            if col['character_maximum_length']:
                return f"VARCHAR({col['character_maximum_length']})"
            return "VARCHAR"
        elif data_type == 'character':
            if col['character_maximum_length']:
                return f"CHAR({col['character_maximum_length']})"
            return "CHAR"
        elif data_type == 'numeric':
            if col['numeric_precision'] and col['numeric_scale']:
                return f"NUMERIC({col['numeric_precision']},{col['numeric_scale']})"
            elif col['numeric_precision']:
                return f"NUMERIC({col['numeric_precision']})"
            return "NUMERIC"
        elif data_type == 'ARRAY':
            return col['udt_name'].replace('_', '', 1).upper() + '[]'
        elif data_type == 'USER-DEFINED':
            return col['udt_name']
        else:
            return data_type.upper()

    def generate_create_table_ddl(self, table_name):
        """Generate CREATE TABLE DDL statement."""
        columns = self.get_table_columns(table_name)
        
        if not columns:
            return None
        
        ddl = f"CREATE TABLE {self.schema}.{table_name} (\n"
        column_defs = []
        
        for col in columns:
            col_type = self.format_column_type(col)
            col_def = f"    {col['column_name']} {col_type}"
            
            # Check if this is a SERIAL type (which already implies NOT NULL)
            is_serial = col_type in ('SERIAL', 'BIGSERIAL', 'SMALLSERIAL')
            
            # Add NOT NULL constraint (skip for SERIAL types as they're implicitly NOT NULL)
            if col['is_nullable'] == 'NO' and not is_serial:
                col_def += " NOT NULL"
            
            # Add DEFAULT constraint (skip for SERIAL types as the default is already handled)
            if col['column_default'] and not is_serial:
                col_def += f" DEFAULT {col['column_default']}"
            
            column_defs.append(col_def)
        
        ddl += ",\n".join(column_defs)
        ddl += "\n);\n"
        
        # Add table comment if exists
        table_info = self.get_table_comment(table_name)
        if table_info:
            ddl += f"\nCOMMENT ON TABLE {self.schema}.{table_name} IS '{table_info}';\n"
        
        # Add column comments
        for col in columns:
            if col['column_comment']:
                comment = col['column_comment'].replace("'", "''")
                ddl += f"COMMENT ON COLUMN {self.schema}.{table_name}.{col['column_name']} IS '{comment}';\n"
        
        return ddl

    def get_table_comment(self, table_name):
        """Get table comment."""
        query = """
            SELECT obj_description((quote_ident(%s) || '.' || quote_ident(%s))::regclass, 'pg_class') as comment;
        """
        self.cursor.execute(query, (self.schema, table_name))
        result = self.cursor.fetchone()
        return result['comment'] if result else None

    def get_primary_keys(self, table_name):
        """Get primary key constraints for a table."""
        query = """
            SELECT
                con.conname AS constraint_name,
                array_agg(att.attname ORDER BY array_position(con.conkey, att.attnum)) AS columns
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN pg_attribute att ON att.attrelid = con.conrelid 
                AND att.attnum = ANY(con.conkey)
            WHERE nsp.nspname = %s
            AND rel.relname = %s
            AND con.contype = 'p'
            GROUP BY con.conname;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def get_foreign_keys(self, table_name):
        """Get foreign key constraints for a table."""
        query = """
            SELECT
                con.conname AS constraint_name,
                array_agg(att.attname ORDER BY array_position(con.conkey, att.attnum)) AS columns,
                nsp2.nspname AS foreign_schema,
                rel2.relname AS foreign_table,
                array_agg(att2.attname ORDER BY array_position(con.confkey, att2.attnum)) AS foreign_columns,
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
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN pg_attribute att ON att.attrelid = con.conrelid 
                AND att.attnum = ANY(con.conkey)
            JOIN pg_class rel2 ON rel2.oid = con.confrelid
            JOIN pg_namespace nsp2 ON nsp2.oid = rel2.relnamespace
            JOIN pg_attribute att2 ON att2.attrelid = con.confrelid 
                AND att2.attnum = ANY(con.confkey)
            WHERE nsp.nspname = %s
            AND rel.relname = %s
            AND con.contype = 'f'
            GROUP BY con.conname, nsp2.nspname, rel2.relname, con.confupdtype, con.confdeltype;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def get_unique_constraints(self, table_name):
        """Get unique constraints for a table."""
        query = """
            SELECT
                con.conname AS constraint_name,
                array_agg(att.attname ORDER BY array_position(con.conkey, att.attnum)) AS columns
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN pg_attribute att ON att.attrelid = con.conrelid 
                AND att.attnum = ANY(con.conkey)
            WHERE nsp.nspname = %s
            AND rel.relname = %s
            AND con.contype = 'u'
            GROUP BY con.conname;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def get_check_constraints(self, table_name):
        """Get check constraints for a table."""
        query = """
            SELECT
                con.conname AS constraint_name,
                pg_get_constraintdef(con.oid) AS definition
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = %s
            AND rel.relname = %s
            AND con.contype = 'c';
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def generate_constraint_ddl(self, table_name):
        """Generate DDL for all constraints."""
        ddl = ""
        
        # Primary keys
        pks = self.get_primary_keys(table_name)
        for pk in pks:
            columns = ', '.join(pk['columns'])
            ddl += f"ALTER TABLE {self.schema}.{table_name} ADD CONSTRAINT {pk['constraint_name']} PRIMARY KEY ({columns});\n"
        
        # Foreign keys
        fks = self.get_foreign_keys(table_name)
        for fk in fks:
            columns = ', '.join(fk['columns'])
            foreign_columns = ', '.join(fk['foreign_columns'])
            ddl += f"ALTER TABLE {self.schema}.{table_name} ADD CONSTRAINT {fk['constraint_name']} "
            ddl += f"FOREIGN KEY ({columns}) REFERENCES {fk['foreign_schema']}.{fk['foreign_table']} ({foreign_columns})"
            if fk['on_update'] != 'NO ACTION':
                ddl += f" ON UPDATE {fk['on_update']}"
            if fk['on_delete'] != 'NO ACTION':
                ddl += f" ON DELETE {fk['on_delete']}"
            ddl += ";\n"
        
        # Unique constraints
        uqs = self.get_unique_constraints(table_name)
        for uq in uqs:
            columns = ', '.join(uq['columns'])
            ddl += f"ALTER TABLE {self.schema}.{table_name} ADD CONSTRAINT {uq['constraint_name']} UNIQUE ({columns});\n"
        
        # Check constraints
        cks = self.get_check_constraints(table_name)
        for ck in cks:
            ddl += f"ALTER TABLE {self.schema}.{table_name} ADD CONSTRAINT {ck['constraint_name']} {ck['definition']};\n"
        
        return ddl

    def get_indexes(self, table_name):
        """Get indexes for a table (excluding primary key indexes)."""
        query = """
            SELECT
                i.relname AS index_name,
                pg_get_indexdef(idx.indexrelid) AS definition,
                obj_description(idx.indexrelid, 'pg_class') AS comment
            FROM pg_index idx
            JOIN pg_class i ON i.oid = idx.indexrelid
            JOIN pg_class t ON t.oid = idx.indrelid
            JOIN pg_namespace nsp ON nsp.oid = t.relnamespace
            WHERE nsp.nspname = %s
            AND t.relname = %s
            AND NOT idx.indisprimary
            ORDER BY i.relname;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def generate_index_ddl(self, table_name):
        """Generate DDL for indexes."""
        indexes = self.get_indexes(table_name)
        ddl = ""
        
        for idx in indexes:
            ddl += f"{idx['definition']};\n"
            if idx['comment']:
                comment = idx['comment'].replace("'", "''")
                ddl += f"COMMENT ON INDEX {self.schema}.{idx['index_name']} IS '{comment}';\n"
        
        return ddl

    def get_trigger_functions(self):
        """Get all trigger functions used by triggers in the schema."""
        query = """
            SELECT DISTINCT
                p.proname AS function_name,
                pg_get_functiondef(p.oid) AS definition,
                obj_description(p.oid, 'pg_proc') AS comment
            FROM pg_trigger t
            JOIN pg_class rel ON rel.oid = t.tgrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN pg_proc p ON p.oid = t.tgfoid
            WHERE nsp.nspname = %s
            AND NOT t.tgisinternal
            ORDER BY p.proname;
        """
        self.cursor.execute(query, (self.schema,))
        return self.cursor.fetchall()

    def generate_trigger_function_ddl(self):
        """Generate DDL for trigger functions."""
        functions = self.get_trigger_functions()
        ddl = ""
        
        for func in functions:
            ddl += f"{func['definition']};\n\n"
            if func['comment']:
                # Extract schema from function definition if exists
                comment = func['comment'].replace("'", "''")
                ddl += f"COMMENT ON FUNCTION {self.schema}.{func['function_name']}() IS '{comment}';\n\n"
        
        return ddl

    def get_triggers(self, table_name):
        """Get triggers for a table."""
        query = """
            SELECT
                t.tgname AS trigger_name,
                pg_get_triggerdef(t.oid) AS definition,
                obj_description(t.oid, 'pg_trigger') AS comment
            FROM pg_trigger t
            JOIN pg_class rel ON rel.oid = t.tgrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = %s
            AND rel.relname = %s
            AND NOT t.tgisinternal
            ORDER BY t.tgname;
        """
        self.cursor.execute(query, (self.schema, table_name))
        return self.cursor.fetchall()

    def generate_trigger_ddl(self, table_name):
        """Generate DDL for triggers."""
        triggers = self.get_triggers(table_name)
        ddl = ""
        
        for trg in triggers:
            ddl += f"{trg['definition']};\n"
            if trg['comment']:
                comment = trg['comment'].replace("'", "''")
                ddl += f"COMMENT ON TRIGGER {trg['trigger_name']} ON {self.schema}.{table_name} IS '{comment}';\n"
        
        return ddl

    def generate_schema_ddl(self):
        """Generate complete DDL for the schema."""
        print(f"-- DDL for schema: {self.schema}")
        print(f"-- Database: {self.database}")
        print(f"-- Generated by PostgreSQL DDL Generator\n")
        
        tables = self.get_tables()
        
        if not tables:
            print(f"-- No tables found in schema '{self.schema}'", file=sys.stderr)
            return
        
        # Generate trigger functions first (they need to exist before triggers)
        print("-- =============================================")
        print("-- Trigger Functions")
        print("-- =============================================\n")
        trigger_func_ddl = self.generate_trigger_function_ddl()
        if trigger_func_ddl:
            print(trigger_func_ddl)
        
        # Generate table DDLs
        print("-- =============================================")
        print("-- Tables")
        print("-- =============================================\n")
        for table in tables:
            table_name = table['table_name']
            print(f"-- Table: {table_name}")
            print(self.generate_create_table_ddl(table_name))
        
        # Generate constraints
        print("\n-- =============================================")
        print("-- Constraints")
        print("-- =============================================\n")
        for table in tables:
            table_name = table['table_name']
            constraint_ddl = self.generate_constraint_ddl(table_name)
            if constraint_ddl:
                print(f"-- Constraints for table: {table_name}")
                print(constraint_ddl)
        
        # Generate indexes
        print("\n-- =============================================")
        print("-- Indexes")
        print("-- =============================================\n")
        for table in tables:
            table_name = table['table_name']
            index_ddl = self.generate_index_ddl(table_name)
            if index_ddl:
                print(f"-- Indexes for table: {table_name}")
                print(index_ddl)
        
        # Generate triggers
        print("\n-- =============================================")
        print("-- Triggers")
        print("-- =============================================\n")
        for table in tables:
            table_name = table['table_name']
            trigger_ddl = self.generate_trigger_ddl(table_name)
            if trigger_ddl:
                print(f"-- Triggers for table: {table_name}")
                print(trigger_ddl)


def main():
    parser = argparse.ArgumentParser(
        description='Generate DDL statements for PostgreSQL schema objects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate DDL for 'public' schema
  python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s public

  # Generate DDL and save to file
  python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s myschema > schema.sql

  # Using environment variables for password
  PGPASSWORD=secret python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s public
        """
    )
    
    parser.add_argument('-H', '--host', default='localhost', help='Database host (default: localhost)')
    parser.add_argument('-p', '--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('-d', '--database', required=True, help='Database name')
    parser.add_argument('-U', '--user', required=True, help='Database user')
    parser.add_argument('-W', '--password', help='Database password (or use PGPASSWORD env var)')
    parser.add_argument('-s', '--schema', required=True, help='Schema name to generate DDL for')
    
    args = parser.parse_args()
    
    # Get password from environment if not provided
    import os
    password = args.password or os.environ.get('PGPASSWORD', '')
    
    if not password:
        print("Error: Password required. Use -W option or set PGPASSWORD environment variable.", file=sys.stderr)
        sys.exit(1)
    
    generator = PostgreSQLDDLGenerator(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=password,
        schema=args.schema
    )
    
    try:
        generator.connect()
        generator.generate_schema_ddl()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        generator.close()


if __name__ == '__main__':
    main()
