# PostgreSQL DDL Generator

A comprehensive Python script to generate DDL (Data Definition Language) statements from an existing PostgreSQL 18 database.

## Features

- ✅ **User-Defined Types**: Exports ENUM, COMPOSITE, and DOMAIN types
- ✅ **Tables**: Both regular and partitioned tables with all columns
- ✅ **Serial Types**: Automatically converts integer columns with sequences to `serial`, `bigserial`, or `smallserial`
- ✅ **Primary Keys**: Inline primary key constraints
- ✅ **Foreign Keys**: With ON UPDATE/ON DELETE actions
- ✅ **Dependency Management**: Automatically sorts tables by foreign key dependencies
- ✅ **Partitioned Tables**: Handles both partitioned tables and their partitions
- ✅ **Triggers**: Exports trigger definitions
- ✅ **Functions**: Exports function definitions used by triggers
- ✅ **Comments**: Preserves table, column, type, and function comments

## Requirements

- Python 3.6+
- PostgreSQL 18 (compatible with earlier versions too)
- psycopg2

## Installation

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
# Generate DDL for public schema
python postgres_ddl_generator.py -H localhost -d mydb -U postgres -s public

# Save to file
python postgres_ddl_generator.py -H localhost -d mydb -U postgres -s public -o schema.sql
```

### Command Line Arguments

```
-H, --host        PostgreSQL host (default: localhost)
-p, --port        PostgreSQL port (default: 5432)
-d, --database    Database name (required)
-U, --user        Database user (required)
-W, --password    Database password (optional, will prompt if not provided)
-s, --schema      Schema name (default: public)
-o, --output      Output file (default: stdout)
```

### Using Environment Variables

You can set the password via environment variable:

```bash
export PGPASSWORD=mypassword
python postgres_ddl_generator.py -H localhost -d mydb -U postgres
```

### Examples

#### Example 1: Export to stdout

```bash
python postgres_ddl_generator.py -H localhost -d production_db -U admin -s public
```

#### Example 2: Export to file

```bash
python postgres_ddl_generator.py \
  -H db.example.com \
  -p 5432 \
  -d ecommerce \
  -U dbuser \
  -s public \
  -o ecommerce_schema.sql
```

#### Example 3: Export custom schema

```bash
python postgres_ddl_generator.py -H localhost -d mydb -U postgres -s inventory -o inventory.sql
```

## Features in Detail

### Serial Type Conversion

The script automatically detects columns that use sequences and converts them to the appropriate serial type:

**Before** (what's in the database):
```sql
id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass)
```

**After** (generated DDL):
```sql
id serial NOT NULL
```

This works for:
- `integer` → `serial`
- `bigint` → `bigserial`
- `smallint` → `smallserial`

### Dependency Management

Tables are automatically sorted by foreign key dependencies, ensuring that:
1. Referenced tables are created before tables that reference them
2. Circular dependencies are handled gracefully
3. Foreign keys are added after all tables are created

### Partitioned Tables

The script handles:
- **Partitioned tables** with PARTITION BY clause
- **Partitions** with proper PARTITION OF syntax
- **Partition bounds** (RANGE, LIST, HASH)

Example output:
```sql
-- Parent table
CREATE TABLE "public"."sales" (
    "id" bigserial NOT NULL,
    "sale_date" date NOT NULL,
    "amount" numeric(10,2),
    CONSTRAINT "sales_pkey" PRIMARY KEY ("id")
) PARTITION BY RANGE (sale_date);

-- Partition
CREATE TABLE "public"."sales_2024_q1" PARTITION OF "public"."sales"
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
```

### User-Defined Types

Exports all custom types in the correct order:

**ENUM Types:**
```sql
CREATE TYPE "public"."order_status" AS ENUM ('pending', 'processing', 'shipped', 'delivered');
```

**COMPOSITE Types:**
```sql
CREATE TYPE "public"."address" AS (
    "street" text,
    "city" text,
    "zipcode" varchar(10)
);
```

**DOMAIN Types:**
```sql
CREATE DOMAIN "public"."email" AS text 
    CHECK (VALUE ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

### Functions and Triggers

Exports complete function definitions and trigger definitions:

```sql
-- Function
CREATE FUNCTION update_modified_timestamp()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$;

-- Trigger
CREATE TRIGGER users_update_timestamp 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_modified_timestamp();
```

## Output Structure

The generated DDL is organized in the following order:

1. **User-Defined Types** (ENUMs, Composite Types, Domains)
2. **Functions** (used by triggers)
3. **Tables** (sorted by dependencies)
   - Regular tables
   - Partitioned tables
   - Partitions
4. **Foreign Keys** (all constraints)
5. **Triggers** (all triggers)

## Limitations

- Does not export:
  - Indexes (other than PK/FK)
  - Views
  - Materialized Views
  - Procedures (only functions)
  - Sequences that are not tied to serial columns
  - Grants and permissions
  - Table inheritance (non-partition)

## Contributing

Feel free to extend this script to include additional PostgreSQL objects or features.

## License

MIT License - feel free to use and modify as needed.

## Example Output

Here's a sample of what the generated DDL looks like:

```sql
-- PostgreSQL DDL Generator
-- Schema: public
-- Generated for PostgreSQL 18

-- ========================================
-- User-Defined Types
-- ========================================

CREATE TYPE "public"."user_role" AS ENUM ('admin', 'user', 'guest');

-- ========================================
-- Functions
-- ========================================

CREATE OR REPLACE FUNCTION public.update_timestamp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$;

-- ========================================
-- Tables
-- ========================================

CREATE TABLE "public"."users" (
    "id" bigserial NOT NULL,
    "username" varchar(50) NOT NULL,
    "email" varchar(100) NOT NULL,
    "role" user_role DEFAULT 'user',
    "created_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "public"."orders" (
    "id" bigserial NOT NULL,
    "user_id" bigint NOT NULL,
    "total" numeric(10,2),
    "created_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "orders_pkey" PRIMARY KEY ("id")
);

-- ========================================
-- Foreign Keys
-- ========================================

ALTER TABLE "public"."orders"
    ADD CONSTRAINT "orders_user_id_fkey" FOREIGN KEY ("user_id")
    REFERENCES "public"."users" ("id")
    ON DELETE CASCADE;

-- ========================================
-- Triggers
-- ========================================

CREATE TRIGGER users_update_timestamp BEFORE UPDATE ON public.users 
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
```

## Troubleshooting

### Connection Issues

If you get connection errors:
```bash
# Test connection with psql first
psql -h localhost -U postgres -d mydb -c "SELECT version();"
```

### Permission Issues

Ensure your database user has SELECT permissions on system catalogs:
```sql
GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO your_user;
```

### Empty Output

If the output is empty, check:
1. The schema name is correct
2. The schema contains objects
3. Your user has permissions to view the objects

```sql
-- List available schemas
SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema';
```
