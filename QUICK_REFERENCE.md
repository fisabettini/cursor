# PostgreSQL DDL Generator - Quick Reference

## Installation
```bash
pip install psycopg2-binary
```

## Basic Command
```bash
python generate_schema_ddl.py -h HOST -d DATABASE -u USER -s SCHEMA [-o OUTPUT]
```

## Common Usage Patterns

### 1. Interactive (prompts for password)
```bash
python generate_schema_ddl.py -h localhost -d mydb -u postgres -s public
```

### 2. With Environment Variable
```bash
export PGPASSWORD=mypassword
python generate_schema_ddl.py -h localhost -d mydb -u postgres -s public -o output.sql
```

### 3. Remote Database
```bash
python generate_schema_ddl.py \
  -h db.example.com \
  -p 5433 \
  -d production \
  -u readonly_user \
  -s app_schema \
  -o backup.sql
```

### 4. Multiple Schemas
```bash
for schema in public app reporting; do
  python generate_schema_ddl.py \
    -h localhost -d mydb -u postgres \
    -s $schema -o ${schema}.sql
done
```

## Command-Line Arguments

| Argument | Short | Required | Default | Description |
|----------|-------|----------|---------|-------------|
| --host | -h | Yes | - | Database hostname or IP |
| --port | -p | No | 5432 | Database port |
| --database | -d | Yes | - | Database name |
| --user | -u | Yes | - | Database user |
| --password | -w | No | - | Database password (or use PGPASSWORD env var) |
| --schema | -s | Yes | - | Schema name to export |
| --output | -o | No | stdout | Output file path |

## Output Structure

The script generates DDL in this order:

```
1. Schema creation
2. Trigger functions
3. Standalone sequences
4. Tables (in dependency order)
   - Columns with serial/bigserial
   - Primary keys
   - Unique constraints
   - Check constraints
5. Foreign key constraints
6. Indexes
7. Triggers
8. Views
```

## Key Features

### ✓ Serial/BigSerial Conversion
Automatically converts:
- `integer` + sequence → `serial`
- `bigint` + sequence → `bigserial`
- `smallint` + sequence → `smallserial`

### ✓ Dependency Ordering
- Tables created before foreign keys reference them
- Topological sort handles complex dependencies
- Circular dependencies resolved by deferring FKs

### ✓ All Object Types
- Tables, columns, constraints
- Sequences (standalone only)
- Indexes (excluding PK/unique)
- Triggers and trigger functions
- Views with definitions
- Comments on tables and columns

## Special Handling

### Identity Columns
```sql
-- Source: id INTEGER DEFAULT nextval('seq')
-- Output: id SERIAL
```

### Foreign Keys
```sql
-- First: CREATE TABLE parent (id SERIAL PRIMARY KEY)
-- Then: CREATE TABLE child (parent_id INTEGER)
-- Finally: ALTER TABLE child ADD FOREIGN KEY (parent_id) REFERENCES parent(id)
```

### Sequences
```sql
-- Owned by columns (serial): NOT generated separately
-- Standalone sequences: Full CREATE SEQUENCE statement
```

## Troubleshooting

### Connection Issues
```bash
# Test connection with psql first
psql -h HOST -p PORT -d DATABASE -U USER

# Check firewall/network
ping HOST

# Verify credentials
```

### Permission Errors
The user needs read access to system catalogs (usually granted by default).

### Module Not Found
```bash
# Install psycopg2
pip install psycopg2-binary

# Or use system package
apt-get install python3-psycopg2  # Debian/Ubuntu
yum install python3-psycopg2      # RedHat/CentOS
```

## Examples with Real Scenarios

### Backup Before Migration
```bash
python generate_schema_ddl.py \
  -h prod-db.company.com \
  -d maindb \
  -u backup_user \
  -s production_schema \
  -o backup_$(date +%Y%m%d).sql
```

### Compare Environments
```bash
# Export from DEV
python generate_schema_ddl.py -h dev-db -d app -u admin -s public -o dev.sql

# Export from PROD
python generate_schema_ddl.py -h prod-db -d app -u admin -s public -o prod.sql

# Compare
diff dev.sql prod.sql
```

### Recreate Schema in Test
```bash
# Export from production
python generate_schema_ddl.py -h prod-db -d app -u user -s public -o schema.sql

# Import to test
psql -h test-db -d testapp -U user -f schema.sql
```

## Performance Tips

- Use read-only database user for safety
- Run during low-traffic periods for large schemas
- Consider network bandwidth for remote databases
- Large schemas may take several seconds to process

## File Outputs

### Stdout (default)
```bash
python generate_schema_ddl.py -h localhost -d mydb -u postgres -s public > output.sql
```

### Direct to File (recommended)
```bash
python generate_schema_ddl.py -h localhost -d mydb -u postgres -s public -o output.sql
```

### With Timestamp
```bash
OUTPUT="schema_$(date +%Y%m%d_%H%M%S).sql"
python generate_schema_ddl.py -h localhost -d mydb -u postgres -s public -o "$OUTPUT"
```

## Return Codes

- `0` - Success
- `1` - Error (connection, permission, etc.)

## See Also

- `README.md` - Detailed documentation
- `PROJECT_SUMMARY.md` - Technical details
- `example_output.sql` - Sample output
- `examples.sh` - More usage examples

## Quick Test

```bash
# Verify script syntax
python3 -m py_compile generate_schema_ddl.py

# Run structure test
python3 test_script.py

# Show help
python3 generate_schema_ddl.py --help
```
