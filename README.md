# PostgreSQL 17 - Partitioned Parent Tables Queries

This repository contains SQL queries to select all parent tables that are partitioned in PostgreSQL 17.

## Files

1. **select_partitioned_parent_tables.sql** - Standard query with essential information
2. **select_partitioned_parent_tables_detailed.sql** - Comprehensive query with size and metadata
3. **select_partitioned_parent_tables_simple.sql** - Simple query listing table names only

## Query Explanation

### Key Concepts

In PostgreSQL 17, partitioned parent tables can be identified using:
- `pg_class.relkind = 'p'` - Indicates a partitioned table
- `pg_partitioned_table` - System catalog containing partition strategy information
- `pg_inherits` - Tracks parent-child relationships between tables

### Partition Strategies

PostgreSQL supports three partition strategies:
- **LIST** - Partition by discrete values
- **RANGE** - Partition by value ranges
- **HASH** - Partition by hash function

## Usage

Connect to your PostgreSQL 17 database and run any of the queries:

```bash
psql -U username -d database_name -f select_partitioned_parent_tables.sql
```

Or copy and paste the query directly into your SQL client.

## What the Queries Return

- **schema_name**: Schema containing the partitioned table
- **table_name**: Name of the partitioned parent table
- **partition_strategy**: Type of partitioning (LIST, RANGE, or HASH)
- **partition_key**: Column(s) used for partitioning
- **partition_count**: Number of child partitions
- **size information**: Storage sizes (in detailed query)

## Example Output

```
 schema_name |    table_name     | partition_strategy_name | partition_key | partition_count
-------------+-------------------+-------------------------+---------------+-----------------
 public      | sales_data        | RANGE                   | sale_date     | 12
 public      | user_events       | HASH                    | user_id       | 8
 analytics   | measurement_data  | LIST                    | region        | 5
```
