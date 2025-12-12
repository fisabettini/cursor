#!/usr/bin/env python3
"""
Example script demonstrating the PostgreSQL DDL Generator
This creates a sample database schema to test the DDL generator
"""

import psycopg2
import sys


def create_example_schema(conn_params):
    """Create an example schema with various PostgreSQL features."""
    
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        print("Creating example schema...")
        
        # Create schema if needed
        cursor.execute("CREATE SCHEMA IF NOT EXISTS test_schema;")
        cursor.execute("SET search_path TO test_schema;")
        
        # 1. Create ENUM type
        cursor.execute("""
            DROP TYPE IF EXISTS user_status CASCADE;
            CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended');
        """)
        print("✓ Created ENUM type: user_status")
        
        # 2. Create DOMAIN type
        cursor.execute("""
            DROP DOMAIN IF EXISTS email CASCADE;
            CREATE DOMAIN email AS TEXT
            CHECK (VALUE ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');
        """)
        print("✓ Created DOMAIN type: email")
        
        # 3. Create COMPOSITE type
        cursor.execute("""
            DROP TYPE IF EXISTS address_type CASCADE;
            CREATE TYPE address_type AS (
                street TEXT,
                city TEXT,
                state TEXT,
                zipcode VARCHAR(10)
            );
        """)
        print("✓ Created COMPOSITE type: address_type")
        
        # 4. Create regular table with serial
        cursor.execute("""
            DROP TABLE IF EXISTS users CASCADE;
            CREATE TABLE users (
                id BIGSERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email_address email NOT NULL,
                status user_status DEFAULT 'active',
                address address_type,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            COMMENT ON TABLE users IS 'User accounts table';
            COMMENT ON COLUMN users.email_address IS 'User email address';
        """)
        print("✓ Created table: users")
        
        # 5. Create partitioned table
        cursor.execute("""
            DROP TABLE IF EXISTS sales CASCADE;
            CREATE TABLE sales (
                id BIGSERIAL,
                user_id BIGINT NOT NULL,
                sale_date DATE NOT NULL,
                amount NUMERIC(10, 2),
                product_name VARCHAR(100),
                PRIMARY KEY (id, sale_date)
            ) PARTITION BY RANGE (sale_date);
            COMMENT ON TABLE sales IS 'Sales transactions partitioned by date';
        """)
        print("✓ Created partitioned table: sales")
        
        # 6. Create partitions
        cursor.execute("""
            DROP TABLE IF EXISTS sales_2024_q1;
            CREATE TABLE sales_2024_q1 PARTITION OF sales
            FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
        """)
        print("✓ Created partition: sales_2024_q1")
        
        cursor.execute("""
            DROP TABLE IF EXISTS sales_2024_q2;
            CREATE TABLE sales_2024_q2 PARTITION OF sales
            FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');
        """)
        print("✓ Created partition: sales_2024_q2")
        
        # 7. Create dependent table with foreign key
        cursor.execute("""
            DROP TABLE IF EXISTS orders CASCADE;
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount NUMERIC(10, 2),
                status VARCHAR(20) DEFAULT 'pending',
                CONSTRAINT fk_orders_user FOREIGN KEY (user_id) 
                    REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
            );
            COMMENT ON TABLE orders IS 'Customer orders';
        """)
        print("✓ Created table with FK: orders")
        
        # 8. Add foreign key to sales
        cursor.execute("""
            ALTER TABLE sales 
            ADD CONSTRAINT fk_sales_user FOREIGN KEY (user_id) 
            REFERENCES users(id) ON DELETE RESTRICT;
        """)
        print("✓ Added FK to sales table")
        
        # 9. Create trigger function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            COMMENT ON FUNCTION update_updated_at_column() IS 'Updates the updated_at timestamp';
        """)
        print("✓ Created trigger function: update_updated_at_column")
        
        # 10. Create trigger
        cursor.execute("""
            DROP TRIGGER IF EXISTS trigger_update_users_timestamp ON users;
            CREATE TRIGGER trigger_update_users_timestamp
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
        print("✓ Created trigger: trigger_update_users_timestamp")
        
        # 11. Create another table to test dependency ordering
        cursor.execute("""
            DROP TABLE IF EXISTS order_items CASCADE;
            CREATE TABLE order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL,
                product_name VARCHAR(100),
                quantity INTEGER NOT NULL DEFAULT 1,
                price NUMERIC(10, 2),
                CONSTRAINT fk_order_items_order FOREIGN KEY (order_id)
                    REFERENCES orders(id) ON DELETE CASCADE
            );
        """)
        print("✓ Created table with FK dependency: order_items")
        
        # Insert some sample data
        cursor.execute("""
            INSERT INTO users (username, email_address, status) VALUES
            ('john_doe', 'john@example.com', 'active'),
            ('jane_smith', 'jane@example.com', 'active');
        """)
        
        cursor.execute("""
            INSERT INTO orders (user_id, total_amount) VALUES
            (1, 99.99),
            (2, 149.99);
        """)
        
        cursor.execute("""
            INSERT INTO sales (user_id, sale_date, amount, product_name) VALUES
            (1, '2024-01-15', 99.99, 'Product A'),
            (2, '2024-05-20', 149.99, 'Product B');
        """)
        
        print("\n✅ Example schema created successfully!")
        print("\nYou can now generate DDL using:")
        print(f"python postgres_ddl_generator.py -H {conn_params['host']} -d {conn_params['database']} -U {conn_params['user']} -s test_schema -o example_output.sql")
        
    except Exception as e:
        print(f"❌ Error creating example schema: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    # Example connection parameters
    # Modify these to match your PostgreSQL setup
    conn_params = {
        'host': 'localhost',
        'port': '5432',
        'database': 'postgres',  # Change this to your database
        'user': 'postgres',      # Change this to your user
        'password': 'postgres'   # Change this to your password
    }
    
    print("PostgreSQL DDL Generator - Example Schema Creator")
    print("=" * 60)
    print("\nThis script creates an example schema to demonstrate the DDL generator.")
    print("\nConnection parameters:")
    print(f"  Host: {conn_params['host']}")
    print(f"  Port: {conn_params['port']}")
    print(f"  Database: {conn_params['database']}")
    print(f"  User: {conn_params['user']}")
    print("\nPress Ctrl+C to cancel or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    
    create_example_schema(conn_params)
