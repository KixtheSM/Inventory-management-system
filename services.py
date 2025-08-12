"""
Business logic layer for Inventory Management System
Author: Sujal (BSc.IT)
"""
from typing import Any, Optional
from db import Database, utc_now_iso
from dao import ProductDAO, SupplierDAO, PurchaseDAO, SaleDAO


class InventoryService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.products = ProductDAO(db)
        self.suppliers = SupplierDAO(db)
        self.purchases = PurchaseDAO(db)
        self.sales = SaleDAO(db)

    # Products
    def add_product(self, name: str, sku: Optional[str], description: Optional[str], unit_price: float, reorder_level: int) -> int:
        if unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if reorder_level < 0:
            raise ValueError("Reorder level cannot be negative")
        return self.products.create(name, sku, description, unit_price, reorder_level)

    def update_product(self, product_id: int, **fields: Any) -> None:
        if "unit_price" in fields and fields["unit_price"] is not None and fields["unit_price"] < 0:
            raise ValueError("Unit price cannot be negative")
        if "reorder_level" in fields and fields["reorder_level"] is not None and fields["reorder_level"] < 0:
            raise ValueError("Reorder level cannot be negative")
        self.products.update(product_id, **fields)

    def delete_product(self, product_id: int) -> None:
        self.products.delete(product_id)

    def list_products(self) -> list[dict[str, Any]]:
        return self.products.list_all()

    def get_product(self, product_id: int) -> Optional[dict[str, Any]]:
        return self.products.get_by_id(product_id)

    # Suppliers
    def add_supplier(self, name: str, contact_name: Optional[str], phone: Optional[str], email: Optional[str], address: Optional[str]) -> int:
        return self.suppliers.create(name, contact_name, phone, email, address)

    def update_supplier(self, supplier_id: int, **fields: Any) -> None:
        self.suppliers.update(supplier_id, **fields)

    def delete_supplier(self, supplier_id: int) -> None:
        self.suppliers.delete(supplier_id)

    def list_suppliers(self) -> list[dict[str, Any]]:
        return self.suppliers.list_all()

    def get_supplier(self, supplier_id: int) -> Optional[dict[str, Any]]:
        return self.suppliers.get_by_id(supplier_id)

    # Transactions
    def record_purchase(self, product_id: int, quantity: int, unit_cost: float, supplier_id: Optional[int] = None) -> int:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if unit_cost < 0:
            raise ValueError("Unit cost cannot be negative")
        product = self.products.get_by_id(product_id)
        if product is None:
            raise ValueError("Product not found")
        if supplier_id is not None and self.suppliers.get_by_id(supplier_id) is None:
            raise ValueError("Supplier not found")
        purchase_id = self.purchases.create(product_id, supplier_id, quantity, unit_cost, utc_now_iso())
        self.products.adjust_stock(product_id, quantity)
        return purchase_id

    def record_sale(self, product_id: int, quantity: int, unit_price: float, customer_name: Optional[str] = None, notes: Optional[str] = None) -> int:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        product = self.products.get_by_id(product_id)
        if product is None:
            raise ValueError("Product not found")
        sale_id = self.sales.create(product_id, quantity, unit_price, utc_now_iso(), customer_name, notes)
        self.products.adjust_stock(product_id, -quantity)
        return sale_id

    # Reports
    def report_stock_levels(self) -> list[dict[str, Any]]:
        return self.products.list_all()

    def report_low_stock(self) -> list[dict[str, Any]]:
        products = self.products.list_all()
        return [p for p in products if int(p["quantity_in_stock"]) <= int(p["reorder_level"])]

    def report_sales_summary(self) -> list[dict[str, Any]]:
        return self.sales.sales_summary()

    def report_sales_between(self, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
        return self.sales.list_between(start_iso, end_iso)

    def report_purchases_between(self, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
        return self.purchases.list_between(start_iso, end_iso) 