# PostgreSQL DDL Generator

A Python script that generates DDL (Data Definition Language) statements for PostgreSQL tables and their related database objects from a specific schema.

## Features

- **Tables**: Complete CREATE TABLE statements with all column definitions
- **Data Types**: Properly formatted data types including:
  - VARCHAR/CHAR with lengths
  - NUMERIC with precision/scale
  - Arrays
  - User-defined types
  - **SERIAL/BIGSERIAL/SMALLSERIAL** (automatically detects nextval() sequences)
- **Constraints**:
  - Primary Keys
  - Foreign Keys (with ON UPDATE/ON DELETE actions)
  - Unique Constraints
  - Check Constraints
- **Indexes**: All indexes except primary key indexes
- **Triggers**: All trigger definitions
- **Trigger Functions**: All functions used by triggers
- **Privileges**: REVOKE and GRANT statements for:
  - Tables (SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER)
  - Sequences (USAGE, SELECT, UPDATE)
  - Trigger Functions (EXECUTE)
  - WITH GRANT OPTION support
- **Comments**: Table, column, index, and trigger comments

## Requirements

```bash
pip install psycopg2-binary
```

Or using the included requirements file:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s public
```

### Save Output to File

```bash
python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s myschema > schema.sql
```

### Using Environment Variable for Password

```bash
export PGPASSWORD=your_password
python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s public
```

Or inline:

```bash
PGPASSWORD=your_password python pg_schema_ddl_generator.py -H localhost -d mydb -U postgres -s public
```

## Command Line Arguments

| Argument | Short | Required | Default | Description |
|----------|-------|----------|---------|-------------|
| --host | -H | No | localhost | Database host |
| --port | -p | No | 5432 | Database port |
| --database | -d | Yes | - | Database name |
| --user | -U | Yes | - | Database user |
| --password | -W | No | - | Database password (or use PGPASSWORD env var) |
| --schema | -s | Yes | - | Schema name to generate DDL for |

## Examples

### Generate DDL for public schema

```bash
python pg_schema_ddl_generator.py \
  -H localhost \
  -d mydatabase \
  -U postgres \
  -W mypassword \
  -s public
```

### Generate DDL for custom schema with remote database

```bash
python pg_schema_ddl_generator.py \
  -H db.example.com \
  -p 5433 \
  -d production_db \
  -U readonly_user \
  -s app_schema > app_schema_ddl.sql
```

### Using with Docker PostgreSQL

```bash
PGPASSWORD=docker python pg_schema_ddl_generator.py \
  -H localhost \
  -p 5432 \
  -d postgres \
  -U postgres \
  -s myschema
```

## Output Format

The script generates DDL in the following order:

1. **Trigger Functions** - Created first since triggers depend on them
2. **Tables** - All CREATE TABLE statements with column definitions
3. **Constraints** - Primary keys, foreign keys, unique, and check constraints
4. **Indexes** - All indexes (excluding primary key indexes)
5. **Triggers** - All trigger definitions
6. **REVOKE Privileges** - Remove existing privileges (for clean recreation)
   - Trigger functions
   - Sequences
   - Tables
7. **GRANT Privileges** - Restore privileges
   - Trigger functions (EXECUTE)
   - Sequences (USAGE, SELECT, UPDATE)
   - Tables (SELECT, INSERT, UPDATE, DELETE, etc.)

## Special Features

### Serial Type Detection

The script automatically detects columns that use sequences (via `nextval()`) and converts them to the appropriate SERIAL type:

- `INTEGER` with `nextval()` → `SERIAL`
- `BIGINT` with `nextval()` → `BIGSERIAL`
- `SMALLINT` with `nextval()` → `SMALLSERIAL`

**Example:**

Instead of:
```sql
CREATE TABLE users (
    id INTEGER NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    name VARCHAR(100)
);
```

The script generates:
```sql
CREATE TABLE users (
    id SERIAL,
    name VARCHAR(100)
);
```

### Foreign Key Actions

Foreign key constraints include ON UPDATE and ON DELETE actions when they differ from the default (NO ACTION):

```sql
ALTER TABLE orders ADD CONSTRAINT fk_customer 
  FOREIGN KEY (customer_id) REFERENCES customers (id) 
  ON DELETE CASCADE;
```

### Comments Preservation

All database comments are preserved in the generated DDL:

```sql
COMMENT ON TABLE users IS 'Application users';
COMMENT ON COLUMN users.email IS 'User email address (must be unique)';
```

### Privileges and Grants

The script captures and generates REVOKE/GRANT statements for all privileges:

**Tables:**
```sql
-- Revoke existing privileges
REVOKE SELECT, INSERT, UPDATE ON TABLE myschema.users FROM app_user;

-- Grant privileges back
GRANT SELECT, INSERT, UPDATE ON TABLE myschema.users TO app_user;
GRANT SELECT ON TABLE myschema.users TO readonly_user;
```

**Sequences (for SERIAL columns):**
```sql
REVOKE USAGE ON SEQUENCE myschema.users_id_seq FROM app_user;
GRANT USAGE, SELECT ON SEQUENCE myschema.users_id_seq TO app_user;
```

**Functions:**
```sql
REVOKE EXECUTE ON FUNCTION myschema.update_modified_timestamp() FROM app_user;
GRANT EXECUTE ON FUNCTION myschema.update_modified_timestamp() TO app_user;
```

**WITH GRANT OPTION:**
```sql
GRANT SELECT ON TABLE myschema.users TO admin_user WITH GRANT OPTION;
```

## Error Handling

- Connection errors are reported to stderr
- If no tables are found in the specified schema, a warning is displayed
- Invalid credentials or connection parameters will cause the script to exit with error code 1

## Notes

- The script only generates DDL for BASE TABLEs (not views, materialized views, etc.)
- System/internal triggers are excluded from the output
- The script connects in read-only mode and does not modify the database
- Output is written to stdout, informational messages to stderr

## License

This script is provided as-is for generating PostgreSQL DDL statements.
