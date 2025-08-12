# Inventory Management System (Console + SQLite)

# Author : Sujal Mandal

A console-based Inventory Management System to track product stock, sales, purchases, and supplier data.

- Developed in Python
- Uses SQLite for local database storage (file `inventory.db`)
- Built as a personal project during BSc.IT studies by Sujal

## Features
- Product management: add, list, update, delete, set reorder level
- Supplier management: add, list, update, delete
- Purchasing: record purchases, automatically increases stock
- Sales: record sales, validates stock, automatically decreases stock
- Reports:
  - Current stock levels
  - Low stock items (below reorder level)
  - Sales summary and product performance
  - Sales and purchases between dates
- Usability & Professional touches:
  - Search/filter products
  - CSV export of products and reports (saved in `exports/`)
  - Delete confirmations
  - Currency symbol setting (saved in `settings.json`)
  - One-click database backup (saved in `backups/`)

## Requirements
- Python 3.9+
- No external dependencies required

## Quick Start
1. Open a terminal in the project directory.
2. Run the app:
   ```bash
   python main.py
   ```
3. The database (`inventory.db`) will be initialized on first run.

## Project Structure
- `main.py`: Entry point; initializes the database and starts the CLI
- `db.py`: Database helper and schema initialization
- `dao.py`: Data Access Objects for Products, Suppliers, Purchases, Sales
- `services.py`: Business logic and validations
- `cli.py`: Console menus and user interaction

## Common Tasks
- Add a product: Main Menu → Manage Products → Add Product
- Add a supplier: Main Menu → Manage Suppliers → Add Supplier
- Record purchase: Main Menu → Record Purchase
- Record sale: Main Menu → Record Sale
- View stock report: Main Menu → Reports → Stock Levels
- View low stock: Main Menu → Reports → Low Stock

## Backups
The app stores data in `inventory.db` in this folder. Back up this file to save your data.

## Notes
- All timestamps are stored in ISO 8601 format (UTC).
- Monetary values are stored as REAL in SQLite; for production systems, consider using DECIMAL-like handling. 

## GUI Usage
- Run GUI via:
  ```bash
  python main.py
  ```
  Choose option 1 for GUI, or run the packaged `dist/InventoryGUI.exe` if built.

## Upload to GitHub
1. Create a new repository on GitHub (no README/License to avoid conflicts)
2. Initialize and push locally:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Inventory Management System (Python + SQLite + Tkinter GUI)"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

The `.gitignore` excludes build folders, binaries, caches, and local databases.

## Build a Windows .exe (optional)

If you want a single-file executable to run on this computer without Python:

1. Install PyInstaller (one-time):
   ```bash
   pip install pyinstaller
   ```
2. Build the exe:
   ```bash
   pyinstaller --onefile --name InventoryIMS main.py
   ```
3. Find the executable in the `dist/` folder as `InventoryIMS.exe`.
4. Place `InventoryIMS.exe` anywhere (e.g., Desktop). It will create/use `inventory.db` next to the exe.
5. Optional folders `exports/`, `backups/`, and `settings.json` will also appear next to the exe when used. 
