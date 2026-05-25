// frontend/src/App.jsx - COMPLETE VERSION WITH EQUITY STRATEGY
import { useState, useEffect } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Fix Leaflet default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, shadowUrl: markerShadow });

const API_BASE = 'http://localhost:8000/api';

// Helper functions
function severityColor(severity) {
  if (severity >= 0.8) return '#FF4D1C';
  if (severity >= 0.65) return '#FF8C00';
  return '#FFB800';
}

function severityLabel(severity) {
  if (severity >= 0.8) return 'Critical';
  if (severity >= 0.65) return 'High';
  return 'Moderate';
}

// Get strategy display info
function getStrategyInfo(strategy) {
  switch(strategy) {
    case 'greedy':
      return { name: 'Greedy', icon: '🎯', color: '#4ade80', desc: 'Max severity first' };
    case 'weighted':
      return { name: 'Weighted', icon: '📊', color: '#60a5fa', desc: 'Severity × Riders' };
    case 'equity':
      return { name: 'Equity', icon: '⚖️', color: '#a78bfa', desc: 'Low-income priority' };
    default:
      return { name: 'Greedy', icon: '🎯', color: '#4ade80', desc: '' };
  }
}

// Function to get star icon based on severity
function getStarIcon(severity) {
  let starColor = severityColor(severity);
  return L.divIcon({
    html: `<div style="font-size:24px;line-height:1;filter:drop-shadow(0 0 4px rgba(0,0,0,0.5));color:${starColor};">★</div>`,
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12]
  });
}

// KPI Card Component
function KpiCard({ label, value, sub, accent, delay = 0 }) {
  return (
    <div style={{
      animationDelay: `${delay}ms`,
      background: '#0d0f18',
      border: '1px solid #1a1d2b',
      borderTop: `2px solid ${accent}`,
      borderRadius: 6,
      padding: '12px 18px',
      minWidth: 140,
      flex: '1 1 140px',
    }}>
      <div style={{ fontSize: 10, letterSpacing: '0.14em', color: '#3a4060', textTransform: 'uppercase', fontFamily: "'DM Mono', monospace", marginBottom: 7 }}>{label}</div>
      <div style={{ fontSize: 28, fontFamily: "'DM Mono', monospace", fontWeight: 500, color: accent, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#2e3450', marginTop: 5, fontFamily: "'DM Mono', monospace" }}>{sub}</div>}
    </div>
  );
}

// Supervisor Recommendation Card
function SupervisorCard({ rank, spot, strategy }) {
  if (!spot) return null;
  const strategyInfo = getStrategyInfo(strategy);
  
  return (
    <div style={{
      background: '#080a0f',
      border: '1px solid #1a1d2b',
      borderLeft: `3px solid ${severityColor(spot.severity || 0.5)}`,
      borderRadius: 6,
      padding: '13px 14px',
      marginBottom: 10,
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 11 }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: strategyInfo.color, color: '#080a0f',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: "'DM Mono', monospace", fontWeight: 500, fontSize: 13,
          flexShrink: 0,
        }}>{rank}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: 17, color: '#dde1f0', marginBottom: 6 }}>
            {spot.intersection || 'Unknown'}
          </div>
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
            {spot.routes && spot.routes.map((r, idx) => (
              <span key={`${spot.id}-route-${idx}`} style={{
                background: '#4a90a418', border: '1px solid #4a90a444',
                color: '#4a90a4', borderRadius: 3, padding: '2px 7px',
                fontSize: 11, fontFamily: "'DM Mono', monospace",
              }}>Rt {r}</span>
            ))}
            {spot.equity_factor && (
              <span style={{
                background: '#a78bfa18', border: '1px solid #a78bfa44',
                color: '#a78bfa', borderRadius: 3, padding: '2px 7px',
                fontSize: 11, fontFamily: "'DM Mono', monospace",
              }}>⚖️ {spot.equity_factor}x equity</span>
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 7 }}>
            <div style={{ background: '#0d0f18', borderRadius: 4, padding: '6px 8px' }}>
              <div style={{ fontSize: 9, color: '#2e3450', textTransform: 'uppercase' }}>Riders/hr</div>
              <div style={{ fontSize: 15, color: '#60a5fa', fontFamily: "'DM Mono', monospace" }}>{(spot.riders || 0).toLocaleString()}</div>
            </div>
            <div style={{ background: '#0d0f18', borderRadius: 4, padding: '6px 8px' }}>
              <div style={{ fontSize: 9, color: '#2e3450', textTransform: 'uppercase' }}>Reduction</div>
              <div style={{ fontSize: 15, color: '#4ade80', fontFamily: "'DM Mono', monospace" }}>−{spot.reduction || 0}%</div>
            </div>
            <div style={{ background: '#0d0f18', borderRadius: 4, padding: '6px 8px' }}>
              <div style={{ fontSize: 9, color: '#2e3450', textTransform: 'uppercase' }}>Severity</div>
              <div style={{ fontSize: 15, color: severityColor(spot.severity || 0.5), fontFamily: "'DM Mono', monospace" }}>{(spot.severity || 0).toFixed(2)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Map Component
function BunchMap({ hotspots, selected, strategy }) {
  const [MapComponents, setMapComponents] = useState(null);

  useEffect(() => {
    import('react-leaflet').then((module) => {
      setMapComponents({
        MapContainer: module.MapContainer,
        TileLayer: module.TileLayer,
        CircleMarker: module.CircleMarker,
        Marker: module.Marker,
        Popup: module.Popup,
        ZoomControl: module.ZoomControl,
      });
    }).catch(err => console.error('Failed to load react-leaflet:', err));
  }, []);

  if (!MapComponents) {
    return <div style={{ height: '100%', background: '#060810', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4a5068' }}>Loading map...</div>;
  }

  const { MapContainer, TileLayer, CircleMarker, Marker, Popup, ZoomControl } = MapComponents;
  
  const validHotspots = (hotspots || []).filter(spot => 
    spot && typeof spot.lat === 'number' && typeof spot.lng === 'number' && !isNaN(spot.lat) && !isNaN(spot.lng)
  );
  
  const validSelected = (selected || []).filter(spot => 
    spot && typeof spot.lat === 'number' && typeof spot.lng === 'number' && !isNaN(spot.lat) && !isNaN(spot.lng)
  );
  
  const selectedIds = new Set(validSelected.map(s => s.id));

  return (
    <MapContainer center={[43.685, -79.40]} zoom={12} style={{ height: '100%', width: '100%' }} zoomControl={false}>
      <ZoomControl position="bottomright" />
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; CARTO'
      />
      {validHotspots.map(spot => {
        const isSel = selectedIds.has(spot.id);
        const col = severityColor(spot.severity || 0.5);
        const radius = Math.max(8, (spot.severity || 0.5) * 22);
        return (
          <CircleMarker
            key={`hotspot-${spot.id}`}
            center={[spot.lat, spot.lng]}
            radius={radius}
            pathOptions={{
              color: col,
              fillColor: col,
              fillOpacity: isSel ? 0.2 : 0.06,
              weight: isSel ? 2 : 0.8,
              opacity: isSel ? 0.9 : 0.4,
            }}
          >
            <Popup>
              <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                <strong>{spot.intersection || 'Unknown'}</strong><br />
                Routes: {(spot.routes || []).join(', ')}<br />
                Severity: {spot.severity || 0}<br />
                Riders/hr: {(spot.riders || 0).toLocaleString()}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
      {validSelected.map((spot, i) => {
        const starIcon = getStarIcon(spot.severity || 0.5);
        return (
          <Marker 
            key={`supervisor-${spot.id}`} 
            position={[spot.lat, spot.lng]} 
            icon={starIcon}
          >
            <Popup>
              <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                <strong>★ Supervisor #{i + 1}</strong><br />
                {spot.intersection}<br />
                Severity: {spot.severity || 0} ({severityLabel(spot.severity || 0.5)})<br />
                Reduction: {spot.reduction || 0}%
                {spot.equity_factor && <><br />⚖️ Equity factor: {spot.equity_factor}x</>}
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}

// Main App Component
export default function App() {
  const [nSupervisors, setNSupervisors] = useState(3);
  const [strategy, setStrategy] = useState('greedy');
  const [timeFilter, setTimeFilter] = useState('peak');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [allHotspots, setAllHotspots] = useState([]);
  const [coverage, setCoverage] = useState(0);
  const [equityScore, setEquityScore] = useState(null);
  const [highContrast, setHighContrast] = useState(false);
  const [strategiesInfo, setStrategiesInfo] = useState([]);

  // Fetch strategies info on load
  useEffect(() => {
    fetch(`${API_BASE}/strategies`)
      .then(res => res.json())
      .then(data => setStrategiesInfo(data.strategies || []))
      .catch(err => console.error('Failed to load strategies:', err));
  }, []);

  // Fetch data from backend
  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      
      const peakOnly = timeFilter === 'peak';
      
      try {
        const optRes = await fetch(
          `${API_BASE}/optimize?n_supervisors=${nSupervisors}&strategy=${strategy}&peak_only=${peakOnly}`
        );
        if (!optRes.ok) throw new Error(`HTTP ${optRes.status}`);
        const optData = await optRes.json();
        setRecommendations(optData.recommendations || []);
        setCoverage(optData.coverage_percent || 0);
        setEquityScore(optData.equity_score || null);
        
        const hotspotsRes = await fetch(`${API_BASE}/hotspots?peak_only=${peakOnly}`);
        if (!hotspotsRes.ok) throw new Error(`HTTP ${hotspotsRes.status}`);
        const hotspotsData = await hotspotsRes.json();
        setAllHotspots(hotspotsData.hotspots || []);
        
      } catch (err) {
        console.error('API Error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [nSupervisors, strategy, timeFilter]);

  // Update URL
  useEffect(() => {
    const params = new URLSearchParams({ n: nSupervisors, strategy, time: timeFilter });
    window.history.replaceState({}, '', `?${params}`);
  }, [nSupervisors, strategy, timeFilter]);

  const totalRiders = recommendations.reduce((s, x) => s + (x?.riders || 0), 0);
  const avgReduction = recommendations.length
    ? Math.round(recommendations.reduce((s, x) => s + (x?.reduction || 0), 0) / recommendations.length)
    : 0;

  const strategyInfo = getStrategyInfo(strategy);
  const accent = highContrast ? '#FFE500' : '#F5A623';
  const bg = highContrast ? '#000000' : '#080a0f';
  const surf = highContrast ? '#111111' : '#0d0f18';
  const bord = highContrast ? '#ffffff' : '#1a1d2b';
  const txt = highContrast ? '#ffffff' : '#dde1f0';
  const mut = highContrast ? '#cccccc' : '#4a5068';

  function exportCSV() {
    const rows = [
      ['Rank', 'Intersection', 'Routes', 'Riders/hr', 'Reduction %', 'Severity', 'Severity Level', 'Strategy', 'Time', 'Equity Factor'],
      ...recommendations.map((s, i) => [
        i + 1, 
        s.intersection, 
        s.routes?.join(';'), 
        s.riders, 
        s.reduction, 
        s.severity, 
        severityLabel(s.severity), 
        strategy, 
        timeFilter,
        s.equity_factor || ''
      ]),
    ];
    const blob = new Blob([rows.map(r => r.join(',')).join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `bunch-breaker-${strategy}-n${nSupervisors}-${timeFilter}.csv`;
    a.click();
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: bg, color: txt, fontFamily: "'Barlow Condensed', sans-serif", overflow: 'hidden' }}>
      
      {/* Header */}
      <header style={{ background: surf, borderBottom: `1px solid ${bord}`, padding: '0 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 52, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, background: accent, borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17 }}>🚌</div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>Bunch Breaker</div>
            <div style={{ fontSize: 10, color: mut, letterSpacing: '0.12em', textTransform: 'uppercase' }}>TTC supervisor deployment optimizer</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setHighContrast(h => !h)} style={{ background: highContrast ? accent : '#0d0f18', color: highContrast ? '#000' : mut, border: `1px solid ${bord}`, borderRadius: 4, padding: '5px 12px', fontSize: 10, cursor: 'pointer' }}>
            {highContrast ? '◐ Contrast ON' : '◑ Contrast'}
          </button>
          <button onClick={exportCSV} style={{ background: '#0d0f18', color: mut, border: `1px solid ${bord}`, borderRadius: 4, padding: '5px 12px', fontSize: 10, cursor: 'pointer' }}>↓ CSV</button>
          <button onClick={() => window.print()} style={{ background: '#0d0f18', color: mut, border: `1px solid ${bord}`, borderRadius: 4, padding: '5px 12px', fontSize: 10, cursor: 'pointer' }}>↓ PDF</button>
        </div>
      </header>

      {/* Controls */}
      <div style={{ background: surf, borderBottom: `1px solid ${bord}`, padding: '11px 20px', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
          
          {/* Supervisor Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 250 }}>
            <span style={{ fontSize: 10, color: mut }}>Supervisors</span>
            <input type="range" min={1} max={10} value={nSupervisors} onChange={e => setNSupervisors(parseInt(e.target.value))} style={{ flex: 1 }} />
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 22, fontWeight: 500, color: accent }}>{nSupervisors}</span>
          </div>

          {/* Strategy Dropdown - NOW WITH EQUITY OPTION */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 260 }}>
            <span style={{ fontSize: 10, color: mut }}>Strategy</span>
            <select 
              value={strategy} 
              onChange={e => setStrategy(e.target.value)} 
              style={{ background: '#080a0f', color: txt, border: `1px solid ${bord}`, borderRadius: 4, padding: '6px 10px', fontSize: 12, width: '100%', cursor: 'pointer' }}
            >
              <option value="greedy">🎯 Greedy — Max severity first</option>
              <option value="weighted">📊 Weighted — Severity × Riders</option>
              <option value="equity">⚖️ Equity — Low-income priority (Jane-Finch, etc.)</option>
            </select>
          </div>

          {/* Time Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 230 }}>
            <span style={{ fontSize: 10, color: mut }}>Time</span>
            <select value={timeFilter} onChange={e => setTimeFilter(e.target.value)} style={{ background: '#080a0f', color: txt, border: `1px solid ${bord}`, borderRadius: 4, padding: '6px 10px', fontSize: 12, width: '100%' }}>
              <option value="peak">🌅 Peak hours (6–9am, 3–7pm)</option>
              <option value="offpeak">🌙 Off-peak</option>
              <option value="all">📅 All day</option>
            </select>
          </div>
        </div>
      </div>

      {/* KPI Strip */}
      <div style={{ display: 'flex', gap: 10, padding: '10px 20px', background: bg, borderBottom: `1px solid ${bord}`, flexShrink: 0, overflowX: 'auto' }}>
        <KpiCard label="Supervisors" value={nSupervisors} sub="of 10 available" accent={accent} delay={0} />
        <KpiCard label="Strategy" value={strategyInfo.name} sub={strategyInfo.desc} accent={strategyInfo.color} delay={60} />
        <KpiCard label="Coverage" value={`${coverage}%`} sub={`${recommendations.length} hotspots selected`} accent="#4ade80" delay={120} />
        <KpiCard label="Riders / hr" value={totalRiders.toLocaleString()} sub="estimated benefit" accent="#60a5fa" delay={180} />
        <KpiCard label="Avg reduction" value={`${avgReduction}%`} sub="bunching incidents" accent="#f472b6" delay={240} />
        {equityScore && (
          <KpiCard label="Equity Score" value={`${equityScore}x`} sub="low-income priority" accent="#a78bfa" delay={300} />
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div style={{ background: '#ff444410', border: '1px solid #ff4444', margin: '10px 20px', padding: '10px', borderRadius: 4, color: '#ff8888', fontSize: 12 }}>
          ⚠️ Error: {error}. Make sure backend is running on port 8000.
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: mut }}>
          Loading data from backend...
        </div>
      )}

      {/* Main Body */}
      {!loading && !error && (
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '370px 1fr', minHeight: 0, overflow: 'hidden' }}>
          
          {/* Left Panel - Recommendations */}
          <div style={{ background: surf, borderRight: `1px solid ${bord}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '14px 14px 0', overflowY: 'auto', flex: 1 }}>
              <div style={{ fontSize: 10, letterSpacing: '0.12em', color: mut, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{strategyInfo.icon}</span>
                <span>RANKED SUPERVISOR POSITIONS — {strategyInfo.name.toUpperCase()} STRATEGY</span>
              </div>
              {recommendations.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: mut }}>No hotspots found. Check database.</div>
              ) : (
                recommendations.map((spot, i) => (
                  <SupervisorCard key={`rec-${spot.id || i}`} rank={i + 1} spot={spot} strategy={strategy} />
                ))
              )}
            </div>
          </div>

          {/* Right Panel - Map */}
          <div style={{ position: 'relative', background: '#060810', overflow: 'hidden' }}>
            <BunchMap hotspots={allHotspots} selected={recommendations} strategy={strategy} />
            
            {/* Legend */}
            <div style={{ position: 'absolute', bottom: 20, left: 14, zIndex: 1000, background: 'rgba(6,8,16,0.93)', border: `1px solid ${bord}`, borderRadius: 6, padding: '10px 14px', backdropFilter: 'blur(8px)' }}>
              <div style={{ fontSize: 10, letterSpacing: '0.12em', color: mut, marginBottom: 8, fontWeight: 600 }}>LEGEND</div>
              
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 9, color: '#2e3450', marginBottom: 4 }}>BUNCHING HOTSPOTS</div>
                {[
                  ['#FF4D1C', 'Critical (≥0.80)'],
                  ['#FF8C00', 'High (0.65-0.79)'],
                  ['#FFB800', 'Moderate (<0.65)']
                ].map(([color, label]) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: color, opacity: 0.8 }} />
                    <span style={{ fontSize: 10, color: '#3a4060' }}>{label}</span>
                  </div>
                ))}
              </div>
              
              <div style={{ borderTop: `1px solid ${bord}`, marginTop: 6, paddingTop: 6 }}>
                <div style={{ fontSize: 9, color: '#2e3450', marginBottom: 4 }}>SUPERVISOR POSITIONS</div>
                {[
                  ['#FF4D1C', 'Sent to Critical hotspot'],
                  ['#FF8C00', 'Sent to High hotspot'],
                  ['#FFB800', 'Sent to Moderate hotspot']
                ].map(([color, label]) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 18, color: color }}>★</span>
                    <span style={{ fontSize: 10, color: '#3a4060' }}>{label}</span>
                  </div>
                ))}
              </div>
              
              {strategy === 'equity' && (
                <div style={{ borderTop: `1px solid ${bord}`, marginTop: 6, paddingTop: 6 }}>
                  <div style={{ fontSize: 9, color: '#a78bfa', marginBottom: 4 }}>⚖️ EQUITY STRATEGY ACTIVE</div>
                  <div style={{ fontSize: 9, color: '#3a4060' }}>Prioritizing Jane-Finch, Lawrence Heights, and other low-income neighborhoods</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}