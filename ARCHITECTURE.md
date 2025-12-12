# Architecture and Flow

This document explains how the PostgreSQL DDL Generator works internally.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (CLI)                     │
│                                                             │
│  Command Line Arguments → Argument Parser → Configuration  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              PostgresDDLGenerator Class                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          Connection Management                      │  │
│  │  • connect()                                        │  │
│  │  • disconnect()                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                              ↓                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          Metadata Retrieval Layer                   │  │
│  │  • get_user_types()     • get_tables()             │  │
│  │  • get_functions()       • get_columns()            │  │
│  │  • get_triggers()        • get_foreign_keys()       │  │
│  │  • get_primary_keys()    • get_sequence_info()      │  │
│  │  • get_partition_info()  • get_enum_values()        │  │
│  └─────────────────────────────────────────────────────┘  │
│                              ↓                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          Processing Layer                           │  │
│  │  • sort_tables_by_dependencies()                    │  │
│  │  • convert_sequence_to_serial()                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                              ↓                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          DDL Generation Layer                       │  │
│  │  • generate_user_type_ddl()                         │  │
│  │  • generate_table_ddl()                             │  │
│  │  • generate_column_ddl()                            │  │
│  │  • generate_foreign_key_ddl()                       │  │
│  │  • generate_ddl() [main orchestrator]               │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│                                                             │
│  System Catalogs:                                          │
│  • pg_class         • pg_constraint  • pg_sequence          │
│  • pg_attribute     • pg_type        • pg_enum              │
│  • pg_namespace     • pg_proc        • pg_trigger           │
│  • pg_depend        • pg_language    • pg_inherits          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Output                                   │
│                                                             │
│  SQL File or STDOUT                                         │
└─────────────────────────────────────────────────────────────┘
```

## Execution Flow

### Phase 1: Initialization

```
┌──────────────────────┐
│  Parse CLI Arguments │
│  • Host, Port        │
│  • Database, User    │
│  • Schema, Output    │
└──────────────────────┘
          ↓
┌──────────────────────┐
│  Create Generator    │
│  Instance            │
└──────────────────────┘
          ↓
┌──────────────────────┐
│  Establish DB        │
│  Connection          │
└──────────────────────┘
```

### Phase 2: Metadata Collection

```
┌─────────────────────────────────────────────────────────────┐
│                    Sequential Queries                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
          ┌───────────────────┴───────────────────┐
          ↓                                       ↓
┌───────────────────────┐           ┌───────────────────────┐
│  1. User-Defined Types│           │  2. Functions          │
│  • ENUMs              │           │  • Function defs       │
│  • Composite types    │           │  • Arguments           │
│  • Domains            │           │  • Return types        │
└───────────────────────┘           └───────────────────────┘
          ↓                                       ↓
┌───────────────────────┐           ┌───────────────────────┐
│  3. Tables            │           │  4. For Each Table:    │
│  • Regular tables     │           │  • Columns             │
│  • Partitioned tables │           │  • Sequences           │
│  • Partitions         │           │  • Primary keys        │
└───────────────────────┘           │  • Foreign keys        │
          ↓                         │  • Partition info      │
┌───────────────────────┐           └───────────────────────┘
│  5. All Foreign Keys  │                     ↓
│  • For dependencies   │           ┌───────────────────────┐
└───────────────────────┘           │  6. Triggers           │
          ↓                         │  • Per table           │
┌───────────────────────┐           │  • Or all triggers     │
│  7. Type Details      │           └───────────────────────┘
│  • Enum values        │
│  • Composite attrs    │
│  • Domain info        │
└───────────────────────┘
```

### Phase 3: Processing

```
┌─────────────────────────────────────────────────────────────┐
│              Dependency Analysis & Sorting                  │
└─────────────────────────────────────────────────────────────┘
          ↓
┌───────────────────────┐
│  Build Dependency     │
│  Graph                │
│  • Table → FK → Table │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  Topological Sort     │
│  • Referenced first   │
│  • Handle circular    │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  Sequence Analysis    │
│  • Detect serial cols │
│  • Match seq types    │
└───────────────────────┘
```

### Phase 4: DDL Generation

```
┌─────────────────────────────────────────────────────────────┐
│                    DDL Generation Order                     │
└─────────────────────────────────────────────────────────────┘
          ↓
┌───────────────────────┐
│  1. Header            │
│  • Schema name        │
│  • PG version         │
│  • Timestamp          │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  2. User Types        │
│  • CREATE TYPE        │
│  • ENUM values        │
│  • Composite attrs    │
│  • Domain rules       │
│  • Comments           │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  3. Functions         │
│  • CREATE FUNCTION    │
│  • Function body      │
│  • Language spec      │
│  • Comments           │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  4. Tables            │
│  • CREATE TABLE       │
│  • Columns (serial!)  │
│  • Inline PKs         │
│  • PARTITION BY       │
│  • Partitions         │
│  • Comments           │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  5. Foreign Keys      │
│  • ALTER TABLE        │
│  • ADD CONSTRAINT     │
│  • ON UPDATE/DELETE   │
└───────────────────────┘
          ↓
┌───────────────────────┐
│  6. Triggers          │
│  • CREATE TRIGGER     │
│  • Timing & event     │
│  • Execute function   │
└───────────────────────┘
```

### Phase 5: Output

```
┌───────────────────────┐
│  Output Decision      │
│  • File specified?    │
│  • Or stdout?         │
└───────────────────────┘
          ↓
    ┌─────┴─────┐
    ↓           ↓
┌────────┐  ┌──────────┐
│ To File│  │ To STDOUT│
└────────┘  └──────────┘
```

## Data Flow Diagram

```
                                Input
                                  │
                                  ↓
                    ┌─────────────────────────┐
                    │   PostgreSQL Database   │
                    │   System Catalogs       │
                    └─────────────────────────┘
                               ↓
              ┌────────────────┼────────────────┐
              ↓                ↓                ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   pg_class   │  │ pg_attribute │  │ pg_constraint│
    │  (tables)    │  │  (columns)   │  │  (PK/FK)     │
    └──────────────┘  └──────────────┘  └──────────────┘
              │                │                │
              └────────────────┼────────────────┘
                               ↓
                    ┌─────────────────────────┐
                    │  Metadata Dictionary    │
                    │  {table: {...}}         │
                    └─────────────────────────┘
                               ↓
                    ┌─────────────────────────┐
                    │  Processing             │
                    │  • Dependency sort      │
                    │  • Serial detection     │
                    └─────────────────────────┘
                               ↓
                    ┌─────────────────────────┐
                    │  DDL String Builder     │
                    │  • Format SQL           │
                    │  • Add comments         │
                    └─────────────────────────┘
                               ↓
                             Output
                        (File or STDOUT)
```

## Key Algorithms

### 1. Topological Sort for Table Dependencies

```python
def sort_tables_by_dependencies(tables):
    """
    Algorithm: DFS-based topological sort
    
    Input: List of tables with foreign key relationships
    Output: Sorted list where referenced tables come first
    
    Steps:
    1. Build adjacency list (table → referenced tables)
    2. Initialize visited and temp_mark sets
    3. For each unvisited table:
       a. Mark as temporarily visiting
       b. Recursively visit all dependencies
       c. Mark as permanently visited
       d. Add to result list
    4. Return reversed result (dependencies first)
    
    Handles circular dependencies gracefully.
    """
    dependencies = defaultdict(set)
    
    # Build graph
    for fk in foreign_keys:
        if fk.table != fk.ref_table:  # Skip self-references
            dependencies[fk.table].add(fk.ref_table)
    
    # DFS visit
    sorted_tables = []
    visited = set()
    temp_mark = set()
    
    def visit(table):
        if table in temp_mark:  # Circular dependency
            return
        if table in visited:
            return
        
        temp_mark.add(table)
        for dep in dependencies[table]:
            visit(dep)
        temp_mark.remove(table)
        visited.add(table)
        sorted_tables.append(table)
    
    # Visit all tables
    for table in tables:
        visit(table.name)
    
    return sorted_tables
```

### 2. Serial Type Detection

```python
def convert_sequence_to_serial(data_type, seq_info):
    """
    Algorithm: Sequence-to-Serial conversion
    
    Input: Column data type and sequence information
    Output: Serial type if applicable, else original type
    
    Logic:
    1. Check if sequence exists for column
    2. Match data type with sequence type:
       - int4/integer → serial
       - int8/bigint → bigserial
       - int2/smallint → smallserial
    3. Return converted type or original
    
    Benefits:
    - Cleaner DDL
    - Automatic sequence creation
    - Standard PostgreSQL idiom
    """
    if not seq_info:
        return data_type
    
    type_mapping = {
        'integer': 'serial',
        'int4': 'serial',
        'bigint': 'bigserial',
        'int8': 'bigserial',
        'smallint': 'smallserial',
        'int2': 'smallserial'
    }
    
    return type_mapping.get(data_type.lower(), data_type)
```

### 3. Partition Handling

```python
def handle_partitions(tables):
    """
    Algorithm: Two-pass partition handling
    
    Pass 1: Process parent partitioned tables
    - Identify tables with relkind = 'p'
    - Generate CREATE TABLE ... PARTITION BY ...
    - Extract partition strategy from pg_get_partkeydef()
    
    Pass 2: Process child partitions
    - Identify tables with relispartition = true
    - Generate CREATE TABLE ... PARTITION OF ...
    - Extract partition bounds from relpartbound
    
    Order: Parent tables before child partitions
    """
    parent_tables = [t for t in tables if t.is_partitioned]
    partitions = [t for t in tables if t.is_partition]
    
    # Process parents first
    for parent in parent_tables:
        generate_partitioned_table_ddl(parent)
    
    # Then process partitions
    for partition in partitions:
        generate_partition_ddl(partition)
```

## Database Queries

### Critical Queries

**1. Table Discovery:**
```sql
SELECT 
    c.relname AS table_name,
    c.relkind AS table_type,
    CASE WHEN c.relkind = 'p' THEN TRUE ELSE FALSE END AS is_partitioned,
    c.relispartition AS is_partition
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'schema_name'
    AND c.relkind IN ('r', 'p')
ORDER BY c.relispartition, c.relname;
```

**2. Column Details:**
```sql
SELECT 
    a.attname AS column_name,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
    a.attnotnull AS is_not_null,
    pg_catalog.pg_get_expr(ad.adbin, ad.adrelid) AS column_default
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
LEFT JOIN pg_catalog.pg_attrdef ad ON ad.adrelid = a.attrelid 
                                   AND ad.adnum = a.attnum
WHERE c.relname = 'table_name'
    AND a.attnum > 0
    AND NOT a.attisdropped
ORDER BY a.attnum;
```

**3. Foreign Key Detection:**
```sql
SELECT 
    con.conname AS constraint_name,
    array_agg(a.attname) AS column_names,
    fc.relname AS foreign_table_name,
    array_agg(fa.attname) AS foreign_column_names,
    con.confupdtype AS on_update,
    con.confdeltype AS on_delete
FROM pg_catalog.pg_constraint con
JOIN pg_catalog.pg_class c ON c.oid = con.conrelid
JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid 
                               AND a.attnum = ANY(con.conkey)
JOIN pg_catalog.pg_class fc ON fc.oid = con.confrelid
JOIN pg_catalog.pg_attribute fa ON fa.attrelid = fc.oid 
                                AND fa.attnum = ANY(con.confkey)
WHERE con.contype = 'f'
GROUP BY con.conname, fc.relname, con.confupdtype, con.confdeltype;
```

## Performance Optimizations

1. **Single Connection**: Reuse one connection for all queries
2. **Efficient Queries**: Use system catalog views, not information_schema
3. **Batch Processing**: Fetch all data before generating DDL
4. **Memory Efficient**: Stream output for large schemas
5. **Indexed Lookups**: Use OID relationships (faster than name joins)

## Error Handling

```
Connection Errors
    ↓
┌─────────────────────┐
│ Try to connect      │
│ • Retry logic?      │
│ • Timeout?          │
│ • Fail gracefully   │
└─────────────────────┘

Query Errors
    ↓
┌─────────────────────┐
│ Catch exceptions    │
│ • Log error         │
│ • Continue or stop? │
│ • Partial results?  │
└─────────────────────┘

Output Errors
    ↓
┌─────────────────────┐
│ File write issues   │
│ • Permission denied │
│ • Disk full         │
│ • Fallback to stdout│
└─────────────────────┘
```

## Extension Points

The architecture allows easy extension:

1. **Add new object types**: Create new `get_*()` and `generate_*_ddl()` methods
2. **Custom filters**: Add filtering logic in retrieval methods
3. **Output formats**: Replace DDL generation with JSON/YAML/etc.
4. **Parallel processing**: Add thread pool for large databases
5. **Incremental updates**: Compare current vs. saved DDL

## Security Model

```
┌─────────────────────────────────────────────────┐
│              Read-Only Operations                │
└─────────────────────────────────────────────────┘
                     ↓
        All queries are SELECT statements
                     ↓
┌─────────────────────────────────────────────────┐
│         No data modification possible            │
└─────────────────────────────────────────────────┘
                     ↓
        Only metadata from system catalogs
                     ↓
┌─────────────────────────────────────────────────┐
│       No access to user data in tables           │
└─────────────────────────────────────────────────┘
```

## Summary

The PostgreSQL DDL Generator uses a multi-phase approach:

1. **Connect**: Establish database connection
2. **Discover**: Query system catalogs for metadata
3. **Process**: Sort dependencies, detect serial types
4. **Generate**: Create DDL statements in correct order
5. **Output**: Write to file or stdout

The architecture is modular, extensible, and focused on generating accurate, executable DDL while handling PostgreSQL 18's advanced features like partitioning and user-defined types.
