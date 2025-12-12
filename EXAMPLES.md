# Usage Examples

This document contains practical examples for using the PostgreSQL DDL Generator.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Connection Examples](#connection-examples)
3. [Output Examples](#output-examples)
4. [Advanced Scenarios](#advanced-scenarios)
5. [Integration Examples](#integration-examples)

---

## Basic Usage

### Example 1: Generate DDL to stdout

```bash
python postgres_ddl_generator.py \
    -H localhost \
    -d production_db \
    -U postgres \
    -s public
```

Output will be printed to the console.

### Example 2: Generate DDL to file

```bash
python postgres_ddl_generator.py \
    -H localhost \
    -d production_db \
    -U postgres \
    -s public \
    -o schema_backup.sql
```

### Example 3: Use environment variable for password

```bash
export PGPASSWORD="your_secure_password"
python postgres_ddl_generator.py \
    -H localhost \
    -d mydb \
    -U admin \
    -s public \
    -o output.sql
```

---

## Connection Examples

### Example 4: Remote PostgreSQL server

```bash
python postgres_ddl_generator.py \
    -H db.example.com \
    -p 5432 \
    -d ecommerce \
    -U dbadmin \
    -W "MySecurePass123" \
    -s public \
    -o ecommerce_schema.sql
```

### Example 5: Local PostgreSQL with custom port

```bash
python postgres_ddl_generator.py \
    -H localhost \
    -p 5433 \
    -d testdb \
    -U developer \
    -s test_schema \
    -o test_output.sql
```

### Example 6: Docker PostgreSQL container

```bash
# Assuming PostgreSQL is running in Docker on port 5432
python postgres_ddl_generator.py \
    -H localhost \
    -p 5432 \
    -d postgres \
    -U postgres \
    -W "postgres" \
    -s public \
    -o docker_schema.sql
```

---

## Output Examples

### Example 7: Multiple schemas

```bash
# Generate DDL for each schema separately
for schema in public inventory sales hr; do
    python postgres_ddl_generator.py \
        -H localhost \
        -d company_db \
        -U postgres \
        -s $schema \
        -o "${schema}_schema.sql"
done
```

### Example 8: Date-stamped output

```bash
# Create backup with timestamp
DATE=$(date +%Y%m%d_%H%M%S)
python postgres_ddl_generator.py \
    -H localhost \
    -d production_db \
    -U postgres \
    -s public \
    -o "schema_backup_${DATE}.sql"
```

### Example 9: Piping output

```bash
# Pipe output to less for viewing
python postgres_ddl_generator.py \
    -H localhost \
    -d mydb \
    -U postgres \
    -s public | less

# Pipe output to grep to find specific tables
python postgres_ddl_generator.py \
    -H localhost \
    -d mydb \
    -U postgres \
    -s public | grep "CREATE TABLE.*users"

# Count number of tables
python postgres_ddl_generator.py \
    -H localhost \
    -d mydb \
    -U postgres \
    -s public | grep -c "CREATE TABLE"
```

---

## Advanced Scenarios

### Example 10: Compare development and production schemas

```bash
#!/bin/bash
# compare_schemas.sh

echo "Generating DEV schema..."
python postgres_ddl_generator.py \
    -H dev-server.example.com \
    -d appdb \
    -U postgres \
    -s public \
    -o dev_schema.sql

echo "Generating PROD schema..."
python postgres_ddl_generator.py \
    -H prod-server.example.com \
    -d appdb \
    -U postgres \
    -s public \
    -o prod_schema.sql

echo "Comparing schemas..."
diff -u dev_schema.sql prod_schema.sql > schema_diff.txt

if [ $? -eq 0 ]; then
    echo "✓ Schemas are identical"
else
    echo "⚠ Schemas differ - see schema_diff.txt"
fi
```

### Example 11: Automated daily backup

```bash
#!/bin/bash
# daily_schema_backup.sh

# Configuration
HOST="localhost"
DATABASE="production_db"
USER="postgres"
SCHEMA="public"
BACKUP_DIR="/backups/schema"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate backup
DATE=$(date +%Y%m%d)
BACKUP_FILE="$BACKUP_DIR/schema_${DATABASE}_${SCHEMA}_${DATE}.sql"

python postgres_ddl_generator.py \
    -H "$HOST" \
    -d "$DATABASE" \
    -U "$USER" \
    -s "$SCHEMA" \
    -o "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Schema backup created: $BACKUP_FILE"
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    echo "✓ Backup compressed: ${BACKUP_FILE}.gz"
    
    # Delete backups older than retention period
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "✓ Old backups cleaned up"
else
    echo "✗ Backup failed!"
    exit 1
fi
```

Add to crontab:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/daily_schema_backup.sh >> /var/log/schema_backup.log 2>&1
```

### Example 12: Pre-deployment validation

```bash
#!/bin/bash
# validate_deployment.sh

echo "=== Pre-Deployment Schema Validation ==="

# Generate current production schema
python postgres_ddl_generator.py \
    -H prod-db.example.com \
    -d appdb \
    -U readonly \
    -s public \
    -o prod_current.sql

# Apply migrations to staging
echo "Applying migrations to staging..."
psql -h staging-db.example.com -U admin -d appdb -f migrations/*.sql

# Generate staging schema after migrations
python postgres_ddl_generator.py \
    -H staging-db.example.com \
    -d appdb \
    -U readonly \
    -s public \
    -o staging_after_migration.sql

# Compare and review
echo "Comparing schemas..."
diff -u prod_current.sql staging_after_migration.sql > migration_changes.txt

echo "Review migration_changes.txt before proceeding to production"
```

### Example 13: Schema versioning with Git

```bash
#!/bin/bash
# version_schema.sh

REPO_DIR="/path/to/schema-repo"
cd "$REPO_DIR"

# Generate current schema
python /path/to/postgres_ddl_generator.py \
    -H localhost \
    -d mydb \
    -U postgres \
    -s public \
    -o schema.sql

# Check if there are changes
if git diff --quiet schema.sql; then
    echo "No schema changes detected"
else
    echo "Schema changes detected"
    
    # Commit changes
    git add schema.sql
    git commit -m "Schema update $(date +%Y-%m-%d)"
    
    # Tag with version
    VERSION=$(date +v%Y.%m.%d-%H%M)
    git tag -a "$VERSION" -m "Schema version $VERSION"
    
    echo "Changes committed and tagged as $VERSION"
    
    # Push to remote
    git push origin main
    git push origin "$VERSION"
fi
```

---

## Integration Examples

### Example 14: Python script integration

```python
#!/usr/bin/env python3
"""
Example: Integrate DDL generator into Python application
"""

import subprocess
import json
from datetime import datetime

def generate_schema_ddl(host, database, user, password, schema='public'):
    """Generate DDL using the postgres_ddl_generator script."""
    
    cmd = [
        'python', 'postgres_ddl_generator.py',
        '-H', host,
        '-d', database,
        '-U', user,
        '-W', password,
        '-s', schema
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error generating DDL: {e.stderr}")
        return None

def main():
    # Configuration
    config = {
        'host': 'localhost',
        'database': 'mydb',
        'user': 'postgres',
        'password': 'postgres',
        'schema': 'public'
    }
    
    print("Generating schema DDL...")
    ddl = generate_schema_ddl(**config)
    
    if ddl:
        # Save to file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"schema_{timestamp}.sql"
        
        with open(filename, 'w') as f:
            f.write(ddl)
        
        print(f"✓ DDL saved to {filename}")
        
        # Analyze the DDL
        table_count = ddl.count('CREATE TABLE')
        fk_count = ddl.count('FOREIGN KEY')
        trigger_count = ddl.count('CREATE TRIGGER')
        
        print(f"\nSchema statistics:")
        print(f"  Tables: {table_count}")
        print(f"  Foreign Keys: {fk_count}")
        print(f"  Triggers: {trigger_count}")
    else:
        print("✗ Failed to generate DDL")

if __name__ == '__main__':
    main()
```

### Example 15: Bash script with error handling

```bash
#!/bin/bash
# robust_schema_backup.sh

set -euo pipefail  # Exit on error, undefined variable, or pipe failure

# Configuration
readonly CONFIG_FILE="db_config.env"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BACKUP_DIR="${SCRIPT_DIR}/backups"
readonly LOG_FILE="${SCRIPT_DIR}/schema_backup.log"

# Source configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Configuration file not found: $CONFIG_FILE" >&2
    exit 1
fi

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Main backup function
backup_schema() {
    local host=$1
    local database=$2
    local user=$3
    local schema=$4
    
    log "Starting schema backup for ${database}.${schema}"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR" || error_exit "Failed to create backup directory"
    
    # Generate filename
    local date_str=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/schema_${database}_${schema}_${date_str}.sql"
    
    # Run DDL generator
    if python postgres_ddl_generator.py \
        -H "$host" \
        -d "$database" \
        -U "$user" \
        -s "$schema" \
        -o "$backup_file" 2>&1 | tee -a "$LOG_FILE"; then
        
        log "✓ Backup successful: $backup_file"
        
        # Verify file was created and has content
        if [ -s "$backup_file" ]; then
            local size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file")
            log "✓ Backup file size: $size bytes"
            
            # Compress backup
            gzip "$backup_file"
            log "✓ Backup compressed: ${backup_file}.gz"
            
            return 0
        else
            error_exit "Backup file is empty"
        fi
    else
        error_exit "DDL generator failed"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    local retention_days=${1:-30}
    
    log "Cleaning up backups older than $retention_days days"
    
    local deleted_count=$(find "$BACKUP_DIR" \
        -name "*.sql.gz" \
        -mtime +$retention_days \
        -delete \
        -print | wc -l)
    
    log "✓ Deleted $deleted_count old backup(s)"
}

# Main execution
main() {
    log "=== Schema Backup Script Started ==="
    
    # Perform backup
    backup_schema \
        "${DB_HOST:-localhost}" \
        "${DB_NAME:?Database name required}" \
        "${DB_USER:?Database user required}" \
        "${DB_SCHEMA:-public}"
    
    # Cleanup old backups (keep last 30 days)
    cleanup_old_backups 30
    
    log "=== Schema Backup Script Completed ==="
}

# Run main function
main "$@"
```

Configuration file (`db_config.env`):
```bash
DB_HOST=localhost
DB_NAME=production_db
DB_USER=postgres
DB_SCHEMA=public
export PGPASSWORD=your_password_here
```

### Example 16: Docker integration

```dockerfile
# Dockerfile for schema backup container
FROM python:3.11-slim

# Install PostgreSQL client
RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY postgres_ddl_generator.py /app/
WORKDIR /app

# Run as non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["python", "postgres_ddl_generator.py"]
```

Docker Compose example:
```yaml
# docker-compose.yml
version: '3.8'

services:
  schema-backup:
    build: .
    environment:
      - PGPASSWORD=${DB_PASSWORD}
    command: >
      -H postgres
      -d mydb
      -U postgres
      -s public
      -o /output/schema.sql
    volumes:
      - ./output:/output
    depends_on:
      - postgres
  
  postgres:
    image: postgres:18
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Usage:
```bash
# Run schema backup in Docker
docker-compose run --rm schema-backup
```

---

## Tips for Production Use

### Tip 1: Security
```bash
# Never put passwords in command line or scripts
# Use .pgpass file instead

# Create ~/.pgpass file:
echo "localhost:5432:*:postgres:your_password" > ~/.pgpass
chmod 600 ~/.pgpass

# Now run without password:
python postgres_ddl_generator.py -H localhost -d mydb -U postgres
```

### Tip 2: Monitoring
```bash
# Monitor backup size over time
python postgres_ddl_generator.py -H localhost -d mydb -U postgres | \
    tee schema.sql | \
    wc -c | \
    awk '{print "Schema size:", $1, "bytes"}'
```

### Tip 3: Notifications
```bash
#!/bin/bash
# Send notification on backup completion

python postgres_ddl_generator.py \
    -H localhost \
    -d mydb \
    -U postgres \
    -o backup.sql

if [ $? -eq 0 ]; then
    # Send success notification (example with email)
    echo "Schema backup completed successfully" | \
        mail -s "Schema Backup Success" admin@example.com
else
    # Send failure notification
    echo "Schema backup FAILED" | \
        mail -s "Schema Backup FAILURE" admin@example.com
fi
```

---

## Common Issues and Solutions

### Issue 1: Permission denied

```bash
# Solution: Grant necessary permissions
psql -U postgres -d mydb -c "GRANT USAGE ON SCHEMA public TO readonly_user;"
psql -U postgres -d mydb -c "GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO readonly_user;"
```

### Issue 2: Connection timeout

```bash
# Solution: Increase timeout (modify script or use connection parameters)
export PGCONNECT_TIMEOUT=30
python postgres_ddl_generator.py -H remote-db -d mydb -U postgres
```

### Issue 3: Large databases

```bash
# For very large databases, you might want to process schema by schema
# or even table by table with a modified version of the script
```

---

For more examples and use cases, visit the project repository.
