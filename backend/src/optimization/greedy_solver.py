# backend/src/optimization/greedy_solver.py
"""
Greedy Coverage Solver for Supervisor Deployment
Implements the Maximum Weighted Set Cover approximation algorithm
Hochbaum (1982) - (1 - 1/e) ≈ 63% of optimal
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/processed/hotspots.db")

def get_hotspots_from_db(peak_only=True, hour=None):
    """Fetch hotspots from database with optional filters"""
    
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return []
    
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            intersection,
            GROUP_CONCAT(DISTINCT route) as routes,
            AVG(severity) as severity,
            SUM(riders_affected) as total_riders,
            AVG(stop_lat) as lat,
            AVG(stop_lon) as lng,
            COUNT(DISTINCT route) as route_count
        FROM hotspots
        WHERE 1=1
    """
    
    if peak_only:
        query += " AND peak_hour = 1"
    
    if hour is not None:
        query += f" AND hour = {hour}"
    
    query += " GROUP BY intersection ORDER BY severity DESC"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert to list of dictionaries
    hotspots = []
    for _, row in df.iterrows():
        routes_list = row['routes'].split(',') if row['routes'] else []
        
        hotspots.append({
            'id': len(hotspots),
            'intersection': row['intersection'],
            'routes': set(routes_list),  # Use set for easy coverage tracking
            'routes_list': routes_list,
            'severity': float(row['severity']),
            'riders': int(row['total_riders']),
            'route_count': int(row['route_count']),
            'lat': float(row['lat']) if pd.notna(row['lat']) else 43.6532,
            'lng': float(row['lng']) if pd.notna(row['lng']) else -79.3832,
            'covered': False
        })
    
    return hotspots

def greedy_coverage_solver(hotspots, n_supervisors, strategy='greedy'):
    """
    Greedy algorithm for maximum coverage problem.
    
    Algorithm:
    1. Score each intersection based on strategy
    2. Pick the highest-scoring intersection
    3. Mark all routes at that intersection as "covered"
    4. Remove covered routes from consideration
    5. Repeat until N supervisors placed or no hotspots left
    
    Args:
        hotspots: List of hotspot dictionaries
        n_supervisors: Number of supervisors to deploy (1-10)
        strategy: 'greedy' (max severity) or 'weighted' (severity * riders)
    
    Returns:
        List of selected supervisor locations with metrics
    """
    
    if not hotspots:
        return []
    
    # Make a copy so we don't modify original
    remaining = []
    for h in hotspots:
        remaining.append({
            'id': h['id'],
            'intersection': h['intersection'],
            'routes': h['routes'].copy(),
            'routes_list': h['routes_list'],
            'severity': h['severity'],
            'riders': h['riders'],
            'lat': h['lat'],
            'lng': h['lng']
        })
    
    selected = []
    covered_routes = set()
    
    for _ in range(min(n_supervisors, len(remaining))):
        if not remaining:
            break
        
        # Score each remaining hotspot
        for hotspot in remaining:
            # Count uncovered routes at this intersection
            uncovered_routes = hotspot['routes'] - covered_routes
            uncovered_count = len(uncovered_routes)
            
            if uncovered_count == 0:
                hotspot['score'] = -1  # Already covered
            elif strategy == 'weighted':
                # Weighted: severity * riders * uncovered_count
                hotspot['score'] = hotspot['severity'] * hotspot['riders'] * uncovered_count
            else:
                # Greedy: severity * uncovered_count
                hotspot['score'] = hotspot['severity'] * uncovered_count
        
        # Pick highest scoring hotspot
        best = max(remaining, key=lambda x: x['score'])
        
        # Calculate metrics for this selection
        uncovered = best['routes'] - covered_routes
        uncovered_list = list(uncovered)
        
        # Estimate reduction percentage based on severity and coverage
        reduction = int(best['severity'] * 70 * (len(uncovered) / max(len(best['routes']), 1)))
        reduction = min(95, max(10, reduction))  # Clamp between 10-95%
        
        selected.append({
            'id': best['id'],
            'intersection': best['intersection'],
            'routes': best['routes_list'],
            'new_routes': uncovered_list,
            'severity': round(best['severity'], 3),
            'riders': best['riders'],
            'reduction': reduction,
            'lat': best['lat'],
            'lng': best['lng']
        })
        
        # Mark these routes as covered
        covered_routes.update(best['routes'])
        
        # Remove selected from remaining
        remaining = [h for h in remaining if h['id'] != best['id']]
    
    return selected

def calculate_coverage_percentage(selected, total_hotspots):
    """Calculate what percentage of hotspots are addressed"""
    if not total_hotspots:
        return 0
    return round((len(selected) / len(total_hotspots)) * 100)

# ============================================================
# Demo / Test Function
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Greedy Coverage Solver - Test")
    print("=" * 60)
    
    # Load hotspots from database
    print("\n1. Loading hotspots from database...")
    hotspots = get_hotspots_from_db(peak_only=True)
    
    if not hotspots:
        print("   No hotspots found. Run create_hotspot_table.py first!")
        exit(1)
    
    print(f"   Loaded {len(hotspots)} hotspots")
    
    # Show top 5 hotspots
    print("\n2. Top 5 Hotspots by Severity:")
    for i, h in enumerate(hotspots[:5]):
        print(f"   {i+1}. {h['intersection'][:40]} | Severity: {h['severity']:.3f} | Routes: {len(h['routes'])} | Riders: {h['riders']:,}")
    
    # Test greedy algorithm
    print("\n3. Running Greedy Algorithm (n=3, strategy=greedy):")
    selected = greedy_coverage_solver(hotspots, n_supervisors=3, strategy='greedy')
    
    for i, s in enumerate(selected):
        print(f"\n   #{i+1}: {s['intersection']}")
        print(f"      Routes: {', '.join(s['routes'])}")
        print(f"      Severity: {s['severity']}")
        print(f"      Riders/hr: {s['riders']:,}")
        print(f"      Est. Reduction: {s['reduction']}%")
    
    # Test weighted strategy
    print("\n4. Running Weighted Algorithm (n=3, strategy=weighted):")
    selected_weighted = greedy_coverage_solver(hotspots, n_supervisors=3, strategy='weighted')
    
    for i, s in enumerate(selected_weighted):
        print(f"\n   #{i+1}: {s['intersection']}")
        print(f"      Routes: {', '.join(s['routes'])}")
        print(f"      Riders/hr: {s['riders']:,}")
    
    # Calculate coverage
    coverage = calculate_coverage_percentage(selected, hotspots)
    print(f"\n5. Coverage with 3 supervisors: {coverage}%")
    
    print("\n" + "=" * 60)
    print("✅ Greedy Solver Test Complete!")
    print("=" * 60)