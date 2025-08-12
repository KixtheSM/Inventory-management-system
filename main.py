#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventory Management System - Main Entry Point
Author: Sujal
Created during BSc.IT studies
"""

from db import Database
from services import InventoryService
import cli


def main():
    print("Choose mode:")
    print("1) GUI (recommended)")
    print("2) Console (CLI)")
    choice = input("Enter 1 or 2 (default 1): ").strip() or "1"
    if choice == "2":
        db = Database()
        db.init_db()
        service = InventoryService(db)
        cli.run(service)
    else:
        from gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main() 