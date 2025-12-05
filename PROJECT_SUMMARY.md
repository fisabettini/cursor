# PostgreSQL Schema DDL Generator - Project Summary

## Overview
This project provides a comprehensive Python script to generate DDL (Data Definition Language) statements for PostgreSQL schemas, with special handling for dependencies, sequences, and all database objects.

## Files Created

### 1. generate_schema_ddl.py (Main Script)
The core Python script that connects to a PostgreSQL database and generates complete DDL statements.

**Key Features:**
- Connects to PostgreSQL database using psycopg2
- Generates DDL for all schema objects in proper order
- Handles complex dependencies and circular references
- Converts identity sequences to serial/bigserial types
- Preserves all metadata (comments, constraints, etc.)

### 2. requirements.txt
Dependencies required to run the script:
- psycopg2-binary>=2.9.0

### 3. README.md
Comprehensive documentation including:
- Installation instructions
- Usage examples
- Command-line arguments
- Feature descriptions
- Technical details on serial/bigserial handling
- Dependency ordering algorithm

### 4. examples.sh
Bash script with commented examples showing various usage scenarios.

### 5. example_output.sql
Sample DDL output demonstrating what the script generates.

### 6. test_script.py
Simple test to verify the script structure and components.

## How It Works

### 1. Connection & Discovery
- Connects to PostgreSQL database
- Queries system catalogs (pg_class, pg_namespace, pg_constraint, etc.)
- Discovers all objects in the specified schema

### 2. Serial/BigSerial Detection
The script intelligently handles PostgreSQL's serial types:

```python
# Finds sequences owned by table columns (auto dependency)
SELECT s.relname as sequence_name
FROM pg_class s
JOIN pg_depend d ON d.objid = s.oid
WHERE s.relkind = 'S' AND d.deptype = 'a'
```

For each column:
- Checks if column uses a sequence via nextval()
- Checks if column type is integer/bigint/smallint
- Converts to serial/bigserial/smallserial if both conditions met
- Excludes these sequences from standalone sequence creation

### 3. Dependency Ordering (Topological Sort)
Ensures tables are created in the correct order:

```
1. Analyze foreign key relationships
2. Build dependency graph
3. Sort tables topologically:
   - Tables with no dependencies first
   - Dependent tables after their references
4. Handle circular dependencies by deferring FK constraints
```

### 4. DDL Generation Order
The script generates DDL in this specific order:

1. **Schema Creation** - CREATE SCHEMA IF NOT EXISTS
2. **Trigger Functions** - Functions that return trigger type
3. **Regular Functions** - Non-trigger functions
4. **Procedures** - Stored procedures (PostgreSQL 11+)
5. **Standalone Sequences** - Sequences not owned by columns
6. **Tables** - In dependency order, without foreign keys
   - Column definitions (with serial types)
   - Primary keys
   - Unique constraints
   - Check constraints
   - Comments
7. **Foreign Key Constraints** - Added after all tables exist
8. **Indexes** - Regular indexes (excluding PK/unique indexes)
9. **Triggers** - All triggers on tables
10. **Views** - All views in the schema

### 5. Object-Specific Handling

#### Functions & Procedures
- **Trigger Functions**: Functions returning trigger type
- **Regular Functions**: All other functions (SQL, PL/pgSQL, etc.)
- **Procedures**: Stored procedures (PostgreSQL 11+)
- Preserves function language and attributes (IMMUTABLE, STABLE, VOLATILE)
- Includes function/procedure comments
- Proper signature handling for COMMENT statements

#### Tables
- Columns with proper data types
- Automatic serial/bigserial conversion
- NOT NULL constraints
- DEFAULT values
- Primary keys (inline)
- Unique constraints (inline)
- Check constraints (inline)
- Column and table comments

#### Sequences
- Only standalone sequences (not serial-related)
- Full configuration: INCREMENT, MINVALUE, MAXVALUE, START, CACHE, CYCLE

#### Foreign Keys
- Always added AFTER all tables are created
- Ensures referenced primary keys exist first
- Handles ON DELETE/ON UPDATE actions

#### Indexes
- Excludes primary key and unique constraint indexes
- Includes all regular indexes
- Preserves index type (btree, hash, gin, gist, etc.)
- Preserves index expressions and conditions

#### Triggers
- Requires trigger functions to be created first
- Preserves timing (BEFORE/AFTER)
- Preserves events (INSERT/UPDATE/DELETE)
- Preserves WHEN conditions

#### Views
- Uses CREATE OR REPLACE VIEW
- Preserves view definition
- Includes view comments

## Usage Examples

### Basic Usage
```bash
python generate_schema_ddl.py \
  --host localhost \
  --database mydb \
  --user postgres \
  --schema public \
  --output schema.sql
```

### With Environment Variable
```bash
export PGPASSWORD=secret
python generate_schema_ddl.py -h localhost -d mydb -u postgres -s myschema
```

### Multiple Schemas
```bash
for schema in public app_data reporting; do
  python generate_schema_ddl.py \
    -h localhost -d mydb -u postgres \
    -s $schema -o ${schema}_schema.sql
done
```

## Technical Implementation Details

### Key Classes & Methods

**PostgreSQLDDLGenerator class:**
- `connect()` - Establishes database connection
- `get_serial_sequences()` - Finds sequences owned by columns
- `get_column_sequence_info()` - Maps columns to their sequences
- `get_column_default_type()` - Converts integer+sequence to serial
- `get_trigger_functions()` - Extracts trigger functions
- `get_functions()` - Extracts regular (non-trigger) functions
- `get_procedures()` - Extracts stored procedures (PostgreSQL 11+)
- `get_table_dependencies()` - Builds foreign key dependency graph
- `topological_sort()` - Sorts tables by dependencies
- `generate_table_ddl()` - Creates table DDL
- `get_foreign_key_constraints()` - Extracts all foreign keys
- `generate_foreign_key_ddl()` - Creates ALTER TABLE statements
- `get_indexes()`, `get_triggers()`, `get_views()` - Extract other objects
- `generate_schema_ddl()` - Main orchestration method

### System Catalog Queries

The script queries these PostgreSQL system catalogs:
- `pg_class` - Tables, indexes, sequences, views
- `pg_namespace` - Schemas
- `pg_attribute` - Table columns
- `pg_constraint` - Constraints (PK, FK, unique, check)
- `pg_index` - Index definitions
- `pg_trigger` - Trigger definitions
- `pg_proc` - Functions (including trigger functions)
- `pg_sequence` - Sequence properties
- `pg_depend` - Object dependencies
- `pg_attrdef` - Column defaults

## Requirements

**Software:**
- Python 3.6+
- PostgreSQL 9.0+
- psycopg2 library

**Database Permissions:**
The database user needs SELECT access to system catalogs (typically granted to all users).

## Error Handling

The script includes error handling for:
- Connection failures
- Invalid schema names
- Missing permissions
- Circular dependencies (handled by deferring FKs)
- Missing sequences or functions

## Limitations & Considerations

1. **Partitioned Tables:** Basic support; partition definitions not included
2. **Inheritance:** Parent-child table relationships handled as regular FKs
3. **Materialized Views:** Not included (can be added if needed)
4. **Row-Level Security:** Policies not included
5. **Extensions:** Extension-dependent types preserved but extension creation not included
6. **Large Objects:** LOBs in columns preserved but BLOB data not dumped

## Advantages Over pg_dump

1. **Serial/BigSerial Conversion:** Automatically converts sequences to serial types
2. **Customizable:** Easy to modify for specific needs
3. **Schema-Only:** Focuses on single schema without full database
4. **Readable Output:** Organized sections with clear comments
5. **Dependency Visualization:** Shows clear ordering of objects

## Future Enhancements

Potential additions:
- Support for materialized views
- Row-level security policies
- Publication/subscription definitions
- Extension management
- Custom type definitions
- Operator classes
- Full-text search configurations
- Domain types

## Installation & Quick Start

```bash
# Clone or download the files
cd /path/to/project

# Install dependencies
pip install -r requirements.txt

# Run the script
python generate_schema_ddl.py \
  -h localhost \
  -d mydb \
  -u postgres \
  -s myschema \
  -o output.sql

# Review the output
cat output.sql
```

## Testing

Run the test script to verify structure:
```bash
python test_script.py
```

This checks that all required methods and features are present.

## License

This script is provided as-is for PostgreSQL database management and migration tasks.

## Support

For issues or questions, review the README.md or examine the example_output.sql file.
