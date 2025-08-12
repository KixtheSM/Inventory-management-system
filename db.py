import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import sys


def _get_app_dir() -> Path:
    if getattr(sys, "frozen", False):  # PyInstaller onefile
        return Path(sys.executable).parent
    return Path(__file__).parent


class Database:
    """Database helper class for SQLite operations"""
    
    def __init__(self, db_path=None):
        # Default to inventory.db in app directory
        if db_path is None:
            self.db_path = str(_get_app_dir() / "inventory.db")
        else:
            self.db_path = db_path

    def _connect(self):
        """Create database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables if they don't exist"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    sku TEXT UNIQUE,
                    description TEXT,
                    unit_price REAL NOT NULL DEFAULT 0,
                    quantity_in_stock INTEGER NOT NULL DEFAULT 0,
                    reorder_level INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            
            # Suppliers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    contact_name TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            
            # Purchases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    supplier_id INTEGER,
                    quantity INTEGER NOT NULL,
                    unit_cost REAL NOT NULL,
                    purchased_at TEXT NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
                );
            """)
            
            # Sales table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    sold_at TEXT NOT NULL,
                    customer_name TEXT,
                    notes TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
                );
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchases_product_id ON purchases(product_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales(product_id);")
            
            conn.commit()

    def execute(self, sql, params=()):
        """Execute SQL and return last row id"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid

    def query_all(self, sql, params=()):
        """Query and return all rows as list of dicts"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def query_one(self, sql, params=()):
        """Query and return single row as dict, or None"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None


def utc_now_iso():
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat() 