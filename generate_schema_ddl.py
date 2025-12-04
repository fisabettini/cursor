#!/usr/bin/env python3
"""
PostgreSQL Schema DDL Generator

This script generates DDL statements for all objects in a specified PostgreSQL schema,
including tables, constraints, indexes, triggers, sequences, views, and trigger functions.
It ensures proper ordering with foreign keys referencing previously created primary keys,
and handles identity column sequences as serial/bigserial types.
"""

import argparse
import sys
from typing import List, Dict, Set, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor


class PostgreSQLDDLGenerator:
    """Generate DDL statements for PostgreSQL schema objects."""
    
    def __init__(self, connection_params: Dict[str, str], schema_name: str):
        """
        Initialize the DDL generator.
        
        Args:
            connection_params: Database connection parameters
            schema_name: Target schema name
        """
        self.connection_params = connection_params
        self.schema_name = schema_name
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}", file=sys.stderr)
            sys.exit(1)
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_serial_sequences(self) -> Set[str]:
        """
        Get sequences that are owned by table columns (serial/bigserial).
        These should not be created separately.
        
        Returns:
            Set of sequence names that are owned by columns
        """
        query = """
            SELECT s.relname as sequence_name
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON d.refobjid = t.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            JOIN pg_namespace n ON s.relnamespace = n.oid
            WHERE s.relkind = 'S'
              AND n.nspname = %s
              AND d.deptype = 'a'  -- auto dependency (owned by column)
        """
        self.cursor.execute(query, (self.schema_name,))
        return {row['sequence_name'] for row in self.cursor.fetchall()}
    
    def get_column_sequence_info(self) -> Dict[Tuple[str, str], str]:
        """
        Get mapping of (table, column) to sequence name for serial columns.
        
        Returns:
            Dictionary mapping (table_name, column_name) to sequence_name
        """
        query = """
            SELECT 
                t.relname as table_name,
                a.attname as column_name,
                s.relname as sequence_name
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON d.refobjid = t.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            JOIN pg_namespace n ON s.relnamespace = n.oid
            WHERE s.relkind = 'S'
              AND n.nspname = %s
              AND d.deptype = 'a'
        """
        self.cursor.execute(query, (self.schema_name,))
        return {(row['table_name'], row['column_name']): row['sequence_name'] 
                for row in self.cursor.fetchall()}
    
    def get_trigger_functions(self) -> List[str]:
        """
        Generate DDL for trigger functions in the schema.
        
        Returns:
            List of CREATE FUNCTION DDL statements
        """
        query = """
            SELECT 
                p.proname as function_name,
                pg_get_functiondef(p.oid) as definition
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = %s
              AND p.prorettype = 'trigger'::regtype
            ORDER BY p.proname
        """
        self.cursor.execute(query, (self.schema_name,))
        
        ddl_statements = []
        for row in self.cursor.fetchall():
            ddl_statements.append(f"-- Function: {self.schema_name}.{row['function_name']}")
            ddl_statements.append(row['definition'] + ";")
            ddl_statements.append("")
        
        return ddl_statements
    
    def get_standalone_sequences(self, serial_sequences: Set[str]) -> List[str]:
        """
        Generate DDL for sequences that are not part of serial/bigserial columns.
        
        Args:
            serial_sequences: Set of sequence names owned by columns
            
        Returns:
            List of CREATE SEQUENCE DDL statements
        """
        query = """
            SELECT 
                c.relname as sequence_name,
                s.seqstart as start_value,
                s.seqincrement as increment_by,
                s.seqmin as min_value,
                s.seqmax as max_value,
                s.seqcache as cache_value,
                s.seqcycle as is_cycle
            FROM pg_class c
            JOIN pg_sequence s ON c.oid = s.seqrelid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relkind = 'S'
              AND n.nspname = %s
            ORDER BY c.relname
        """
        self.cursor.execute(query, (self.schema_name,))
        
        ddl_statements = []
        for row in self.cursor.fetchall():
            if row['sequence_name'] not in serial_sequences:
                seq_name = f"{self.schema_name}.{row['sequence_name']}"
                ddl = [f"-- Sequence: {seq_name}"]
                ddl.append(f"CREATE SEQUENCE {seq_name}")
                ddl.append(f"    INCREMENT BY {row['increment_by']}")
                ddl.append(f"    MINVALUE {row['min_value']}")
                ddl.append(f"    MAXVALUE {row['max_value']}")
                ddl.append(f"    START WITH {row['start_value']}")
                ddl.append(f"    CACHE {row['cache_value']}")
                if row['is_cycle']:
                    ddl.append("    CYCLE")
                else:
                    ddl.append("    NO CYCLE")
                ddl.append(";")
                ddl.append("")
                ddl_statements.extend(ddl)
        
        return ddl_statements
    
    def get_column_default_type(self, table_name: str, column_name: str, 
                                 data_type: str, column_default: str,
                                 column_sequence_info: Dict) -> Tuple[str, str]:
        """
        Determine the actual data type and default for a column.
        Converts integer columns with sequence defaults to serial/bigserial.
        
        Returns:
            Tuple of (data_type, default_value)
        """
        key = (table_name, column_name)
        
        # Check if this column uses a sequence
        if key in column_sequence_info and column_default:
            seq_name = column_sequence_info[key]
            # Check if the default is nextval for this sequence
            if f"nextval('{self.schema_name}.{seq_name}'::regclass)" in column_default or \
               f"nextval('\"{self.schema_name}\".\"{seq_name}\"'::regclass)" in column_default:
                # Convert to serial types
                if data_type == 'integer':
                    return 'serial', None
                elif data_type == 'bigint':
                    return 'bigserial', None
                elif data_type == 'smallint':
                    return 'smallserial', None
        
        return data_type, column_default
    
    def get_table_columns(self, table_name: str, 
                          column_sequence_info: Dict) -> List[Dict]:
        """
        Get column definitions for a table.
        
        Args:
            table_name: Name of the table
            column_sequence_info: Mapping of columns to sequences
            
        Returns:
            List of column definitions
        """
        query = """
            SELECT 
                a.attname as column_name,
                pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                a.attnotnull as not_null,
                pg_get_expr(d.adbin, d.adrelid) as column_default,
                col_description(a.attrelid, a.attnum) as comment,
                a.attnum as ordinal_position
            FROM pg_attribute a
            LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = %s
              AND n.nspname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
        """
        self.cursor.execute(query, (table_name, self.schema_name))
        
        columns = []
        for row in self.cursor.fetchall():
            data_type, default_value = self.get_column_default_type(
                table_name, row['column_name'], row['data_type'],
                row['column_default'], column_sequence_info
            )
            
            col_def = {
                'name': row['column_name'],
                'type': data_type,
                'not_null': row['not_null'],
                'default': default_value,
                'comment': row['comment']
            }
            columns.append(col_def)
        
        return columns
    
    def get_table_constraints(self, table_name: str, 
                              include_foreign_keys: bool = False) -> List[Dict]:
        """
        Get constraint definitions for a table.
        
        Args:
            table_name: Name of the table
            include_foreign_keys: Whether to include foreign key constraints
            
        Returns:
            List of constraint definitions
        """
        query = """
            SELECT 
                con.conname as constraint_name,
                con.contype as constraint_type,
                pg_get_constraintdef(con.oid) as definition
            FROM pg_constraint con
            JOIN pg_class c ON con.conrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = %s
              AND n.nspname = %s
              AND con.contype IN ('p', 'u', 'c', 'f')
            ORDER BY 
                CASE con.contype
                    WHEN 'p' THEN 1
                    WHEN 'u' THEN 2
                    WHEN 'c' THEN 3
                    WHEN 'f' THEN 4
                END,
                con.conname
        """
        self.cursor.execute(query, (table_name, self.schema_name))
        
        constraints = []
        for row in self.cursor.fetchall():
            # Skip foreign keys if not requested
            if row['constraint_type'] == 'f' and not include_foreign_keys:
                continue
            
            constraint_types = {
                'p': 'PRIMARY KEY',
                'u': 'UNIQUE',
                'c': 'CHECK',
                'f': 'FOREIGN KEY'
            }
            
            constraints.append({
                'name': row['constraint_name'],
                'type': constraint_types.get(row['constraint_type'], 'UNKNOWN'),
                'definition': row['definition']
            })
        
        return constraints
    
    def get_table_dependencies(self) -> Dict[str, Set[str]]:
        """
        Get foreign key dependencies between tables.
        
        Returns:
            Dictionary mapping table names to sets of tables they depend on
        """
        query = """
            SELECT 
                c1.relname as table_name,
                c2.relname as referenced_table
            FROM pg_constraint con
            JOIN pg_class c1 ON con.conrelid = c1.oid
            JOIN pg_class c2 ON con.confrelid = c2.oid
            JOIN pg_namespace n1 ON c1.relnamespace = n1.oid
            JOIN pg_namespace n2 ON c2.relnamespace = n2.oid
            WHERE con.contype = 'f'
              AND n1.nspname = %s
              AND n2.nspname = %s
        """
        self.cursor.execute(query, (self.schema_name, self.schema_name))
        
        dependencies = {}
        for row in self.cursor.fetchall():
            table = row['table_name']
            ref_table = row['referenced_table']
            if table not in dependencies:
                dependencies[table] = set()
            dependencies[table].add(ref_table)
        
        return dependencies
    
    def topological_sort(self, dependencies: Dict[str, Set[str]], 
                         all_tables: List[str]) -> List[str]:
        """
        Sort tables in topological order based on foreign key dependencies.
        
        Args:
            dependencies: Dictionary of table dependencies
            all_tables: List of all table names
            
        Returns:
            List of table names in dependency order
        """
        # Tables with no dependencies
        no_deps = [t for t in all_tables if t not in dependencies or not dependencies[t]]
        
        # Tables with dependencies
        with_deps = [t for t in all_tables if t in dependencies and dependencies[t]]
        
        sorted_tables = []
        processed = set()
        
        # Add tables with no dependencies first
        sorted_tables.extend(no_deps)
        processed.update(no_deps)
        
        # Process remaining tables
        max_iterations = len(with_deps) * len(with_deps)
        iteration = 0
        
        while with_deps and iteration < max_iterations:
            iteration += 1
            added_this_round = []
            
            for table in with_deps:
                deps = dependencies[table]
                # Check if all dependencies are processed
                if deps.issubset(processed):
                    sorted_tables.append(table)
                    processed.add(table)
                    added_this_round.append(table)
            
            # Remove processed tables
            for table in added_this_round:
                with_deps.remove(table)
        
        # Add any remaining tables (circular dependencies)
        if with_deps:
            sorted_tables.extend(with_deps)
        
        return sorted_tables
    
    def generate_table_ddl(self, table_name: str, 
                           column_sequence_info: Dict,
                           include_foreign_keys: bool = False) -> List[str]:
        """
        Generate CREATE TABLE DDL statement.
        
        Args:
            table_name: Name of the table
            column_sequence_info: Mapping of columns to sequences
            include_foreign_keys: Whether to include foreign key constraints
            
        Returns:
            List of DDL statement lines
        """
        columns = self.get_table_columns(table_name, column_sequence_info)
        constraints = self.get_table_constraints(table_name, include_foreign_keys)
        
        ddl = [f"-- Table: {self.schema_name}.{table_name}"]
        ddl.append(f"CREATE TABLE {self.schema_name}.{table_name} (")
        
        # Column definitions
        col_defs = []
        for col in columns:
            col_def = f"    {col['name']} {col['type']}"
            
            if col['default'] and 'serial' not in col['type']:
                col_def += f" DEFAULT {col['default']}"
            
            if col['not_null']:
                col_def += " NOT NULL"
            
            col_defs.append(col_def)
        
        # Inline constraints
        for constraint in constraints:
            const_def = f"    CONSTRAINT {constraint['name']} {constraint['definition']}"
            col_defs.append(const_def)
        
        ddl.append(",\n".join(col_defs))
        ddl.append(");")
        
        # Column comments
        for col in columns:
            if col['comment']:
                escaped_comment = col['comment'].replace("'", "''")
                comment_sql = (f"COMMENT ON COLUMN {self.schema_name}.{table_name}."
                             f"{col['name']} IS '{escaped_comment}';")
                ddl.append(comment_sql)
        
        # Table comment
        self.cursor.execute("""
            SELECT obj_description(c.oid) as comment
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = %s AND n.nspname = %s
        """, (table_name, self.schema_name))
        
        row = self.cursor.fetchone()
        if row and row['comment']:
            escaped_comment = row['comment'].replace("'", "''")
            ddl.append(f"COMMENT ON TABLE {self.schema_name}.{table_name} IS "
                      f"'{escaped_comment}';")
        
        ddl.append("")
        return ddl
    
    def get_foreign_key_constraints(self) -> List[Dict]:
        """
        Get all foreign key constraints in the schema.
        
        Returns:
            List of foreign key constraint definitions
        """
        query = """
            SELECT 
                c.relname as table_name,
                con.conname as constraint_name,
                pg_get_constraintdef(con.oid) as definition
            FROM pg_constraint con
            JOIN pg_class c ON con.conrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = %s
              AND con.contype = 'f'
            ORDER BY c.relname, con.conname
        """
        self.cursor.execute(query, (self.schema_name,))
        
        foreign_keys = []
        for row in self.cursor.fetchall():
            foreign_keys.append({
                'table': row['table_name'],
                'name': row['constraint_name'],
                'definition': row['definition']
            })
        
        return foreign_keys
    
    def generate_foreign_key_ddl(self, foreign_keys: List[Dict]) -> List[str]:
        """
        Generate ALTER TABLE statements for foreign key constraints.
        
        Args:
            foreign_keys: List of foreign key definitions
            
        Returns:
            List of ALTER TABLE DDL statements
        """
        if not foreign_keys:
            return []
        
        ddl = ["-- Foreign Key Constraints"]
        for fk in foreign_keys:
            ddl.append(f"ALTER TABLE {self.schema_name}.{fk['table']}")
            ddl.append(f"    ADD CONSTRAINT {fk['name']} {fk['definition']};")
            ddl.append("")
        
        return ddl
    
    def get_indexes(self) -> List[str]:
        """
        Generate DDL for indexes (excluding primary key and unique constraint indexes).
        
        Returns:
            List of CREATE INDEX DDL statements
        """
        query = """
            SELECT 
                c.relname as table_name,
                i.relname as index_name,
                pg_get_indexdef(i.oid) as definition
            FROM pg_index ix
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_class c ON c.oid = ix.indrelid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = %s
              AND NOT ix.indisprimary
              AND NOT ix.indisunique
              AND i.relkind = 'i'
            ORDER BY c.relname, i.relname
        """
        self.cursor.execute(query, (self.schema_name,))
        
        ddl_statements = []
        for row in self.cursor.fetchall():
            ddl_statements.append(f"-- Index: {self.schema_name}.{row['index_name']}")
            ddl_statements.append(row['definition'] + ";")
            ddl_statements.append("")
        
        return ddl_statements
    
    def get_triggers(self) -> List[str]:
        """
        Generate DDL for triggers.
        
        Returns:
            List of CREATE TRIGGER DDL statements
        """
        query = """
            SELECT 
                c.relname as table_name,
                t.tgname as trigger_name,
                pg_get_triggerdef(t.oid) as definition
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = %s
              AND NOT t.tgisinternal
            ORDER BY c.relname, t.tgname
        """
        self.cursor.execute(query, (self.schema_name,))
        
        ddl_statements = []
        for row in self.cursor.fetchall():
            ddl_statements.append(f"-- Trigger: {self.schema_name}.{row['trigger_name']}")
            ddl_statements.append(row['definition'] + ";")
            ddl_statements.append("")
        
        return ddl_statements
    
    def get_views(self) -> List[str]:
        """
        Generate DDL for views.
        
        Returns:
            List of CREATE VIEW DDL statements
        """
        query = """
            SELECT 
                c.relname as view_name,
                pg_get_viewdef(c.oid, true) as definition
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = %s
              AND c.relkind = 'v'
            ORDER BY c.relname
        """
        self.cursor.execute(query, (self.schema_name,))
        
        ddl_statements = []
        for row in self.cursor.fetchall():
            ddl_statements.append(f"-- View: {self.schema_name}.{row['view_name']}")
            ddl_statements.append(f"CREATE OR REPLACE VIEW {self.schema_name}.{row['view_name']} AS")
            ddl_statements.append(row['definition'].rstrip(';') + ";")
            
            # View comment
            self.cursor.execute("""
                SELECT obj_description(c.oid) as comment
                FROM pg_class c
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE c.relname = %s AND n.nspname = %s
            """, (row['view_name'], self.schema_name))
            
            comment_row = self.cursor.fetchone()
            if comment_row and comment_row['comment']:
                escaped_comment = comment_row['comment'].replace("'", "''")
                ddl_statements.append(
                    f"COMMENT ON VIEW {self.schema_name}.{row['view_name']} IS "
                    f"'{escaped_comment}';")
            
            ddl_statements.append("")
        
        return ddl_statements
    
    def get_all_tables(self) -> List[str]:
        """
        Get all table names in the schema.
        
        Returns:
            List of table names
        """
        query = """
            SELECT c.relname as table_name
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = %s
              AND c.relkind = 'r'
            ORDER BY c.relname
        """
        self.cursor.execute(query, (self.schema_name,))
        return [row['table_name'] for row in self.cursor.fetchall()]
    
    def generate_schema_ddl(self) -> str:
        """
        Generate complete DDL for the schema.
        
        Returns:
            Complete DDL as a string
        """
        ddl_statements = []
        
        # Header
        ddl_statements.append(f"-- DDL for schema: {self.schema_name}")
        ddl_statements.append(f"-- Generated by PostgreSQL DDL Generator")
        ddl_statements.append("")
        ddl_statements.append(f"-- Create schema if not exists")
        ddl_statements.append(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name};")
        ddl_statements.append("")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- TRIGGER FUNCTIONS")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        
        # 1. Trigger Functions
        ddl_statements.extend(self.get_trigger_functions())
        
        # Get serial sequences to exclude them
        serial_sequences = self.get_serial_sequences()
        column_sequence_info = self.get_column_sequence_info()
        
        # 2. Standalone Sequences
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- SEQUENCES")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        ddl_statements.extend(self.get_standalone_sequences(serial_sequences))
        
        # 3. Tables (without foreign keys)
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- TABLES")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        
        all_tables = self.get_all_tables()
        dependencies = self.get_table_dependencies()
        sorted_tables = self.topological_sort(dependencies, all_tables)
        
        for table_name in sorted_tables:
            ddl_statements.extend(
                self.generate_table_ddl(table_name, column_sequence_info, 
                                       include_foreign_keys=False)
            )
        
        # 4. Foreign Key Constraints
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- FOREIGN KEY CONSTRAINTS")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        
        foreign_keys = self.get_foreign_key_constraints()
        ddl_statements.extend(self.generate_foreign_key_ddl(foreign_keys))
        
        # 5. Indexes
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- INDEXES")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        ddl_statements.extend(self.get_indexes())
        
        # 6. Triggers
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- TRIGGERS")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        ddl_statements.extend(self.get_triggers())
        
        # 7. Views
        ddl_statements.append("-- ======================================")
        ddl_statements.append("-- VIEWS")
        ddl_statements.append("-- ======================================")
        ddl_statements.append("")
        ddl_statements.extend(self.get_views())
        
        return "\n".join(ddl_statements)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate DDL statements for a PostgreSQL schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate DDL for 'public' schema
  %(prog)s -h localhost -d mydb -u postgres -s public

  # Generate DDL and save to file
  %(prog)s -h localhost -d mydb -u postgres -s public -o schema.sql

  # Using environment variables for password
  PGPASSWORD=secret %(prog)s -h localhost -d mydb -u postgres -s public
        """
    )
    
    parser.add_argument('-h', '--host', required=True,
                       help='Database host')
    parser.add_argument('-p', '--port', default='5432',
                       help='Database port (default: 5432)')
    parser.add_argument('-d', '--database', required=True,
                       help='Database name')
    parser.add_argument('-u', '--user', required=True,
                       help='Database user')
    parser.add_argument('-w', '--password', 
                       help='Database password (can also use PGPASSWORD env var)')
    parser.add_argument('-s', '--schema', required=True,
                       help='Schema name to generate DDL for')
    parser.add_argument('-o', '--output',
                       help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Get password from args or environment
    import os
    password = args.password or os.environ.get('PGPASSWORD')
    
    if not password:
        import getpass
        password = getpass.getpass('Database password: ')
    
    # Connection parameters
    conn_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': password
    }
    
    # Generate DDL
    generator = PostgreSQLDDLGenerator(conn_params, args.schema)
    
    try:
        generator.connect()
        ddl = generator.generate_schema_ddl()
        
        # Output DDL
        if args.output:
            with open(args.output, 'w') as f:
                f.write(ddl)
            print(f"DDL generated successfully: {args.output}", file=sys.stderr)
        else:
            print(ddl)
    
    except Exception as e:
        print(f"Error generating DDL: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        generator.close()


if __name__ == '__main__':
    main()
