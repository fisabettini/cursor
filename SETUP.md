# Setup Guide

## Quick Start

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   Or using a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Verify installation**:
   ```bash
   python postgres_ddl_generator.py --help
   ```

3. **Run the script**:
   ```bash
   python postgres_ddl_generator.py -H localhost -d mydb -U postgres -s public -o output.sql
   ```

## Testing with Example Schema

To test the DDL generator with a sample schema:

1. **Create example schema** (optional):
   ```bash
   # Edit connection parameters in example_create_schema.py first
   python example_create_schema.py
   ```

2. **Generate DDL from example schema**:
   ```bash
   python postgres_ddl_generator.py -H localhost -d postgres -U postgres -s test_schema -o example_output.sql
   ```

3. **View the generated DDL**:
   ```bash
   cat example_output.sql
   ```

## Requirements

- Python 3.6 or higher
- PostgreSQL 18 (compatible with earlier versions)
- psycopg2 library

## Troubleshooting

### psycopg2 installation issues

If you encounter issues installing psycopg2, try:

```bash
# On Ubuntu/Debian
sudo apt-get install python3-dev libpq-dev
pip install psycopg2-binary

# On macOS
brew install postgresql
pip install psycopg2-binary

# On Windows
pip install psycopg2-binary
```

### Connection issues

Make sure PostgreSQL is running and accessible:

```bash
# Test connection
psql -h localhost -U postgres -d postgres -c "SELECT version();"
```

### Permission issues

Ensure your database user has the necessary permissions:

```sql
-- Grant read access to system catalogs
GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO your_user;
```
