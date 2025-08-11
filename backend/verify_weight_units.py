#!/usr/bin/env python3
"""
Weight Unit Verification Script
Checks if weight values in database are in correct units
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_weight_units():
    """Check weight values in database for unit consistency"""
    try:
        # Connect to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Check loaded_sensor_data table
        logger.info("=" * 50)
        logger.info("WEIGHT UNIT VERIFICATION")
        logger.info("=" * 50)
        
        # Get recent weight entries
        c.execute('''
            SELECT id, weight, created_at 
            FROM loaded_sensor_data 
            WHERE weight IS NOT NULL 
            ORDER BY id DESC 
            LIMIT 10
        ''')
        
        weight_entries = c.fetchall()
        
        if not weight_entries:
            logger.warning("No weight entries found in loaded_sensor_data table")
            return
        
        logger.info("Recent weight entries from loaded_sensor_data:")
        logger.info("-" * 50)
        
        issues_found = False
        
        for entry_id, weight, created_at in weight_entries:
            weight_kg = float(weight)
            weight_grams = weight_kg * 1000
            
            # Check if weight seems to be in wrong units
            if weight_kg > 100:  # Unlikely to have packages > 100kg
                status = "❌ SUSPICIOUS (too large - might be in grams instead of kg)"
                issues_found = True
            elif weight_kg < 0.001:  # Unlikely to have packages < 1g
                status = "❌ SUSPICIOUS (too small - might be incorrectly converted)"
                issues_found = True
            elif 0.001 <= weight_kg <= 100:  # Reasonable package weight range
                status = "✅ OK"
            else:
                status = "❓ UNKNOWN"
                
            logger.info(f"ID {entry_id}: {weight_kg:.6f} kg ({weight_grams:.1f} g) - {status}")
            logger.info(f"  Created: {created_at}")
            logger.info("")
        
        # Summary
        logger.info("=" * 50)
        logger.info("SUMMARY")
        logger.info("=" * 50)
        
        if issues_found:
            logger.error("❌ ISSUES FOUND - Some weight values appear to be in wrong units")
            logger.info("Expected values:")
            logger.info("  - Small packages: 0.1 - 2.0 kg (100 - 2000 g)")
            logger.info("  - Medium packages: 2.0 - 10.0 kg (2000 - 10000 g)")
            logger.info("  - Large packages: 10.0 - 50.0 kg (10000 - 50000 g)")
            logger.info("")
            logger.info("If values are too large (>100kg), they might be stored in grams instead of kg")
            logger.info("If values are too small (<0.001kg), there might be a conversion error")
        else:
            logger.info("✅ All weight values appear to be in correct units (kg in database)")
        
        # Check package_information table if it exists
        try:
            c.execute('''
                SELECT id, weight, created_at 
                FROM package_information 
                WHERE weight IS NOT NULL 
                ORDER BY id DESC 
                LIMIT 5
            ''')
            
            pkg_entries = c.fetchall()
            
            if pkg_entries:
                logger.info("")
                logger.info("Recent entries from package_information:")
                logger.info("-" * 50)
                
                for entry_id, weight, created_at in pkg_entries:
                    weight_kg = float(weight)
                    weight_grams = weight_kg * 1000
                    
                    if weight_kg > 100:
                        status = "❌ SUSPICIOUS"
                        issues_found = True
                    elif weight_kg < 0.001:
                        status = "❌ SUSPICIOUS"
                        issues_found = True
                    else:
                        status = "✅ OK"
                        
                    logger.info(f"ID {entry_id}: {weight_kg:.6f} kg ({weight_grams:.1f} g) - {status}")
                    
        except sqlite3.OperationalError:
            logger.info("package_information table not found or no weight column")
        
        conn.close()
        return not issues_found
        
    except Exception as e:
        logger.error(f"Error checking weight units: {e}")
        return False

def fix_weight_units_interactive():
    """Interactive fix for weight units if issues are found"""
    logger.info("=" * 50)
    logger.info("WEIGHT UNIT FIX")
    logger.info("=" * 50)
    
    response = input("Do you want to fix weight units in the database? (y/n): ")
    if response.lower() != 'y':
        logger.info("Fix cancelled by user")
        return
    
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Check for entries that are likely in grams instead of kg
        c.execute('''
            SELECT id, weight 
            FROM loaded_sensor_data 
            WHERE weight > 100
        ''')
        
        large_weights = c.fetchall()
        
        if large_weights:
            logger.info(f"Found {len(large_weights)} entries with weight > 100kg (likely in grams)")
            
            for entry_id, weight in large_weights:
                new_weight = weight / 1000  # Convert grams to kg
                logger.info(f"Converting ID {entry_id}: {weight} → {new_weight} kg")
                
                c.execute('''
                    UPDATE loaded_sensor_data 
                    SET weight = ? 
                    WHERE id = ?
                ''', (new_weight, entry_id))
            
            conn.commit()
            logger.info("✅ Weight units fixed in loaded_sensor_data table")
        else:
            logger.info("No weight unit issues found in loaded_sensor_data table")
        
        # Fix package_information table if needed
        try:
            c.execute('''
                SELECT id, weight 
                FROM package_information 
                WHERE weight > 100
            ''')
            
            large_pkg_weights = c.fetchall()
            
            if large_pkg_weights:
                logger.info(f"Found {len(large_pkg_weights)} entries with weight > 100kg in package_information")
                
                for entry_id, weight in large_pkg_weights:
                    new_weight = weight / 1000  # Convert grams to kg
                    logger.info(f"Converting package ID {entry_id}: {weight} → {new_weight} kg")
                    
                    c.execute('''
                        UPDATE package_information 
                        SET weight = ? 
                        WHERE id = ?
                    ''', (new_weight, entry_id))
                
                conn.commit()
                logger.info("✅ Weight units fixed in package_information table")
            else:
                logger.info("No weight unit issues found in package_information table")
                
        except sqlite3.OperationalError:
            logger.info("package_information table not checked (doesn't exist or no weight column)")
        
        conn.close()
        logger.info("✅ Database weight unit fix completed")
        
    except Exception as e:
        logger.error(f"Error fixing weight units: {e}")

def main():
    """Main verification and fix routine"""
    logger.info("Weight Unit Verification Script")
    logger.info(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check current weight units
    is_correct = check_weight_units()
    
    if not is_correct:
        logger.warning("Issues found with weight units")
        fix_weight_units_interactive()
        
        # Re-check after fix
        logger.info("")
        logger.info("Re-checking after fix...")
        check_weight_units()
    else:
        logger.info("✅ All weight units appear correct")

if __name__ == "__main__":
    main()
