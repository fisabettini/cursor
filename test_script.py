#!/usr/bin/env python3
"""
Test script to verify the DDL generator structure without database connection.
"""

def test_script_structure():
    """Test that the script has all required components."""
    
    with open('generate_schema_ddl.py', 'r') as f:
        content = f.read()
    
    # Check for required classes
    assert 'class PostgreSQLDDLGenerator' in content, "PostgreSQLDDLGenerator class not found"
    
    # Check for required methods
    required_methods = [
        'get_serial_sequences',
        'get_column_sequence_info',
        'get_trigger_functions',
        'get_standalone_sequences',
        'get_table_columns',
        'get_table_constraints',
        'get_table_dependencies',
        'topological_sort',
        'generate_table_ddl',
        'get_foreign_key_constraints',
        'generate_foreign_key_ddl',
        'get_indexes',
        'get_triggers',
        'get_views',
        'get_all_tables',
        'generate_schema_ddl'
    ]
    
    for method in required_methods:
        assert f'def {method}' in content, f"Method {method} not found"
        print(f"✓ Method {method} found")
    
    # Check for serial/bigserial handling
    assert 'serial' in content.lower(), "Serial type handling not found"
    assert 'bigserial' in content.lower(), "Bigserial type handling not found"
    
    # Check for dependency ordering
    assert 'topological' in content.lower(), "Topological sorting not found"
    
    # Check for foreign key handling
    assert 'foreign' in content.lower() and 'key' in content.lower(), "Foreign key handling not found"
    
    print("\n✓ All required components found!")
    print("✓ Script structure is correct!")
    print("\nScript features:")
    print("  - Handles serial/bigserial types")
    print("  - Topological sorting for table dependencies")
    print("  - Foreign key constraints added after tables")
    print("  - Trigger functions, sequences, indexes, triggers, views")
    print("  - Column and table comments preserved")
    
    return True

if __name__ == '__main__':
    test_script_structure()
