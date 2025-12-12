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
        
        cursor.execute("""
            INSERT INTO order_items (order_id, product_name, quantity, price) VALUES
            (1, 'Item 1', 2, 49.99),
            (2, 'Item 2', 1, 149.99);
        """)
        
        # 12. Create a procedure
        cursor.execute("""
            CREATE OR REPLACE PROCEDURE process_order(p_user_id BIGINT, p_amount NUMERIC)
            LANGUAGE plpgsql
            AS $$
            BEGIN
                INSERT INTO orders (user_id, total_amount, status)
                VALUES (p_user_id, p_amount, 'pending');
                
                RAISE NOTICE 'Order created for user % with amount %', p_user_id, p_amount;
            END;
            $$;
            COMMENT ON PROCEDURE process_order(BIGINT, NUMERIC) IS 'Creates a new order for a user';
        """)
        print("✓ Created procedure: process_order")
        
        # 13. Create a simple view
        cursor.execute("""
            DROP VIEW IF EXISTS user_order_summary CASCADE;
            CREATE VIEW user_order_summary AS
            SELECT 
                u.id AS user_id,
                u.username,
                u.email_address,
                COUNT(o.id) AS total_orders,
                COALESCE(SUM(o.total_amount), 0) AS total_spent
            FROM users u
            LEFT JOIN orders o ON o.user_id = u.id
            GROUP BY u.id, u.username, u.email_address;
            COMMENT ON VIEW user_order_summary IS 'Summary of user orders and spending';
        """)
        print("✓ Created view: user_order_summary")
        
        # 14. Create a materialized view
        cursor.execute("""
            DROP MATERIALIZED VIEW IF EXISTS sales_summary CASCADE;
            CREATE MATERIALIZED VIEW sales_summary AS
            SELECT 
                DATE_TRUNC('month', sale_date) AS month,
                COUNT(*) AS total_sales,
                SUM(amount) AS total_amount,
                AVG(amount) AS avg_amount
            FROM sales
            GROUP BY DATE_TRUNC('month', sale_date)
            ORDER BY month;
            COMMENT ON MATERIALIZED VIEW sales_summary IS 'Monthly sales summary statistics';
        """)
        print("✓ Created materialized view: sales_summary")
        
        # 15. Create another function (non-trigger)
        cursor.execute("""
            CREATE OR REPLACE FUNCTION calculate_user_total(p_user_id BIGINT)
            RETURNS NUMERIC
            LANGUAGE plpgsql
            STABLE
            AS $$
            DECLARE
                v_total NUMERIC;
            BEGIN
                SELECT COALESCE(SUM(total_amount), 0)
                INTO v_total
                FROM orders
                WHERE user_id = p_user_id;
                
                RETURN v_total;
            END;
            $$;
            COMMENT ON FUNCTION calculate_user_total(BIGINT) IS 'Calculates total order amount for a user';
        """)
        print("✓ Created function: calculate_user_total")
        
        # 16. Create a standalone sequence
        cursor.execute("""
            DROP SEQUENCE IF EXISTS custom_id_seq CASCADE;
            CREATE SEQUENCE custom_id_seq
                START WITH 1000
                INCREMENT BY 10
                MINVALUE 1000
                MAXVALUE 999999
                CACHE 20;
            COMMENT ON SEQUENCE custom_id_seq IS 'Custom sequence for special IDs';
        """)
        print("✓ Created sequence: custom_id_seq")
        
        # 17. Create indexes
        cursor.execute("""
            CREATE INDEX idx_users_username ON users(username);
            CREATE INDEX idx_users_status ON users(status);
            CREATE INDEX idx_orders_user_date ON orders(user_id, order_date);
            CREATE INDEX idx_sales_date ON sales(sale_date);
            COMMENT ON INDEX idx_users_username IS 'Index for quick username lookups';
        """)
        print("✓ Created indexes on tables")
        
        # 18. Grant permissions
        # Note: This assumes there's a 'readonly' role. You may need to create it first.
        try:
            cursor.execute("CREATE ROLE readonly_user NOLOGIN;")
        except:
            pass  # Role might already exist
        
        cursor.execute("""
            GRANT SELECT ON users TO readonly_user;
            GRANT SELECT ON orders TO readonly_user;
            GRANT SELECT ON sales TO readonly_user;
            GRANT SELECT ON user_order_summary TO readonly_user;
            GRANT SELECT, UPDATE ON custom_id_seq TO readonly_user;
        """)
        print("✓ Granted permissions to readonly_user")
        
        # 19. Create extension (if not exists)
        try:
            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            """)
            print("✓ Created extension: uuid-ossp")
        except Exception as e:
            print(f"⚠ Could not create extension: {e}")
        
        # 20. Create foreign server and foreign table (example - requires postgres_fdw)
        try:
            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS postgres_fdw;
            """)
            
            cursor.execute("""
                DROP SERVER IF EXISTS remote_server CASCADE;
                CREATE SERVER remote_server
                    FOREIGN DATA WRAPPER postgres_fdw
                    OPTIONS (host 'localhost', dbname 'postgres', port '5432');
            """)
            
            cursor.execute("""
                CREATE FOREIGN TABLE remote_users (
                    id BIGINT,
                    username VARCHAR(50),
                    email VARCHAR(100)
                ) SERVER remote_server
                OPTIONS (schema_name 'public', table_name 'pg_user');
                COMMENT ON FOREIGN TABLE remote_users IS 'Foreign table mapping to remote database users';
            """)
            print("✓ Created foreign server and foreign table")
        except Exception as e:
            print(f"⚠ Could not create foreign table: {e}")
        
        print("\n✅ Example schema created successfully!")
        print("\nSchema now includes:")
        print("  • 3 User-defined types (ENUM, DOMAIN, COMPOSITE)")
        print("  • 2 Functions (trigger + regular)")
        print("  • 1 Procedure")
        print("  • 4 Tables (regular + partitioned)")
        print("  • 2 Partitions")
        print("  • 3 Foreign keys")
        print("  • 1 Trigger")
        print("  • 1 View")
        print("  • 1 Materialized view")
        print("  • 1 Standalone sequence")
        print("  • 4 Indexes")
        print("  • 1+ Extensions")
        print("  • 1 Foreign table")
        print("  • Grants on objects")
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
