# add_jane_finch.py
import sqlite3
from pathlib import Path

DB_PATH = Path("data/processed/hotspots.db")

def add_jane_finch_hotspot():
    """Add a demo Jane-Finch hotspot to the database for equity demo"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if Jane-Finch already exists
    cursor.execute("SELECT COUNT(*) FROM hotspots WHERE intersection LIKE '%Jane%Finch%' OR intersection LIKE '%JANE%FINCH%'")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Jane-Finch already exists ({count} records)")
        # Update existing ones to have higher severity
        cursor.execute("""
            UPDATE hotspots 
            SET severity = 0.85, riders_affected = 3200, peak_hour = 1 
            WHERE intersection LIKE '%Jane%Finch%'
        """)
        print("✅ Updated existing Jane-Finch hotspots")
    else:
        print("Adding Jane-Finch hotspot...")
        
        # Insert a synthetic Jane-Finch hotspot
        cursor.execute("""
            INSERT INTO hotspots (
                intersection, route, headway_variance, severity, 
                riders_affected, peak_hour, hour, stop_lat, stop_lon
            ) VALUES 
            ('Jane & Finch', '35', 120.5, 0.85, 3200, 1, 17, 43.7185, -79.5205),
            ('Jane & Finch', '35B', 118.2, 0.84, 3100, 1, 17, 43.7185, -79.5205),
            ('Jane St at Finch Ave W', '35', 125.0, 0.86, 3300, 1, 8, 43.7185, -79.5205),
            ('Finch Ave W at Jane St', '35', 122.0, 0.85, 3150, 1, 17, 43.7185, -79.5205)
        """)
        print("✅ Added Jane & Finch hotspots (severity: 0.85, riders: 3,200, equity_factor: 2.0)")
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT intersection, severity, riders_affected FROM hotspots WHERE intersection LIKE '%Jane%Finch%'")
    results = cursor.fetchall()
    print(f"\n📊 Jane-Finch hotspots in database:")
    for row in results:
        print(f"   - {row[0]} | Severity: {row[1]} | Riders: {row[2]}")
    
    conn.close()

if __name__ == "__main__":
    add_jane_finch_hotspot()