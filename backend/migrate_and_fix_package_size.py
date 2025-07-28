import sqlite3

def migrate_and_fix_package_size(default_size="Medium"):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Check if package_size column exists
    c.execute("PRAGMA table_info(package_information)")
    columns = [col[1] for col in c.fetchall()]
    if 'package_size' not in columns:
        print("Adding package_size column to package_information table...")
        c.execute("ALTER TABLE package_information ADD COLUMN package_size TEXT")
        conn.commit()
    else:
        print("package_size column already exists.")
    # Set all NULL or empty package_size values to the default
    c.execute("""
        UPDATE package_information
        SET package_size = ?
        WHERE package_size IS NULL OR package_size = ''
    """, (default_size,))
    conn.commit()
    updated = c.rowcount
    conn.close()
    print(f"Updated {updated} package_information records with package_size='{default_size}'")

if __name__ == "__main__":
    migrate_and_fix_package_size()
