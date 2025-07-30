#!/usr/bin/env python3
"""
Database Clearing Script for MicroProject
=========================================

This script clears all data from the database tables and resets them to their initial state.
It provides options to clear specific tables or all tables.

Usage:
    python clear_db.py [options]

Options:
    --all              Clear all tables (default)
    --orders           Clear only orders table
    --qr-scans         Clear only qr_scans table
    --packages         Clear only package_information table
    --scanned-codes    Clear only scanned_codes table
    --sensor-data      Clear only loaded_sensor_data table
    --confirm          Skip confirmation prompt (for automation)
    --help             Show this help message

Author: GitHub Copilot
Date: July 28, 2025
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime

# Database file path
DB_PATH = 'database.db'

# Table definitions for recreation
TABLES = {
    'orders': '''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            address TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
    ''',
    
    'qr_scans': '''
        CREATE TABLE IF NOT EXISTS qr_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_data TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            device TEXT NOT NULL,
            is_valid BOOLEAN NOT NULL,
            order_id INTEGER,
            validation_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    
    'package_information': '''
        CREATE TABLE IF NOT EXISTS package_information (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            order_number TEXT,
            weight REAL,
            width REAL,
            height REAL,
            length REAL,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''',
    
    'scanned_codes': '''
        CREATE TABLE IF NOT EXISTS scanned_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            order_number TEXT NOT NULL,
            isverified TEXT NOT NULL CHECK(isverified IN ('yes', 'no')),
            scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            device TEXT DEFAULT 'raspberry_pi',
            FOREIGN KEY (order_id) REFERENCES orders (id),
            UNIQUE(order_id)
        )
    ''',
    
    'loaded_sensor_data': '''
        CREATE TABLE IF NOT EXISTS loaded_sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight REAL,
            width REAL,
            height REAL,
            length REAL,
            package_size TEXT,
            loadcell_timestamp TEXT,
            box_dimensions_timestamp TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    '''
}

def print_banner():
    """Print script banner"""
    print("=" * 60)
    print("  MicroProject Database Clearing Script")
    print("=" * 60)
    print(f"  Database: {DB_PATH}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

def check_database_exists():
    """Check if database file exists"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file '{DB_PATH}' not found!")
        print("   Make sure you're running this script from the backend directory.")
        return False
    return True

def get_table_stats(conn):
    """Get current table statistics"""
    stats = {}
    cursor = conn.cursor()
    
    for table_name in TABLES.keys():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            stats[table_name] = count
        except sqlite3.OperationalError:
            stats[table_name] = 0  # Table doesn't exist
    
    return stats

def print_table_stats(stats, title="Current Database Statistics"):
    """Print table statistics"""
    print(f"\n📊 {title}:")
    print("-" * 40)
    total_records = 0
    for table_name, count in stats.items():
        print(f"  {table_name:<20}: {count:>8} records")
        total_records += count
    print("-" * 40)
    print(f"  {'TOTAL':<20}: {total_records:>8} records")
    print()

def clear_table(conn, table_name):
    """Clear a specific table"""
    cursor = conn.cursor()
    try:
        # Delete all data
        cursor.execute(f"DELETE FROM {table_name}")
        deleted_count = cursor.rowcount
        
        # Reset auto-increment counter
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
        
        conn.commit()
        return deleted_count, None
    except sqlite3.Error as e:
        return 0, str(e)

def recreate_table(conn, table_name):
    """Drop and recreate a table"""
    cursor = conn.cursor()
    try:
        # Drop table
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Recreate table
        cursor.execute(TABLES[table_name])
        
        # Create index for scanned_codes if needed
        if table_name == 'scanned_codes':
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_scanned_codes_order_id 
                ON scanned_codes(order_id)
            ''')
        
        conn.commit()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

def clear_tables(tables_to_clear, recreate=False, confirm=True):
    """Clear specified tables"""
    
    if not check_database_exists():
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        
        # Get current stats
        before_stats = get_table_stats(conn)
        print_table_stats(before_stats, "Before Clearing")
        
        # Confirmation
        if confirm:
            if tables_to_clear == list(TABLES.keys()):
                action = "clear ALL tables"
            else:
                action = f"clear tables: {', '.join(tables_to_clear)}"
            
            print(f"⚠️  You are about to {action}!")
            print("   This action cannot be undone.")
            
            response = input("\n   Do you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("❌ Operation cancelled by user.")
                return False
        
        print(f"\n🧹 {'Recreating' if recreate else 'Clearing'} tables...")
        print("-" * 40)
        
        success_count = 0
        total_deleted = 0
        
        for table_name in tables_to_clear:
            if recreate:
                success, error = recreate_table(conn, table_name)
                if success:
                    print(f"  ✅ {table_name:<20}: Recreated")
                    success_count += 1
                else:
                    print(f"  ❌ {table_name:<20}: Error - {error}")
            else:
                deleted_count, error = clear_table(conn, table_name)
                if error is None:
                    print(f"  ✅ {table_name:<20}: {deleted_count:>8} records deleted")
                    success_count += 1
                    total_deleted += deleted_count
                else:
                    print(f"  ❌ {table_name:<20}: Error - {error}")
        
        print("-" * 40)
        print(f"  ✅ Success: {success_count}/{len(tables_to_clear)} tables processed")
        
        if not recreate:
            print(f"  🗑️  Total deleted: {total_deleted} records")
        
        # Get final stats
        after_stats = get_table_stats(conn)
        print_table_stats(after_stats, "After Clearing")
        
        conn.close()
        
        print("✅ Database clearing completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Clear MicroProject database tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--all', action='store_true', 
                       help='Clear all tables (default)')
    parser.add_argument('--orders', action='store_true',
                       help='Clear only orders table')
    parser.add_argument('--qr-scans', action='store_true',
                       help='Clear only qr_scans table')
    parser.add_argument('--packages', action='store_true',
                       help='Clear only package_information table')
    parser.add_argument('--scanned-codes', action='store_true',
                       help='Clear only scanned_codes table')
    parser.add_argument('--sensor-data', action='store_true',
                       help='Clear only loaded_sensor_data table')
    parser.add_argument('--recreate', action='store_true',
                       help='Drop and recreate tables instead of just clearing data')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt (for automation)')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Determine which tables to clear
    tables_to_clear = []
    
    if args.orders:
        tables_to_clear.append('orders')
    if getattr(args, 'qr_scans', False):
        tables_to_clear.append('qr_scans')
    if args.packages:
        tables_to_clear.append('package_information')
    if getattr(args, 'scanned_codes', False):
        tables_to_clear.append('scanned_codes')
    if getattr(args, 'sensor_data', False):
        tables_to_clear.append('loaded_sensor_data')
    
    # If no specific tables selected or --all specified, clear all tables
    if not tables_to_clear or args.all:
        tables_to_clear = list(TABLES.keys())
    
    # Perform clearing
    success = clear_tables(
        tables_to_clear, 
        recreate=args.recreate,
        confirm=not args.confirm
    )
    
    if success:
        print("\n🎉 Database clearing operation completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Database clearing operation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
