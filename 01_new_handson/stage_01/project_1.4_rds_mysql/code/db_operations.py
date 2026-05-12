"""
db_operations.py — Connect to RDS MySQL and run basic CRUD operations.

Prerequisites:
    pip install pymysql

Environment Variables (set before running):
    DB_HOST   — RDS endpoint (e.g. mydb.abc123.us-east-1.rds.amazonaws.com)
    DB_PORT   — MySQL port (default: 3306)
    DB_USER   — Database username
    DB_PASS   — Database password
    DB_NAME   — Database name

Usage:
    export DB_HOST=mydb.abc123.us-east-1.rds.amazonaws.com
    export DB_USER=admin
    export DB_PASS=yourpassword
    export DB_NAME=shopdb
    python db_operations.py

What this script demonstrates:
    1. Connect to RDS MySQL using environment variables
    2. Create an 'orders' table (idempotent)
    3. Insert 5 sample orders
    4. Query and print results with formatting
    5. Connection pooling pattern using a context manager
"""

import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Generator

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("[ERROR] pymysql is not installed. Run: pip install pymysql")
    sys.exit(1)


# ── Configuration from environment variables ──────────────────────────────────

def get_db_config() -> dict:
    """
    Read database connection parameters from environment variables.
    Raises ValueError if required variables are missing.
    """
    required = ["DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"]
    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Set them before running:\n"
            "  export DB_HOST=<rds-endpoint>\n"
            "  export DB_USER=<username>\n"
            "  export DB_PASS=<password>\n"
            "  export DB_NAME=<database>"
        )

    return {
        "host":    os.environ["DB_HOST"],
        "port":    int(os.environ.get("DB_PORT", "3306")),
        "user":    os.environ["DB_USER"],
        "password": os.environ["DB_PASS"],
        "database": os.environ["DB_NAME"],
        "charset":  "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        # SSL for RDS (recommended in production)
        # "ssl": {"ca": "/path/to/rds-ca-2019-root.pem"},
        "connect_timeout": 10,
        "autocommit": False,
    }


# ── Connection pool pattern ───────────────────────────────────────────────────

class ConnectionPool:
    """
    Simple connection pool using a list of reusable connections.

    In production, use a proper pool like:
        - SQLAlchemy connection pool
        - PyMySQL with a pool wrapper
        - AWS RDS Proxy (recommended for Lambda/serverless)
    """

    def __init__(self, config: dict, pool_size: int = 5):
        self._config = config
        self._pool_size = pool_size
        self._pool: list[pymysql.Connection] = []

    def _create_connection(self) -> pymysql.Connection:
        """Create a new database connection."""
        return pymysql.connect(**self._config)

    def get_connection(self) -> pymysql.Connection:
        """Get a connection from the pool, or create a new one."""
        # Reuse an existing connection if available and still alive
        while self._pool:
            conn = self._pool.pop()
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception:
                pass  # Connection is dead — discard and try next
        return self._create_connection()

    def return_connection(self, conn: pymysql.Connection):
        """Return a connection to the pool."""
        if len(self._pool) < self._pool_size:
            self._pool.append(conn)
        else:
            conn.close()

    def close_all(self):
        """Close all pooled connections."""
        for conn in self._pool:
            try:
                conn.close()
            except Exception:
                pass
        self._pool.clear()


# ── Context manager for safe connection handling ──────────────────────────────

@contextmanager
def get_db_connection(pool: ConnectionPool) -> Generator[pymysql.Connection, None, None]:
    """
    Context manager that borrows a connection from the pool,
    commits on success, rolls back on error, and returns the connection.

    Usage:
        with get_db_connection(pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
    """
    conn = pool.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.return_connection(conn)


# ── DDL: create table ─────────────────────────────────────────────────────────

CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    order_id     INT          AUTO_INCREMENT PRIMARY KEY,
    customer     VARCHAR(100) NOT NULL,
    product      VARCHAR(200) NOT NULL,
    quantity     INT          NOT NULL DEFAULT 1,
    unit_price   DECIMAL(10,2) NOT NULL,
    total_price  DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    status       ENUM('pending','processing','shipped','delivered','cancelled')
                 NOT NULL DEFAULT 'pending',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer (customer),
    INDEX idx_status   (status),
    INDEX idx_created  (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def create_tables(pool: ConnectionPool):
    """Create the orders table if it doesn't already exist."""
    print("[*] Creating tables...")
    with get_db_connection(pool) as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_ORDERS_TABLE)
    print("[+] Table 'orders' ready.")


# ── DML: insert sample data ───────────────────────────────────────────────────

SAMPLE_ORDERS = [
    ("Alice Johnson",  "AWS Solutions Architect Book",  2, Decimal("49.99"),  "pending"),
    ("Bob Smith",      "Mechanical Keyboard",           1, Decimal("129.00"), "processing"),
    ("Carol White",    "USB-C Hub 7-in-1",              3, Decimal("35.50"),  "shipped"),
    ("David Lee",      "Noise Cancelling Headphones",   1, Decimal("299.99"), "delivered"),
    ("Eve Martinez",   "Laptop Stand Adjustable",       2, Decimal("45.00"),  "pending"),
]

INSERT_ORDER = """
INSERT INTO orders (customer, product, quantity, unit_price, status)
VALUES (%s, %s, %s, %s, %s)
"""


def insert_sample_orders(pool: ConnectionPool):
    """Insert 5 sample orders into the orders table."""
    print("\n[*] Inserting sample orders...")
    with get_db_connection(pool) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(INSERT_ORDER, SAMPLE_ORDERS)
            print(f"[+] Inserted {cursor.rowcount} orders.")


# ── DML: query and display ────────────────────────────────────────────────────

def query_orders(pool: ConnectionPool):
    """Query all orders and print a formatted table."""
    print("\n[*] Querying orders...")

    with get_db_connection(pool) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT order_id, customer, product, quantity,
                       unit_price, total_price, status, created_at
                FROM orders
                ORDER BY order_id
            """)
            rows = cursor.fetchall()

    if not rows:
        print("  (No orders found)")
        return

    # Print formatted table
    print(f"\n  {'ID':<5} {'Customer':<18} {'Product':<35} {'Qty':<5} {'Total':>10} {'Status':<12}")
    print("  " + "-" * 90)
    for row in rows:
        print(
            f"  {row['order_id']:<5} "
            f"{row['customer']:<18} "
            f"{row['product']:<35} "
            f"{row['quantity']:<5} "
            f"${row['total_price']:>9.2f} "
            f"{row['status']:<12}"
        )

    # Aggregate summary
    with get_db_connection(pool) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*)           AS total_orders,
                    SUM(total_price)   AS revenue,
                    AVG(total_price)   AS avg_order_value,
                    status,
                    COUNT(*)           AS count_by_status
                FROM orders
                GROUP BY status
            """)
            stats = cursor.fetchall()

    print("\n  ── Order Status Breakdown ──")
    for stat in stats:
        print(f"    {stat['status']:<15} {stat['count_by_status']} orders")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  RDS MySQL — Database Operations Demo")
    print("=" * 60)

    # Load config from environment
    try:
        config = get_db_config()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"  Host     : {config['host']}")
    print(f"  Database : {config['database']}")
    print(f"  User     : {config['user']}")

    # Create connection pool
    pool = ConnectionPool(config, pool_size=5)

    try:
        # Test connectivity
        print("\n[*] Testing connection...")
        with get_db_connection(pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION() AS version, NOW() AS server_time")
                info = cursor.fetchone()
                print(f"[+] Connected! MySQL {info['version']} — Server time: {info['server_time']}")

        # Run operations
        create_tables(pool)
        insert_sample_orders(pool)
        query_orders(pool)

        print("\n" + "=" * 60)
        print("  All operations completed successfully.")
        print("=" * 60 + "\n")

    except pymysql.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        sys.exit(1)
    finally:
        pool.close_all()
        print("[*] Connection pool closed.")


if __name__ == "__main__":
    main()
