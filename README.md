# PostgreSQL Schema DDL Generator

A Python script that generates complete DDL (Data Definition Language) statements for a PostgreSQL schema, including all related objects.

> **Note**: Use `-H` (capital H) for the host argument. The lowercase `-h` is reserved for `--help`.

## Features

- **Complete Schema Export**: Generates DDL for all objects in a specified schema:
  - Trigger functions
  - Regular functions (non-trigger)
  - Procedures (PostgreSQL 11+)
  - Sequences (standalone, non-serial)
  - Tables with all columns
  - Primary keys, unique constraints, check constraints
  - Foreign key constraints (added after tables)
  - Indexes
  - Triggers
  - Views

- **Smart Dependency Management**:
  - Tables are created in topological order based on foreign key dependencies
  - Foreign keys are added after all tables exist, ensuring references are valid
  - Handles circular dependencies gracefully

- **Serial/BigSerial Handling**:
  - Automatically detects sequences owned by table columns
  - Converts integer columns with sequence defaults to `serial`/`bigserial`/`smallserial`
  - Avoids creating sequences separately when they're part of serial columns
  - Only generates standalone sequences that are explicitly created

- **Preserves Object Metadata**:
  - Column and table comments
  - Sequence parameters (increment, min/max values, cache, cycle)
  - Index definitions
  - Trigger definitions
  - View definitions

## Installation

1. Install Python 3.6 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install psycopg2-binary
```

## Usage

### Basic Usage

```bash
python generate_schema_ddl.py -H localhost -d mydb -u postgres -s public
```

### Save to File

```bash
python generate_schema_ddl.py -H localhost -d mydb -u postgres -s myschema -o schema_ddl.sql
```

### Using Environment Variable for Password

```bash
export PGPASSWORD=your_password
python generate_schema_ddl.py -H localhost -d mydb -u postgres -s public
```

### Command Line Arguments

- `-h, --host`: Database host (required)
- `-p, --port`: Database port (default: 5432)
- `-d, --database`: Database name (required)
- `-u, --user`: Database user (required)
- `-w, --password`: Database password (optional, will prompt if not provided)
- `-s, --schema`: Schema name to generate DDL for (required)
- `-o, --output`: Output file path (optional, prints to stdout if not provided)

## Examples

### Example 1: Export Public Schema

```bash
python generate_schema_ddl.py \
  --host localhost \
  --database myapp \
  --user postgres \
  --schema public \
  --output public_schema.sql
```

### Example 2: Export Custom Schema with Password

```bash
PGPASSWORD=secret python generate_schema_ddl.py \
  -H db.example.com \
  -p 5432 \
  -d production \
  -u readonly_user \
  -s app_schema \
  -o app_schema_backup.sql
```

### Example 3: Remote Database Export

```bash
python generate_schema_ddl.py \
  --host remote-db.example.com \
  --port 5433 \
  --database analytics \
  --user analyst \
  --schema reporting \
  --output reporting_schema.sql
```

## Output Structure

The generated DDL follows this order:

1. **Schema Creation**: `CREATE SCHEMA IF NOT EXISTS`
2. **Trigger Functions**: All functions that return `trigger` type
3. **Functions**: Regular functions (non-trigger)
4. **Procedures**: Stored procedures (PostgreSQL 11+)
5. **Sequences**: Standalone sequences (excluding serial/bigserial sequences)
6. **Tables**: In dependency order
   - Column definitions with proper data types (serial/bigserial when applicable)
   - Primary keys, unique constraints, check constraints
   - Column and table comments
7. **Foreign Key Constraints**: Added after all tables are created
8. **Indexes**: Regular indexes (excluding PK and unique constraint indexes)
9. **Triggers**: All triggers on tables
10. **Views**: All views in the schema

## How Serial/BigSerial Detection Works

The script intelligently handles PostgreSQL's serial types:

1. Queries `pg_depend` to find sequences owned by table columns (auto dependency)
2. For each column, checks if:
   - The column type is `integer`, `bigint`, or `smallint`
   - The column has a default value using `nextval()` on the owned sequence
3. If both conditions are met, replaces the type with:
   - `smallint` + sequence → `smallserial`
   - `integer` + sequence → `serial`
   - `bigint` + sequence → `bigserial`
4. Excludes owned sequences from the standalone sequences section

## Dependency Ordering

The script uses topological sorting to ensure tables are created in the correct order:

1. Analyzes foreign key relationships between tables
2. Creates tables with no dependencies first
3. Creates dependent tables after their referenced tables
4. Handles circular dependencies by deferring foreign key creation

## Requirements

- Python 3.6+
- PostgreSQL 9.0+
- psycopg2 library
- Database user must have read access to:
  - `pg_class`
  - `pg_namespace`
  - `pg_attribute`
  - `pg_constraint`
  - `pg_index`
  - `pg_trigger`
  - `pg_proc`
  - `pg_sequence`
  - `pg_depend`
  - `pg_attrdef`

## License

This script is provided as-is for use in PostgreSQL database management and migration tasks.

## Contributing

Feel free to submit issues or pull requests for improvements.
