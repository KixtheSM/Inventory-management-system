"""
Data Access Layer for the Inventory Management System
Author: Sujal (BSc.IT)
"""
from typing import Any, Optional
from db import Database, utc_now_iso


class ProductDAO:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, name: str, sku: Optional[str], description: Optional[str], unit_price: float, reorder_level: int) -> int:
        now = utc_now_iso()
        return self.db.execute(
            """
            INSERT INTO products (name, sku, description, unit_price, quantity_in_stock, reorder_level, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (name, sku, description, unit_price, reorder_level, now, now),
        )

    def update(self, product_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utc_now_iso()
        columns = ", ".join([f"{key} = ?" for key in fields.keys()])
        params = list(fields.values()) + [product_id]
        self.db.execute(f"UPDATE products SET {columns} WHERE id = ?", params)

    def delete(self, product_id: int) -> None:
        self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def list_all(self) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT id, name, sku, description, unit_price, quantity_in_stock, reorder_level, created_at, updated_at
            FROM products
            ORDER BY name COLLATE NOCASE
            """
        )

    def get_by_id(self, product_id: int) -> Optional[dict[str, Any]]:
        return self.db.query_one("SELECT * FROM products WHERE id = ?", (product_id,))

    def get_by_name_or_sku(self, token: str) -> Optional[dict[str, Any]]:
        return self.db.query_one(
            "SELECT * FROM products WHERE name = ? OR sku = ?",
            (token, token),
        )

    def adjust_stock(self, product_id: int, delta: int) -> None:
        product = self.get_by_id(product_id)
        if product is None:
            raise ValueError("Product not found")
        new_qty = int(product["quantity_in_stock"]) + int(delta)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self.update(product_id, quantity_in_stock=new_qty)


class SupplierDAO:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, name: str, contact_name: Optional[str], phone: Optional[str], email: Optional[str], address: Optional[str]) -> int:
        return self.db.execute(
            """
            INSERT INTO suppliers (name, contact_name, phone, email, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, contact_name, phone, email, address, utc_now_iso()),
        )

    def update(self, supplier_id: int, **fields: Any) -> None:
        if not fields:
            return
        columns = ", ".join([f"{key} = ?" for key in fields.keys()])
        params = list(fields.values()) + [supplier_id]
        self.db.execute(f"UPDATE suppliers SET {columns} WHERE id = ?", params)

    def delete(self, supplier_id: int) -> None:
        self.db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))

    def list_all(self) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT id, name, contact_name, phone, email, address, created_at
            FROM suppliers
            ORDER BY name COLLATE NOCASE
            """
        )

    def get_by_id(self, supplier_id: int) -> Optional[dict[str, Any]]:
        return self.db.query_one("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))

    def get_by_name(self, name: str) -> Optional[dict[str, Any]]:
        return self.db.query_one("SELECT * FROM suppliers WHERE name = ?", (name,))


class PurchaseDAO:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, product_id: int, supplier_id: Optional[int], quantity: int, unit_cost: float, purchased_at_iso: str) -> int:
        return self.db.execute(
            """
            INSERT INTO purchases (product_id, supplier_id, quantity, unit_cost, purchased_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, supplier_id, quantity, unit_cost, purchased_at_iso),
        )

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT p.id, p.product_id, pr.name AS product_name, p.supplier_id, s.name AS supplier_name,
                   p.quantity, p.unit_cost, p.purchased_at
            FROM purchases p
            LEFT JOIN products pr ON pr.id = p.product_id
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            ORDER BY p.purchased_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_between(self, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT p.id, p.product_id, pr.name AS product_name, p.supplier_id, s.name AS supplier_name,
                   p.quantity, p.unit_cost, p.purchased_at
            FROM purchases p
            LEFT JOIN products pr ON pr.id = p.product_id
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.purchased_at BETWEEN ? AND ?
            ORDER BY p.purchased_at ASC
            """,
            (start_iso, end_iso),
        )


class SaleDAO:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, product_id: int, quantity: int, unit_price: float, sold_at_iso: str, customer_name: Optional[str], notes: Optional[str]) -> int:
        return self.db.execute(
            """
            INSERT INTO sales (product_id, quantity, unit_price, sold_at, customer_name, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, quantity, unit_price, sold_at_iso, customer_name, notes),
        )

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT s.id, s.product_id, p.name AS product_name, s.quantity, s.unit_price, s.sold_at,
                   s.customer_name, s.notes
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.sold_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_between(self, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT s.id, s.product_id, p.name AS product_name, s.quantity, s.unit_price, s.sold_at,
                   s.customer_name, s.notes
            FROM sales s
            JOIN products p ON p.id = s.product_id
            WHERE s.sold_at BETWEEN ? AND ?
            ORDER BY s.sold_at ASC
            """,
            (start_iso, end_iso),
        )

    def sales_summary(self) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            SELECT p.id AS product_id, p.name AS product_name,
                   SUM(s.quantity) AS total_quantity_sold,
                   SUM(s.quantity * s.unit_price) AS total_revenue
            FROM sales s
            JOIN products p ON p.id = s.product_id
            GROUP BY p.id, p.name
            ORDER BY total_revenue DESC
            """
        ) 