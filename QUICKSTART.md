# Quick Start Guide

Get started with the PostgreSQL DDL Generator in 5 minutes!

## Prerequisites

- Python 3.6 or higher installed
- Access to a PostgreSQL database
- PostgreSQL client tools (optional, for testing)

## Step 1: Install Dependencies

```bash
pip install psycopg2-binary
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

## Step 2: Basic Usage

Generate DDL for your database:

```bash
python postgres_ddl_generator.py \
    -H localhost \
    -d your_database \
    -U your_username \
    -s public \
    -o schema.sql
```

You'll be prompted for a password, or set it in advance:

```bash
export PGPASSWORD=your_password
```

## Step 3: View the Output

```bash
cat schema.sql
```

Or open in your favorite editor!

## Common Use Cases

### Use Case 1: Quick Schema Backup

```bash
# Backup to timestamped file
DATE=$(date +%Y%m%d_%H%M%S)
python postgres_ddl_generator.py \
    -H localhost \
    -d production_db \
    -U postgres \
    -o "backup_${DATE}.sql"
```

### Use Case 2: Compare Two Schemas

```bash
# Generate DDL for both databases
python postgres_ddl_generator.py -H db1 -d mydb -U postgres -o db1_schema.sql
python postgres_ddl_generator.py -H db2 -d mydb -U postgres -o db2_schema.sql

# Compare
diff db1_schema.sql db2_schema.sql
```

### Use Case 3: Multiple Schemas

```bash
# Export all schemas
for schema in public inventory sales; do
    python postgres_ddl_generator.py \
        -H localhost \
        -d mydb \
        -U postgres \
        -s $schema \
        -o "${schema}_schema.sql"
done
```

## Testing with Example Data

Want to try it out first? Run the example schema creator:

```bash
# Edit connection params in example_create_schema.py
python example_create_schema.py

# Then generate DDL from the example schema
python postgres_ddl_generator.py \
    -H localhost \
    -d postgres \
    -U postgres \
    -s test_schema \
    -o example_output.sql
```

## What Gets Generated?

The script generates DDL for:

✅ User-defined types (ENUMs, COMPOSITEs, DOMAINs)  
✅ Functions (used by triggers)  
✅ Tables (regular and partitioned)  
✅ Partitions  
✅ Primary keys  
✅ Foreign keys  
✅ Triggers  
✅ Comments  

**Plus:** Automatic conversion of sequences to serial types!

## Example Output

```sql
-- PostgreSQL DDL Generator
-- Schema: public
-- Generated for PostgreSQL 18

-- User-Defined Types
CREATE TYPE "public"."user_status" AS ENUM ('active', 'inactive', 'suspended');

-- Functions
CREATE FUNCTION "public"."update_timestamp"() ...;

-- Tables
CREATE TABLE "public"."users" (
    "id" bigserial NOT NULL,
    "username" varchar(50) NOT NULL,
    "email" varchar(100),
    "status" user_status DEFAULT 'active',
    "created_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- Foreign Keys
ALTER TABLE "public"."orders"
    ADD CONSTRAINT "orders_user_fk" FOREIGN KEY ("user_id")
    REFERENCES "public"."users" ("id")
    ON DELETE CASCADE;

-- Triggers
CREATE TRIGGER "update_timestamp" ...;
```

## Command Line Options

```
Required:
  -d, --database    Database name

Connection:
  -H, --host        PostgreSQL host (default: localhost)
  -p, --port        PostgreSQL port (default: 5432)
  -U, --user        Database user
  -W, --password    Password (optional, will prompt)

Options:
  -s, --schema      Schema name (default: public)
  -o, --output      Output file (default: stdout)
```

## Tips

### Tip 1: Security
Never put passwords in scripts! Use environment variables:

```bash
export PGPASSWORD=your_password
python postgres_ddl_generator.py -H localhost -d mydb -U postgres
```

Or use PostgreSQL's `.pgpass` file:

```bash
echo "localhost:5432:*:postgres:your_password" > ~/.pgpass
chmod 600 ~/.pgpass
```

### Tip 2: Piping Output

View output with less:
```bash
python postgres_ddl_generator.py -H localhost -d mydb -U postgres | less
```

Count tables:
```bash
python postgres_ddl_generator.py -H localhost -d mydb -U postgres | grep -c "CREATE TABLE"
```

### Tip 3: Remote Databases

For remote databases, just change the host:
```bash
python postgres_ddl_generator.py \
    -H db.example.com \
    -p 5432 \
    -d production \
    -U readonly_user \
    -o prod_schema.sql
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'psycopg2'"

**Solution:**
```bash
pip install psycopg2-binary
```

### Issue: "connection refused"

**Solution:** Check that PostgreSQL is running and accessible:
```bash
psql -h localhost -U postgres -d postgres -c "SELECT version();"
```

### Issue: "permission denied"

**Solution:** Grant necessary permissions:
```sql
GRANT USAGE ON SCHEMA public TO your_user;
GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO your_user;
```

### Issue: "password authentication failed"

**Solution:** Verify your credentials:
```bash
psql -h localhost -U postgres -d postgres
```

## Next Steps

1. **Read the full documentation**: Check out `README.md`
2. **Explore features**: See `FEATURES.md` for details
3. **Try examples**: Look at `EXAMPLES.md` for advanced usage
4. **Customize**: Modify the script for your needs

## Need Help?

- 📖 Read `README.md` for comprehensive documentation
- 🚀 Check `FEATURES.md` for feature details
- 💡 See `EXAMPLES.md` for usage examples
- 🔧 Review `SETUP.md` for installation help

## Quick Reference

```bash
# Basic usage
python postgres_ddl_generator.py -H HOST -d DB -U USER -o OUTPUT

# With password
export PGPASSWORD=pass
python postgres_ddl_generator.py -H HOST -d DB -U USER -o OUTPUT

# Custom schema
python postgres_ddl_generator.py -H HOST -d DB -U USER -s SCHEMA -o OUTPUT

# To stdout
python postgres_ddl_generator.py -H HOST -d DB -U USER

# Get help
python postgres_ddl_generator.py --help
```

---

**You're ready to go!** 🚀

Start generating DDL and exploring your database schema.
