#!/usr/bin/env python3
"""
Fix package size displaying as 'Unknown' in frontend
Updates all NULL or empty package_size values in the package_information table
"""

import sqlite3
from datetime import datetime

def fix_package_sizes():
    """Fix package sizes based on weight and dimensions"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        print("🔧 Fixing Package Sizes...")
        
        # First, check current state
        c.execute("SELECT COUNT(*) FROM package_information WHERE package_size IS NULL OR package_size = ''")
        null_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM package_information")
        total_count = c.fetchone()[0]
        
        print(f"📊 Found {null_count} records with missing package_size out of {total_count} total records")
        
        if null_count == 0:
            print("✅ All records already have package_size values!")
            return True
        
        # Update package sizes based on weight and dimensions
        print("🎯 Calculating package sizes based on weight and dimensions...")
        
        # Get all records that need fixing
        c.execute("""
            SELECT id, weight, width, height, length 
            FROM package_information 
            WHERE package_size IS NULL OR package_size = ''
        """)
        
        records_to_fix = c.fetchall()
        fixed_count = 0
        
        for record_id, weight, width, height, length in records_to_fix:
            # Calculate package size based on weight and dimensions
            package_size = "Medium"  # Default
            
            # Size logic based on weight and volume
            volume = (width or 0) * (height or 0) * (length or 0)  # cm³
            weight_kg = weight or 0
            
            if weight_kg <= 0.3 and volume <= 1000:  # <= 300g and <= 1000 cm³
                package_size = "Small"
            elif weight_kg >= 1.5 or volume >= 8000:  # >= 1.5kg or >= 8000 cm³
                package_size = "Large"
            else:
                package_size = "Medium"
            
            # Update the record
            c.execute("""
                UPDATE package_information 
                SET package_size = ? 
                WHERE id = ?
            """, (package_size, record_id))
            
            fixed_count += 1
            print(f"✅ Fixed record {record_id}: {weight}kg, {width}x{height}x{length}cm → {package_size}")
        
        conn.commit()
        
        # Verify the fix
        c.execute("SELECT COUNT(*) FROM package_information WHERE package_size IS NULL OR package_size = ''")
        remaining_null = c.fetchone()[0]
        
        print(f"\n📊 Results:")
        print(f"   Fixed: {fixed_count} records")
        print(f"   Remaining with missing size: {remaining_null}")
        
        # Show current distribution
        c.execute("""
            SELECT package_size, COUNT(*) as count 
            FROM package_information 
            GROUP BY package_size 
            ORDER BY count DESC
        """)
        
        sizes = c.fetchall()
        print(f"\n📦 Package Size Distribution:")
        for size, count in sizes:
            print(f"   {size}: {count} packages")
        
        conn.close()
        
        print(f"\n🎉 Package size fix completed! Frontend should now show correct sizes.")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing package sizes: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Package Size Fix...")
    success = fix_package_sizes()
    if success:
        print("✅ Package size fix completed successfully!")
        print("💡 Refresh your frontend to see the updated sizes!")
    else:
        print("❌ Package size fix failed!")