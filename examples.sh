#!/bin/bash
# Example usage script for PostgreSQL Schema DDL Generator

# Example 1: Generate DDL for public schema and display to stdout
echo "Example 1: Generate DDL for public schema"
echo "----------------------------------------"
# python generate_schema_ddl.py -H localhost -d mydb -u postgres -s public

# Example 2: Generate DDL and save to file
echo "Example 2: Save DDL to file"
echo "----------------------------------------"
# python generate_schema_ddl.py -H localhost -d mydb -u postgres -s public -o schema.sql

# Example 3: Using environment variable for password
echo "Example 3: Using PGPASSWORD environment variable"
echo "----------------------------------------"
# export PGPASSWORD=your_password
# python generate_schema_ddl.py -H localhost -d mydb -u postgres -s public

# Example 4: Connect to remote database
echo "Example 4: Remote database connection"
echo "----------------------------------------"
# python generate_schema_ddl.py -H remote.example.com -p 5432 -d production -u readonly -s app_schema -o backup.sql

# Example 5: Multiple schemas (run separately for each)
echo "Example 5: Export multiple schemas"
echo "----------------------------------------"
# for schema in public app_data reporting; do
#   python generate_schema_ddl.py -H localhost -d mydb -u postgres -s $schema -o ${schema}_schema.sql
# done

echo ""
echo "Uncomment the examples above to use them with your database credentials"
