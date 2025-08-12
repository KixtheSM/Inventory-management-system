"""
GUI Application for Inventory Management System (Tkinter)
Author: Sujal (BSc.IT)
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Optional
import csv
from pathlib import Path
from datetime import datetime, timezone
import json
import tkinter.font as tkfont

from db import Database
from services import InventoryService


def format_currency(value: float, symbol: str) -> str:
    return f"{symbol}{value:,.2f}"


SETTINGS_FILE = Path(__file__).with_name("settings.json")


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def enable_treeview_sort(tree: ttk.Treeview) -> None:
    def sortby(col_id: str, reverse: bool) -> None:
        rows = [(tree.set(k, col_id), k) for k in tree.get_children("")]

        def parse_val(v: str):
            try:
                s = v.replace(",", "").strip()
                if s and not s[0].isdigit() and s[0] in {"₹", "$", "€", "£"}:
                    s = s[1:]
                return float(s)
            except Exception:
                return v.lower()

        rows.sort(key=lambda t: parse_val(t[0]), reverse=reverse)
        for idx, (_, k) in enumerate(rows):
            tree.move(k, "", idx)
        tree.heading(col_id, command=lambda: sortby(col_id, not reverse))

    for col in tree["columns"]:
        tree.heading(col, command=lambda c=col: sortby(c, False))


class ProductsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, service: InventoryService, currency_symbol: str) -> None:
        super().__init__(parent)
        self.service = service
        self.currency_symbol = currency_symbol

        self.columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()

        search_frame = ttk.Frame(self)
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(search_frame, text="Find", command=self.refresh).pack(side=tk.LEFT)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=(6, 0))

        buttons = ttk.Frame(self)
        buttons.grid(row=1, column=0, sticky="ew", padx=10)
        ttk.Button(buttons, text="Add", command=self.add_product).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Edit", command=self.edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Delete", command=self.delete_selected).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Refresh", command=self.refresh).pack(side=tk.LEFT)

        columns = ("id", "name", "sku", "unit_price", "quantity_in_stock", "reorder_level")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("sku", text="SKU")
        self.tree.heading("unit_price", text="Unit Price")
        self.tree.heading("quantity_in_stock", text="Stock")
        self.tree.heading("reorder_level", text="Reorder")
        self.tree.column("id", width=50, anchor=tk.E)
        self.tree.column("name", width=260)
        self.tree.column("sku", width=140)
        self.tree.column("unit_price", width=120, anchor=tk.E)
        self.tree.column("quantity_in_stock", width=100, anchor=tk.E)
        self.tree.column("reorder_level", width=100, anchor=tk.E)

        # Add vertical scrollbar
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0), pady=(6, 10))
        vsb.grid(row=2, column=1, sticky="ns", pady=(6, 10))

        # Apply sorting behavior
        enable_treeview_sort(self.tree)

        # Striped rows style
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=24)
        self.tree.tag_configure("odd", background="#fbfbfb")

        self.refresh()

    def clear_search(self) -> None:
        self.search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        q = (self.search_var.get() or "").lower()
        products = self.service.list_products()
        if q:
            products = [p for p in products if q in (p['name'] or '').lower() or q in (p.get('sku') or '').lower()]
        for p in products:
            price_str = format_currency(float(p['unit_price']), self.currency_symbol)
            self.tree.insert("", tk.END, values=(p['id'], p['name'], p.get('sku') or '', price_str, p['quantity_in_stock'], p['reorder_level']))

    def _get_selected_id(self) -> Optional[int]:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], 'values')
        return int(values[0])

    def add_product(self) -> None:
        ProductDialog(self, title="Add Product", on_submit=self._create_product)

    def _create_product(self, data: dict) -> None:
        try:
            self.service.add_product(data['name'], data.get('sku'), data.get('description'), float(data['unit_price']), int(data['reorder_level']))
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def edit_selected(self) -> None:
        product_id = self._get_selected_id()
        if product_id is None:
            messagebox.showinfo("Select", "Please select a product to edit.", parent=self)
            return
        product = self.service.get_product(product_id)
        if product is None:
            messagebox.showerror("Error", "Product not found.", parent=self)
            return
        ProductDialog(self, title="Edit Product", initial=product, on_submit=lambda d: self._update_product(product_id, d))

    def _update_product(self, product_id: int, data: dict) -> None:
        try:
            fields = {
                'name': data['name'],
                'sku': data.get('sku'),
                'description': data.get('description'),
                'unit_price': float(data['unit_price']),
                'reorder_level': int(data['reorder_level']),
            }
            self.service.update_product(product_id, **fields)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_selected(self) -> None:
        product_id = self._get_selected_id()
        if product_id is None:
            messagebox.showinfo("Select", "Please select a product to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Delete selected product?", parent=self):
            return
        try:
            self.service.delete_product(product_id)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def export_csv(self) -> None:
        products = self.service.list_products()
        filepath = filedialog.asksaveasfilename(parent=self, title="Export Products CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile=f"products_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv")
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "name", "sku", "description", "unit_price", "quantity_in_stock", "reorder_level"])
                for p in products:
                    writer.writerow([p['id'], p['name'], p.get('sku') or '', p.get('description') or '', p['unit_price'], p['quantity_in_stock'], p['reorder_level']])
            messagebox.showinfo("Export", f"Exported to {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class SuppliersTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, service: InventoryService) -> None:
        super().__init__(parent)
        self.service = service

        self.columnconfigure(0, weight=1)

        buttons = ttk.Frame(self)
        buttons.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        ttk.Button(buttons, text="Add", command=self.add_supplier).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Edit", command=self.edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Delete", command=self.delete_selected).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=6)

        columns = ("id", "name", "contact_name", "phone", "email", "address")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        for c, label, width, anchor in (
            ("id", "ID", 50, tk.E),
            ("name", "Name", 220, tk.W),
            ("contact_name", "Contact", 150, tk.W),
            ("phone", "Phone", 130, tk.W),
            ("email", "Email", 220, tk.W),
            ("address", "Address", 300, tk.W),
        ):
            self.tree.heading(c, text=label)
            self.tree.column(c, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(6, 10))
        vsb.grid(row=1, column=1, sticky="ns", pady=(6, 10))

        enable_treeview_sort(self.tree)
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=24)
        self.tree.tag_configure("odd", background="#fbfbfb")

        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for s in self.service.list_suppliers():
            self.tree.insert("", tk.END, values=(s['id'], s['name'], s.get('contact_name') or '', s.get('phone') or '', s.get('email') or '', s.get('address') or ''))

    def _get_selected_id(self) -> Optional[int]:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], 'values')
        return int(values[0])

    def add_supplier(self) -> None:
        SupplierDialog(self, title="Add Supplier", on_submit=self._create_supplier)

    def _create_supplier(self, data: dict) -> None:
        try:
            self.service.add_supplier(data['name'], data.get('contact_name'), data.get('phone'), data.get('email'), data.get('address'))
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def edit_selected(self) -> None:
        sid = self._get_selected_id()
        if sid is None:
            messagebox.showinfo("Select", "Please select a supplier to edit.", parent=self)
            return
        supplier = self.service.get_supplier(sid)
        if supplier is None:
            messagebox.showerror("Error", "Supplier not found.", parent=self)
            return
        SupplierDialog(self, title="Edit Supplier", initial=supplier, on_submit=lambda d: self._update_supplier(sid, d))

    def _update_supplier(self, sid: int, data: dict) -> None:
        try:
            self.service.update_supplier(
                sid,
                name=data['name'],
                contact_name=data.get('contact_name'),
                phone=data.get('phone'),
                email=data.get('email'),
                address=data.get('address'),
            )
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_selected(self) -> None:
        sid = self._get_selected_id()
        if sid is None:
            messagebox.showinfo("Select", "Please select a supplier to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Delete selected supplier?", parent=self):
            return
        try:
            self.service.delete_supplier(sid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class TransactionsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, service: InventoryService, currency_symbol: str) -> None:
        super().__init__(parent)
        self.service = service
        self.currency_symbol = currency_symbol

        container = ttk.Notebook(self)
        container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.purchase_frame = ttk.Frame(container)
        self.sale_frame = ttk.Frame(container)
        container.add(self.purchase_frame, text="Record Purchase")
        container.add(self.sale_frame, text="Record Sale")

        # Purchase UI
        self.product_var_p = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.qty_var_p = tk.StringVar()
        self.cost_var = tk.StringVar()

        self._build_purchase_ui()

        # Sale UI
        self.product_var_s = tk.StringVar()
        self.qty_var_s = tk.StringVar()
        self.price_var = tk.StringVar()
        self.customer_var = tk.StringVar()
        self.notes_var = tk.StringVar()

        self._build_sale_ui()

    def _get_products_list(self) -> list[tuple[int, str]]:
        return [(p['id'], f"{p['name']} (SKU: {p.get('sku') or '-'})") for p in self.service.list_products()]

    def _get_suppliers_list(self) -> list[tuple[int, str]]:
        return [(s['id'], s['name']) for s in self.service.list_suppliers()]

    def _build_purchase_ui(self) -> None:
        frm = self.purchase_frame
        ttk.Label(frm, text="Product:").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        self.products_cb_p = ttk.Combobox(frm, textvariable=self.product_var_p, state="readonly", width=40)
        self.products_cb_p.grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(frm, text="Supplier:").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        self.suppliers_cb = ttk.Combobox(frm, textvariable=self.supplier_var, state="readonly", width=40)
        self.suppliers_cb.grid(row=1, column=1, padx=8, pady=6)
        ttk.Label(frm, text="Quantity:").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.qty_var_p).grid(row=2, column=1, padx=8, pady=6)
        ttk.Label(frm, text=f"Unit Cost ({self.currency_symbol}):").grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.cost_var).grid(row=3, column=1, padx=8, pady=6)
        ttk.Button(frm, text="Record Purchase", command=self.record_purchase).grid(row=4, column=0, columnspan=2, padx=8, pady=(10, 8))

        frm.grid_columnconfigure(1, weight=1)
        self._refresh_purchase_choices()

    def _refresh_purchase_choices(self) -> None:
        prods = self._get_products_list()
        sups = self._get_suppliers_list()
        self.products_cb_p['values'] = [f"{pid}: {label}" for pid, label in prods]
        self.suppliers_cb['values'] = [f"{sid}: {label}" for sid, label in sups]
        if prods:
            self.products_cb_p.current(0)
        if sups:
            self.suppliers_cb.current(0)

    def record_purchase(self) -> None:
        try:
            pid = int((self.product_var_p.get().split(":", 1)[0]))
            sid_str = self.supplier_var.get()
            sid = int((sid_str.split(":", 1)[0])) if sid_str else None
            qty = int(self.qty_var_p.get())
            cost = float(self.cost_var.get())
            self.service.record_purchase(pid, qty, cost, sid)
            messagebox.showinfo("Success", "Purchase recorded.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _build_sale_ui(self) -> None:
        frm = self.sale_frame
        ttk.Label(frm, text="Product:").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        self.products_cb_s = ttk.Combobox(frm, textvariable=self.product_var_s, state="readonly", width=40)
        self.products_cb_s.grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(frm, text="Quantity:").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.qty_var_s).grid(row=1, column=1, padx=8, pady=6)
        ttk.Label(frm, text=f"Unit Price ({self.currency_symbol}):").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.price_var).grid(row=2, column=1, padx=8, pady=6)
        ttk.Label(frm, text="Customer (optional):").grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.customer_var).grid(row=3, column=1, padx=8, pady=6)
        ttk.Label(frm, text="Notes (optional):").grid(row=4, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.notes_var).grid(row=4, column=1, padx=8, pady=6)
        ttk.Button(frm, text="Record Sale", command=self.record_sale).grid(row=5, column=0, columnspan=2, padx=8, pady=(10, 8))

        frm.grid_columnconfigure(1, weight=1)
        self._refresh_sale_choices()

    def _refresh_sale_choices(self) -> None:
        prods = self._get_products_list()
        self.products_cb_s['values'] = [f"{pid}: {label}" for pid, label in prods]
        if prods:
            self.products_cb_s.current(0)

    def record_sale(self) -> None:
        try:
            pid = int((self.product_var_s.get().split(":", 1)[0]))
            qty = int(self.qty_var_s.get())
            price = float(self.price_var.get())
            customer = self.customer_var.get().strip() or None
            notes = self.notes_var.get().strip() or None
            self.service.record_sale(pid, qty, price, customer, notes)
            messagebox.showinfo("Success", "Sale recorded.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class ReportsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, service: InventoryService, currency_symbol: str) -> None:
        super().__init__(parent)
        self.service = service
        self.currency_symbol = currency_symbol

        self.view_var = tk.StringVar(value="Stock Levels")
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(top, text="Report:").pack(side=tk.LEFT)
        self.view_cb = ttk.Combobox(top, textvariable=self.view_var, state="readonly", values=["Stock Levels", "Low Stock", "Sales Summary"], width=20)
        self.view_cb.pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Run", command=self.refresh).pack(side=tk.LEFT)
        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=6)

        # Keep stable column identifiers and just change headings/widths
        self.tree = ttk.Treeview(self, columns=("col1", "col2", "col3"), show="headings", height=16)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        view = self.view_var.get()
        if view == "Stock Levels":
            labels = ("Product", "Stock", "Reorder")
            for i, h in enumerate(labels):
                self.tree.heading(f"col{i+1}", text=h)
                self.tree.column(f"col{i+1}", width=(250 if i == 0 else 100), anchor=(tk.W if i == 0 else tk.E))
            for p in self.service.report_stock_levels():
                self.tree.insert("", tk.END, values=(p['name'], p['quantity_in_stock'], p['reorder_level']))
        elif view == "Low Stock":
            labels = ("Product", "Stock", "Reorder")
            for i, h in enumerate(labels):
                self.tree.heading(f"col{i+1}", text=h)
                self.tree.column(f"col{i+1}", width=(250 if i == 0 else 100), anchor=(tk.W if i == 0 else tk.E))
            for p in self.service.report_low_stock():
                self.tree.insert("", tk.END, values=(p['name'], p['quantity_in_stock'], p['reorder_level']))
        else:
            labels = ("Product", "Qty Sold", "Revenue")
            for i, h in enumerate(labels):
                self.tree.heading(f"col{i+1}", text=h)
                self.tree.column(f"col{i+1}", width=(250 if i == 0 else 120), anchor=(tk.W if i == 0 else tk.E))
            for r in self.service.report_sales_summary():
                revenue = format_currency(float(r['total_revenue'] or 0), self.currency_symbol)
                self.tree.insert("", tk.END, values=(r['product_name'], int(r['total_quantity_sold'] or 0), revenue))

    def export_csv(self) -> None:
        view = self.view_var.get()
        default_name = {
            "Stock Levels": "stock_levels.csv",
            "Low Stock": "low_stock.csv",
            "Sales Summary": "sales_summary.csv",
        }[view]
        filepath = filedialog.asksaveasfilename(parent=self, title="Export CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile=default_name)
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if view == "Stock Levels":
                    writer.writerow(["product", "stock", "reorder"])
                    for p in self.service.report_stock_levels():
                        writer.writerow([p['name'], p['quantity_in_stock'], p['reorder_level']])
                elif view == "Low Stock":
                    writer.writerow(["product", "stock", "reorder"])
                    for p in self.service.report_low_stock():
                        writer.writerow([p['name'], p['quantity_in_stock'], p['reorder_level']])
                else:
                    writer.writerow(["product", "qty_sold", "revenue"])
                    for r in self.service.report_sales_summary():
                        writer.writerow([r['product_name'], int(r['total_quantity_sold'] or 0), float(r['total_revenue'] or 0)])
            messagebox.showinfo("Export", f"Exported to {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class SettingsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, on_currency_change) -> None:
        super().__init__(parent)
        self.on_currency_change = on_currency_change
        settings = load_settings()
        self.currency_var = tk.StringVar(value=settings.get("currency", "₹"))

        ttk.Label(self, text="Currency symbol:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=(12, 6))
        ttk.Entry(self, textvariable=self.currency_var, width=10).grid(row=0, column=1, padx=8, pady=(12, 6))
        ttk.Button(self, text="Save", command=self.save).grid(row=0, column=2, padx=8, pady=(12, 6))

        ttk.Label(self, text="Backup database:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=6)
        ttk.Button(self, text="Create backup", command=self.backup_db).grid(row=1, column=1, padx=8, pady=6)

        self.grid_columnconfigure(3, weight=1)

    def save(self) -> None:
        symbol = self.currency_var.get().strip() or "₹"
        settings = load_settings()
        settings["currency"] = symbol
        save_settings(settings)
        self.on_currency_change(symbol)
        messagebox.showinfo("Saved", "Settings updated.", parent=self)

    def backup_db(self) -> None:
        db_file = Path(__file__).with_name("inventory.db")
        if not db_file.exists():
            messagebox.showerror("Error", "Database not found.", parent=self)
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        default_name = f"inventory_{timestamp}.db"
        filepath = filedialog.asksaveasfilename(parent=self, title="Save backup", defaultextension=".db", filetypes=[("SQLite DB", "*.db")], initialfile=default_name)
        if not filepath:
            return
        try:
            data = db_file.read_bytes()
            Path(filepath).write_bytes(data)
            messagebox.showinfo("Backup", f"Backup saved: {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class ProductDialog(tk.Toplevel):
    def __init__(self, parent: ProductsTab, title: str, on_submit, initial: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.on_submit = on_submit

        self.name_var = tk.StringVar(value=(initial or {}).get('name') or '')
        self.sku_var = tk.StringVar(value=(initial or {}).get('sku') or '')
        self.desc_var = tk.StringVar(value=(initial or {}).get('description') or '')
        self.price_var = tk.StringVar(value=str((initial or {}).get('unit_price') or ''))
        self.reorder_var = tk.StringVar(value=str((initial or {}).get('reorder_level') or '0'))

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        ttk.Label(body, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.name_var, width=40).grid(row=0, column=1, pady=4)
        ttk.Label(body, text="SKU:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.sku_var, width=40).grid(row=1, column=1, pady=4)
        ttk.Label(body, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.desc_var, width=40).grid(row=2, column=1, pady=4)
        ttk.Label(body, text="Unit price:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.price_var, width=20).grid(row=3, column=1, sticky=tk.W, pady=4)
        ttk.Label(body, text="Reorder level:").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.reorder_var, width=20).grid(row=4, column=1, sticky=tk.W, pady=4)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.RIGHT, padx=8)

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _save(self) -> None:
        data = {
            'name': self.name_var.get().strip(),
            'sku': self.sku_var.get().strip() or None,
            'description': self.desc_var.get().strip() or None,
            'unit_price': self.price_var.get().strip() or '0',
            'reorder_level': self.reorder_var.get().strip() or '0',
        }
        if not data['name']:
            messagebox.showerror("Error", "Name is required.", parent=self)
            return
        self.on_submit(data)
        self.destroy()


class SupplierDialog(tk.Toplevel):
    def __init__(self, parent: SuppliersTab, title: str, on_submit, initial: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.on_submit = on_submit

        self.name_var = tk.StringVar(value=(initial or {}).get('name') or '')
        self.contact_var = tk.StringVar(value=(initial or {}).get('contact_name') or '')
        self.phone_var = tk.StringVar(value=(initial or {}).get('phone') or '')
        self.email_var = tk.StringVar(value=(initial or {}).get('email') or '')
        self.address_var = tk.StringVar(value=(initial or {}).get('address') or '')

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        ttk.Label(body, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.name_var, width=40).grid(row=0, column=1, pady=4)
        ttk.Label(body, text="Contact:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.contact_var, width=40).grid(row=1, column=1, pady=4)
        ttk.Label(body, text="Phone:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.phone_var, width=40).grid(row=2, column=1, pady=4)
        ttk.Label(body, text="Email:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.email_var, width=40).grid(row=3, column=1, pady=4)
        ttk.Label(body, text="Address:").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=self.address_var, width=40).grid(row=4, column=1, pady=4)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Save", command=self._save).pack(side=tk.RIGHT, padx=8)

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _save(self) -> None:
        data = {
            'name': self.name_var.get().strip(),
            'contact_name': self.contact_var.get().strip() or None,
            'phone': self.phone_var.get().strip() or None,
            'email': self.email_var.get().strip() or None,
            'address': self.address_var.get().strip() or None,
        }
        if not data['name']:
            messagebox.showerror("Error", "Name is required.", parent=self)
            return
        self.on_submit(data)
        self.destroy()


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("900x600")

        # Init core services
        self.database = Database()
        self.database.init_db()
        self.service = InventoryService(self.database)

        # Simple runtime settings (currency)
        self.currency_symbol = "₹"

        # Apply professional styling
        self._apply_style()

        # Menu bar
        self._build_menu()

        # Notebook tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook = notebook

        self.products_tab = ProductsTab(notebook, self.service, self.currency_symbol)
        self.suppliers_tab = SuppliersTab(notebook, self.service)
        self.transactions_tab = TransactionsTab(notebook, self.service, self.currency_symbol)
        self.reports_tab = ReportsTab(notebook, self.service, self.currency_symbol)
        self.settings_tab = SettingsTab(notebook, self._on_currency_change)

        notebook.add(self.products_tab, text="Products")
        notebook.add(self.suppliers_tab, text="Suppliers")
        notebook.add(self.transactions_tab, text="Transactions")
        notebook.add(self.reports_tab, text="Reports")
        notebook.add(self.settings_tab, text="Settings")

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken")
        status.pack(side=tk.BOTTOM, fill=tk.X)

        # Center window
        self.after(50, self._center_on_screen)

        # Global shortcuts
        self.bind_all("<F5>", lambda e: self.refresh_current_tab())
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _apply_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        # Fonts
        default_font = tkfont.nametofont("TkDefaultFont")
        family = "Segoe UI" if "Segoe UI" in tkfont.families() else default_font.cget("family")
        size = max(10, default_font.cget("size"))
        default_font.configure(family=family, size=size)
        heading_font = tkfont.Font(family=family, size=size, weight="bold")
        style.configure("TButton", padding=6)
        style.configure("Treeview", rowheight=26, font=default_font)
        style.configure("Treeview.Heading", font=heading_font)
        style.configure("TNotebook.Tab", padding=(12, 6))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Backup Database", command=self._menu_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh (F5)", command=self.refresh_current_tab)
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _menu_backup(self) -> None:
        # Delegate to settings tab backup
        try:
            self.settings_tab.backup_db()
            self.set_status("Backup created")
        except Exception:
            pass

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "Inventory Management System\nBuilt with Python, Tkinter, and SQLite\nAuthor: Sujal",
            parent=self,
        )

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def refresh_current_tab(self) -> None:
        tab = self.notebook.nametowidget(self.notebook.select())
        if hasattr(tab, "refresh"):
            try:
                tab.refresh()
                self.set_status("Refreshed")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)

    def _center_on_screen(self) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_exit(self) -> None:
        if messagebox.askokcancel("Exit", "Quit the application?"):
            self.destroy()

    def _on_currency_change(self, symbol: str) -> None:
        self.currency_symbol = symbol
        # Update dependent tabs
        self.products_tab.currency_symbol = symbol
        self.transactions_tab.currency_symbol = symbol
        self.reports_tab.currency_symbol = symbol
        self.products_tab.refresh()
        self.reports_tab.refresh()


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
