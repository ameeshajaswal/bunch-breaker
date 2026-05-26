# backend/src/api/main.py - FINAL VERSION WITH 2x EQUITY MULTIPLIER
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
from pathlib import Path
import re
import os

app = FastAPI(title="Bunch Breaker API", description="Transit Data Challenge 2026")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path("data/processed/hotspots.db")
EQUITY_PATH = Path("data/processed/income_quartiles.csv")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def normalize_intersection_name(name):
    if not name:
        return name
    name = name.upper()
    name = name.replace(' AT ', ' & ')
    name = name.replace(' AND ', ' & ')
    name = name.replace(' ST ', ' STREET ')
    name = name.replace(' AVE ', ' AVENUE ')
    name = name.replace(' RD ', ' ROAD ')
    name = ' '.join(name.split())
    return name

def load_equity_data():
    equity_dict = {}
    if EQUITY_PATH.exists():
        df = pd.read_csv(EQUITY_PATH)
        for _, row in df.iterrows():
            intersection = row['intersection']
            quartile = row['income_quartile']
            equity_factor = 0.5 + (quartile - 1) * 0.5
            equity_dict[normalize_intersection_name(intersection)] = equity_factor
            equity_dict[intersection] = equity_factor

    equity_dict["JANE ST AT FINCH AVE WEST NORTH SIDE"] = 2.0
    equity_dict["JANE ST AT FINCH AVE WEST SOUTH SIDE"] = 2.0
    equity_dict["JANE ST AT FINCH AVE WEST"] = 2.0
    equity_dict["JANE & FINCH"] = 2.0
    equity_dict["JANE ST AT FINCH AVE W"] = 2.0
    equity_dict["FINCH AVE W AT JANE ST"] = 2.0

    print(f"Loaded equity data for {len(equity_dict)} intersections")
    print(f"Jane-Finch factor: {equity_dict.get('JANE ST AT FINCH AVE WEST NORTH SIDE', 'NOT FOUND')}")
    return equity_dict

def get_equity_factor(intersection, equity_data):
    if not equity_data:
        return 1.0
    normalized = normalize_intersection_name(intersection)
    if normalized in equity_data:
        return equity_data[normalized]
    if 'JANE' in normalized and 'FINCH' in normalized:
        print(f"✓ Jane-Finch detected: {intersection} → 2.0x")
        return 2.0
    if 'LAWRENCE' in normalized and 'KEELE' in normalized:
        return 2.0
    if 'JANE & FINCH' in normalized:
        return 2.0
    if intersection in equity_data:
        return equity_data[intersection]
    for key in equity_data:
        if key in normalized or normalized in key:
            return equity_data[key]
    return 1.0

def greedy_coverage_solver(hotspots, n_supervisors, strategy='greedy', equity_data=None):
    if not hotspots:
        return []

    remaining = []
    for h in hotspots:
        equity_factor = get_equity_factor(h['intersection'], equity_data) if equity_data else 1.0
        remaining.append({
            'id': h['id'],
            'intersection': h['intersection'],
            'routes': h['routes'].copy() if isinstance(h['routes'], set) else set(h['routes']),
            'routes_list': h['routes_list'],
            'severity': h['severity'],
            'riders': h['riders'],
            'lat': h['lat'],
            'lng': h['lng'],
            'equity_factor': equity_factor
        })

    selected = []
    covered_routes = set()

    for _ in range(min(n_supervisors, len(remaining))):
        if not remaining:
            break

        for hotspot in remaining:
            uncovered_routes = hotspot['routes'] - covered_routes
            uncovered_count = len(uncovered_routes)
            if uncovered_count == 0:
                hotspot['score'] = -1
            elif strategy == 'weighted':
                hotspot['score'] = hotspot['severity'] * hotspot['riders'] * uncovered_count
            elif strategy == 'equity':
                hotspot['score'] = hotspot['severity'] * hotspot['riders'] * hotspot['equity_factor'] * uncovered_count
            else:
                hotspot['score'] = hotspot['severity'] * uncovered_count

        best = max(remaining, key=lambda x: x['score'])
        uncovered = best['routes'] - covered_routes
        uncovered_list = list(uncovered)

        base_reduction = best['severity'] * 70
        if strategy == 'equity':
            base_reduction = base_reduction * min(1.5, best['equity_factor'])

        reduction = int(base_reduction * (len(uncovered) / max(len(best['routes']), 1)))
        reduction = max(10, min(95, reduction))

        selected.append({
            'id': best['id'],
            'intersection': best['intersection'],
            'routes': best['routes_list'],
            'new_routes': uncovered_list,
            'severity': round(best['severity'], 3),
            'riders': best['riders'],
            'reduction': reduction,
            'lat': best['lat'],
            'lng': best['lng'],
            'equity_factor': round(best['equity_factor'], 2) if strategy == 'equity' else None
        })

        covered_routes.update(best['routes'])
        remaining = [h for h in remaining if h['id'] != best['id']]

    return selected

def get_hotspots_from_db(peak_only=True, hour=None, severity_min=0.5, limit=100):
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return []

    conn = get_db_connection()
    query = """
        SELECT 
            intersection,
            GROUP_CONCAT(DISTINCT route) as routes,
            AVG(severity) as avg_severity,
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
    query += " GROUP BY intersection"
    query += f" HAVING avg_severity >= {severity_min}"
    query += " ORDER BY avg_severity DESC"
    if limit > 0:
        query += f" LIMIT {limit}"

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return []

    hotspots = []
    for idx, row in df.iterrows():
        routes_list = row['routes'].split(',') if row['routes'] else []
        hotspots.append({
            'id': idx,
            'intersection': row['intersection'],
            'routes': set(routes_list),
            'routes_list': routes_list,
            'severity': float(row['avg_severity']),
            'riders': int(row['total_riders']),
            'route_count': int(row['route_count']),
            'lat': float(row['lat']) if pd.notna(row['lat']) else 43.6532,
            'lng': float(row['lng']) if pd.notna(row['lng']) else -79.3832
        })

    return hotspots

# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/api/debug/paths")
async def debug_paths():
    return {
        "cwd": os.getcwd(),
        "db_path_absolute": str(DB_PATH.absolute()),
        "db_exists": DB_PATH.exists(),
        "files_in_cwd": os.listdir(os.getcwd()),
    }

@app.get("/api/hotspots")
async def get_hotspots(
    peak_only: bool = Query(False, description="Filter to peak hours only"),
    hour: int = Query(None, description="Filter to specific hour (0-23)"),
    min_severity: float = Query(0.0, description="Minimum severity threshold")
):
    if not DB_PATH.exists():
        return {"hotspots": [], "count": 0, "error": "Database not found"}

    conn = get_db_connection()
    query = "SELECT * FROM hotspots WHERE 1=1"
    params = []
    if peak_only:
        query += " AND peak_hour = 1"
    if hour is not None:
        query += " AND hour = ?"
        params.append(hour)
    if min_severity > 0:
        query += " AND severity >= ?"
        params.append(min_severity)
    query += " LIMIT 1000"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    result = df.to_dict(orient='records')
    return {"hotspots": result, "count": len(result)}

@app.get("/api/optimize")
async def optimize(
    n_supervisors: int = Query(3, ge=1, le=10),
    strategy: str = Query("greedy", pattern="^(greedy|weighted|equity)$"),
    peak_only: bool = Query(True),
    min_severity: float = Query(0.6, description="Minimum severity threshold (0-1)"),
    limit_hotspots: int = Query(100, description="Limit to top N hotspots for realistic coverage")
):
    if not DB_PATH.exists():
        return {
            "recommendations": [],
            "coverage_percent": 0,
            "total_hotspots": 0,
            "strategy": strategy,
            "error": "Database not found"
        }

    equity_data = load_equity_data() if strategy == 'equity' else None
    hotspots = get_hotspots_from_db(peak_only=peak_only, severity_min=min_severity, limit=limit_hotspots)

    if not hotspots:
        return {
            "recommendations": [],
            "coverage_percent": 0,
            "total_hotspots": 0,
            "strategy": strategy,
            "message": "No hotspots found for the selected filters"
        }

    selected = greedy_coverage_solver(hotspots, n_supervisors, strategy, equity_data)
    total_count = len(hotspots)
    selected_count = len(selected)
    coverage = round((selected_count / total_count) * 100) if total_count > 0 else 0
    total_riders = sum(s.get('riders', 0) for s in selected)

    equity_score = None
    if strategy == 'equity' and selected:
        avg_equity = sum(s.get('equity_factor', 1) for s in selected) / len(selected)
        equity_score = round(avg_equity, 2)

    return {
        "recommendations": selected,
        "coverage_percent": coverage,
        "total_hotspots": total_count,
        "selected_count": selected_count,
        "total_riders_helped": total_riders,
        "strategy": strategy,
        "n_supervisors": n_supervisors,
        "equity_score": equity_score,
        "min_severity": min_severity
    }

@app.get("/api/strategies")
async def get_strategies():
    return {
        "strategies": [
            {
                "name": "greedy",
                "description": "Prioritizes intersections with highest bunching severity",
                "formula": "score = severity × uncovered_routes",
                "best_for": "Pure operational efficiency"
            },
            {
                "name": "weighted",
                "description": "Prioritizes intersections with highest ridership impact",
                "formula": "score = severity × riders × uncovered_routes",
                "best_for": "Maximizing rider benefit"
            },
            {
                "name": "equity",
                "description": "⚖️ Prioritizes low-income neighborhoods (2× multiplier for Jane-Finch)",
                "formula": "score = severity × riders × equity_factor × uncovered_routes",
                "best_for": "Social equity and fairness"
            }
        ]
    }

@app.get("/api/equity-data")
async def get_equity_data():
    equity_data = load_equity_data()
    return {
        "equity_factors": {k: v for k, v in list(equity_data.items())[:20]},
        "note": "Higher equity_factor = lower income area. Jane-Finch receives 2.0× multiplier.",
        "demo_hotspots": ["Jane & Finch (2.0x)", "Lawrence Heights (2.0x)"]
    }

@app.get("/api/debug/hotspots")
async def debug_hotspots(
    min_severity: float = Query(0.5, description="Minimum severity threshold"),
    limit: int = Query(50, description="Limit results")
):
    hotspots = get_hotspots_from_db(peak_only=True, severity_min=min_severity, limit=limit)
    return {
        "count": len(hotspots),
        "min_severity": min_severity,
        "limit": limit,
        "sample": [{"intersection": h['intersection'], "severity": h['severity'], "riders": h['riders']} for h in hotspots[:15]]
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "database_exists": DB_PATH.exists(),
        "equity_data_exists": EQUITY_PATH.exists(),
        "database_path": str(DB_PATH)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))