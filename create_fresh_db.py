# create_fresh_db.py - UPDATED WITH VISIBLE YELLOW HOTSPOTS
import sqlite3
from pathlib import Path

DB_PATH = Path("data/processed/hotspots.db")

def create_fresh_database():
    # Delete old database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Deleted old database")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE hotspots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intersection TEXT,
            route TEXT,
            headway_variance REAL,
            severity REAL,
            riders_affected INTEGER,
            peak_hour INTEGER,
            hour INTEGER,
            stop_lat REAL,
            stop_lon REAL
        )
    ''')
    
    # Add hotspots with different severity levels - ALL VISIBLE ON MAP
    hotspots = [
        # ============================================================
        # RED hotspots (Critical - severity >= 0.80)
        # Located in northwest Toronto (visible on map)
        # ============================================================
        ('Jane St & Finch Ave W', '35', 0.95, 5000, 43.7185, -79.5205),
        ('Keele St & Lawrence Ave W', '52', 0.92, 3800, 43.7118, -79.4745),
        ('Wilson Ave & Keele St', '165', 0.90, 3200, 43.7310, -79.4805),
        ('Sheppard Ave W & Jane St', '84', 0.88, 2900, 43.7390, -79.5130),
        
        # ============================================================
        # ORANGE hotspots (High - severity 0.65-0.79)
        # Located in midtown Toronto (visible on map)
        # ============================================================
        ('Bloor St W & Spadina Ave', '510', 0.75, 1850, 43.6675, -79.4028),
        ('King St W & Bathurst St', '504', 0.72, 2200, 43.6429, -79.4041),
        ('Queen St W & Roncesvalles Ave', '501', 0.68, 1600, 43.6485, -79.4462),
        ('Dundas St W & Ossington Ave', '505', 0.70, 1450, 43.6532, -79.4253),
        ('College St & Lansdowne Ave', '506', 0.66, 1700, 43.6538, -79.4435),
        ('Yonge St & Eglinton Ave', '97', 0.69, 2100, 43.7055, -79.3985),
        
        # ============================================================
        # YELLOW hotspots (Moderate - severity < 0.65)
        # Located in downtown Toronto (EASILY VISIBLE on map)
        # ============================================================
        ('Yonge St & Bloor St', '97', 0.58, 3200, 43.6700, -79.3860),
        ('Queen St W & University Ave', '501', 0.55, 2800, 43.6525, -79.3867),
        ('King St E & Parliament St', '504', 0.52, 2500, 43.6530, -79.3600),
        ('College St & Bay St', '506', 0.48, 2200, 43.6610, -79.3830),
        ('Spadina Ave & Dundas St W', '510', 0.45, 1900, 43.6520, -79.4000),
        ('Front St & Bay St', '509', 0.42, 1700, 43.6425, -79.3810),
    ]
    
    for intersection, route, severity, riders, lat, lng in hotspots:
        cursor.execute('''
            INSERT INTO hotspots (intersection, route, headway_variance, severity, riders_affected, peak_hour, hour, stop_lat, stop_lon)
            VALUES (?, ?, ?, ?, ?, 1, 17, ?, ?)
        ''', (intersection, route, 60.0, severity, riders, lat, lng))
    
    conn.commit()
    print(f"✅ Added {len(hotspots)} hotspots to fresh database")
    
    # Show summary by color
    cursor.execute("SELECT severity, COUNT(*) FROM hotspots GROUP BY severity ORDER BY severity DESC")
    red_count = 0
    orange_count = 0
    yellow_count = 0
    
    print("\n📊 Severity distribution:")
    for row in cursor.fetchall():
        if row[0] >= 0.8:
            color = "🔴 Red"
            red_count += row[1]
        elif row[0] >= 0.65:
            color = "🟠 Orange"
            orange_count += row[1]
        else:
            color = "🟡 Yellow"
            yellow_count += row[1]
        print(f"   {color}: severity {row[0]} ({row[1]} hotspot)")
    
    print(f"\n📈 Summary:")
    print(f"   🔴 Red hotspots: {red_count}")
    print(f"   🟠 Orange hotspots: {orange_count}")
    print(f"   🟡 Yellow hotspots: {yellow_count}")
    
    # Show yellow hotspot locations
    cursor.execute("SELECT intersection, stop_lat, stop_lon FROM hotspots WHERE severity < 0.65")
    print("\n📍 Yellow hotspot locations (downtown - easily visible):")
    for row in cursor.fetchall():
        print(f"   🟡 {row[0]} | Lat: {row[1]}, Lon: {row[2]}")
    
    conn.close()
    print("\n✅ Fresh database created successfully!")
    print("\n💡 Tip: Yellow hotspots are now in downtown Toronto at Yonge & Bloor, Queen & University, etc.")

if __name__ == "__main__":
    create_fresh_database()