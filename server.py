"""
Geo-Deferred Notification Server — Hackathon Edition
FastAPI · SQLite · WebSocket · Priority Queues · Geo Signal Simulation
Features: Priority queue · WebSocket broadcast · Trip simulation · Coverage zones · Retry engine · Analytics · JWT auth
"""

import asyncio, json, logging, math, random, sqlite3, time, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import uvicorn

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from fastapi.responses import FileResponse

log = logging.getLogger("geo_notif")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

# ── Enums & Constants ─────────────────────────────────────────────────────────
class Priority(str, Enum):
    URGENT="URGENT"; HIGH="HIGH"; NORMAL="NORMAL"; LOW="LOW"

class SignalQuality(str, Enum):
    GREEN="GREEN"; YELLOW="YELLOW"; RED="RED"

class NotifStatus(str, Enum):
    QUEUED="QUEUED"; DEFERRED="DEFERRED"; DELIVERED="DELIVERED"; FAILED="FAILED"; RETRYING="RETRYING"

PRIORITY_SIGNAL_MAP = {
    Priority.URGENT: [SignalQuality.GREEN, SignalQuality.YELLOW, SignalQuality.RED],
    Priority.HIGH:   [SignalQuality.GREEN, SignalQuality.YELLOW],
    Priority.NORMAL: [SignalQuality.GREEN],
    Priority.LOW:    [SignalQuality.GREEN],
}
MAX_RETRIES, RETRY_BASE_DELAY, DELIVERY_SIM_FAIL_RATE = 5, 2.0, 0.08
DB_PATH, DEMO_API_KEY = Path("geo_notifications.db"), "Team201A"

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    c = get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY, recipient TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'NORMAL', status TEXT NOT NULL DEFAULT 'QUEUED',
        created_at REAL NOT NULL, deferred_at REAL, delivered_at REAL,
        retry_count INTEGER NOT NULL DEFAULT 0, next_retry_at REAL, zone_at_deliver TEXT, metadata TEXT);
    CREATE TABLE IF NOT EXISTS coverage_zones (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, lat_center REAL NOT NULL, lon_center REAL NOT NULL,
        radius_km REAL NOT NULL, quality TEXT NOT NULL, description TEXT);
    CREATE TABLE IF NOT EXISTS trip_events (
        id TEXT PRIMARY KEY, trip_id TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
        signal TEXT NOT NULL, timestamp REAL NOT NULL, speed_kmh REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS delivery_log (
        id TEXT PRIMARY KEY, notification_id TEXT NOT NULL, attempt INTEGER NOT NULL,
        outcome TEXT NOT NULL, signal TEXT, lat REAL, lon REAL, timestamp REAL NOT NULL, error_msg TEXT);
    CREATE INDEX IF NOT EXISTS idx_notif_status   ON notifications(status);
    CREATE INDEX IF NOT EXISTS idx_notif_priority ON notifications(priority);
    CREATE INDEX IF NOT EXISTS idx_trip_id        ON trip_events(trip_id);
    CREATE INDEX IF NOT EXISTS idx_log_notif      ON delivery_log(notification_id);
    """)
    c.commit()
    if not c.execute("SELECT COUNT(*) FROM coverage_zones").fetchone()[0]:
        c.executemany("INSERT OR IGNORE INTO coverage_zones VALUES (?,?,?,?,?,?,?)", [
            ("zone-001","Bengaluru City Core",       12.9716, 77.5946, 15.0,"GREEN","Dense urban, excellent coverage"),
            ("zone-002","Hosur Industrial Corridor",  12.7409, 77.8253, 10.0,"GREEN","Industrial park, strong towers"),
            ("zone-003","Krishnagiri Ghat Section",   12.5174, 78.2139,  8.0,"YELLOW","Hilly terrain, intermittent signal"),
            ("zone-004","Dharmapuri Forest Reserve",  12.1211, 78.1580, 12.0,"RED","Forest reserve, near-zero coverage"),
            ("zone-005","Salem City",                 11.6643, 78.1460, 12.0,"GREEN","Major city, well-covered"),
            ("zone-006","Attur Countryside",          11.5986, 78.5960,  9.0,"YELLOW","Rural, patchy towers"),
            ("zone-007","Villupuram Town",            11.9401, 79.4861,  8.0,"GREEN","Highway junction, good signal"),
            ("zone-008","Tindivanam Highway Stretch", 12.2378, 79.6521,  7.0,"YELLOW","Highway, signal drops in valleys"),
            ("zone-009","Maraimalai Nagar Suburb",    12.7891, 80.0232,  6.0,"GREEN","Chennai suburb, strong LTE"),
            ("zone-010","Chennai City Centre",        13.0827, 80.2707, 20.0,"GREEN","Metro area, 5G available"),
        ]); c.commit(); log.info("Seeded 10 demo coverage zones")
    c.close(); log.info("DB initialised at %s", DB_PATH)

# ── Schemas ───────────────────────────────────────────────────────────────────
class NotificationCreate(BaseModel):
    recipient: str; title: str = Field(..., max_length=120); body: str = Field(..., max_length=1024)
    priority: Optional[Priority] = None; metadata: Optional[Dict[str, Any]] = None
@field_validator("title", "body")
def no_empty(cls, v):
    if not v or not v.strip():
        raise ValueError("Field cannot be empty")
        return v
    if not v.strip(): 
        raise ValueError("must not be blank")
        return v.strip()

class NotificationResponse(BaseModel):
    id: str; recipient: str; title: str; body: str; priority: Priority; status: NotifStatus
    created_at: float; deferred_at: Optional[float]; delivered_at: Optional[float]
    retry_count: int; zone_at_deliver: Optional[str]; metadata: Optional[Dict[str, Any]]

class CoverageZoneCreate(BaseModel):
    name: str; lat_center: float = Field(..., ge=-90, le=90); lon_center: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(..., gt=0, le=500); quality: SignalQuality; description: Optional[str] = None

class TripSimRequest(BaseModel):
    trip_id: str = Field(default_factory=lambda: f"trip-{uuid.uuid4().hex[:8]}")
    start_lat: float=12.9716; start_lon: float=77.5946; end_lat: float=13.0827; end_lon: float=80.2707
    waypoints: int = Field(default=20, ge=5, le=100); speed_kmh: float = Field(default=80.0, ge=10, le=200)
    flush_on_green: bool = True

class LocationUpdate(BaseModel):
    trip_id: str; lat: float; lon: float; speed_kmh: float = 60.0

class AnalyticsResponse(BaseModel):
    total_notifications: int; delivered: int; deferred: int; failed: int; queued: int; retrying: int
    delivery_rate_pct: float; avg_defer_duration_s: Optional[float]
    priority_breakdown: Dict[str,int]; zone_delivery_counts: Dict[str,int]; recent_activity: List[Dict]

# ── WebSocket Manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self): self._clients: List[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept(); self._clients.append(ws)
        log.info("WS connected (total=%d)", len(self._clients))
    def disconnect(self, ws: WebSocket):
        self._clients.remove(ws); log.info("WS disconnected (total=%d)", len(self._clients))
    async def broadcast(self, event: str, data: Dict):
        payload = json.dumps({"event": event, "data": data, "ts": time.time()})
        dead = []
        for ws in self._clients:
            try: await ws.send_text(payload)
            except: dead.append(ws)
        for ws in dead: self._clients.remove(ws)

ws_manager = ConnectionManager()
current_position: Dict = {"lat": 12.9716, "lon": 77.5946, "signal": SignalQuality.GREEN}

# ── Core Delivery Logic ───────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R, φ1, φ2 = 6371.0, math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(math.radians(lon2-lon1)/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def get_signal_at(lat, lon, conn) -> SignalQuality:
    rank = {SignalQuality.GREEN:3, SignalQuality.YELLOW:2, SignalQuality.RED:1}
    best = None
    for z in conn.execute("SELECT lat_center,lon_center,radius_km,quality FROM coverage_zones").fetchall():
        if haversine_km(lat, lon, z["lat_center"], z["lon_center"]) <= z["radius_km"]:
            q = SignalQuality(z["quality"])
            if best is None or rank[q] > rank[best]: best = q
    return best or SignalQuality.RED

def _sim_outcome(signal) -> bool:
    if signal == SignalQuality.RED: return False
    if signal == SignalQuality.YELLOW: return random.random() > DELIVERY_SIM_FAIL_RATE
    return True

async def attempt_delivery(notif_id, lat, lon, signal, conn) -> bool:
    row = conn.execute("SELECT * FROM notifications WHERE id=?", (notif_id,)).fetchone()
    if not row: return False
    priority, attempt = Priority(row["priority"]), row["retry_count"] + 1

    if signal not in PRIORITY_SIGNAL_MAP[priority]:
        if row["status"] != NotifStatus.DEFERRED:
            conn.execute("UPDATE notifications SET status=?,deferred_at=? WHERE id=?",
                         (NotifStatus.DEFERRED, time.time(), notif_id)); conn.commit()
            await ws_manager.broadcast("notification_deferred", {"id":notif_id,"priority":priority,"signal":signal,"lat":lat,"lon":lon})
        return False

    success = _sim_outcome(signal)
    conn.execute("INSERT INTO delivery_log VALUES (?,?,?,?,?,?,?,?,?)",
                 (str(uuid.uuid4()), notif_id, attempt, "SUCCESS" if success else "FAIL",
                  signal, lat, lon, time.time(), None if success else "Simulated network error"))
    if success:
        conn.execute("UPDATE notifications SET status=?,delivered_at=?,zone_at_deliver=? WHERE id=?",
                     (NotifStatus.DELIVERED, time.time(), signal, notif_id)); conn.commit()
        log.info("DELIVERED %s [%s] signal=%s attempt=%d", notif_id, priority, signal, attempt)
        await ws_manager.broadcast("notification_delivered",
            {"id":notif_id,"title":row["title"],"priority":priority,"signal":signal,"attempt":attempt,"lat":lat,"lon":lon})
        return True

    if attempt < MAX_RETRIES:
        delay = RETRY_BASE_DELAY * (2 ** (attempt-1))
        conn.execute("UPDATE notifications SET status=?,retry_count=?,next_retry_at=? WHERE id=?",
                     (NotifStatus.RETRYING, attempt, time.time()+delay, notif_id)); conn.commit()
        await ws_manager.broadcast("notification_retrying", {"id":notif_id,"attempt":attempt,"delay_s":delay})
    else:
        conn.execute("UPDATE notifications SET status=?,retry_count=? WHERE id=?",
                     (NotifStatus.FAILED, attempt, notif_id)); conn.commit()
        log.error("FAILED %s max retries exhausted", notif_id)
        await ws_manager.broadcast("notification_failed", {"id":notif_id,"title":row["title"],"priority":priority})
    return False

async def flush_queue(lat, lon, signal):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id,priority FROM notifications
            WHERE status IN ('QUEUED','DEFERRED','RETRYING') AND (next_retry_at IS NULL OR next_retry_at<=?)
            ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END, created_at ASC
        """, (time.time(),)).fetchall()
        for row in rows: await attempt_delivery(row["id"], lat, lon, signal, conn)
    finally: conn.close()

# ── Auth ──────────────────────────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)
def verify_token(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds or creds.credentials != DEMO_API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing Bearer token. Use: 'hackathon-demo-key-2025'")
    return creds.credentials

# ── AI Priority Assignment ────────────────────────────────────────────────────
def ai_assign_priority(title: str, body: str) -> Priority:
    """
    Assigns notification priority using keyword/heuristic rules that mirror
    what an LLM would reason about urgency — no external API required.
    Rules are applied in descending priority order; first match wins.
    """
    text = (title + " " + body).lower()

    urgent_keywords = [
        "emergency", "sos", "critical", "collision", "crash", "fire",
        "brake failure", "engine failure", "airbag", "accident", "mayday",
        "immediate", "evacuate", "911",
    ]
    high_keywords = [
        "low fuel", "fuel warning", "overheat", "overheating", "tire pressure",
        "tyre pressure", "oil pressure", "battery low", "speed limit",
        "road closed", "detour", "alert", "warning", "urgent",
    ]
    low_keywords = [
        "promo", "offer", "discount", "newsletter", "update available",
        "tip", "reminder", "scheduled", "routine", "weekly", "monthly",
    ]

    if any(kw in text for kw in urgent_keywords):
        assigned = Priority.URGENT
    elif any(kw in text for kw in high_keywords):
        assigned = Priority.HIGH
    elif any(kw in text for kw in low_keywords):
        assigned = Priority.LOW
    else:
        assigned = Priority.NORMAL

    log.info("AI priority assignment: title=%r → %s", title, assigned.value)
    return assigned

# ── Background Tasks ──────────────────────────────────────────────────────────
async def retry_worker():
    while True:
        await asyncio.sleep(5)
        try:
            lat, lon = current_position["lat"], current_position["lon"]
            conn = get_db(); signal = get_signal_at(lat, lon, conn); conn.close()
            current_position["signal"] = signal
            await flush_queue(lat, lon, signal)
        except Exception as e: log.exception("retry_worker: %s", e)

# ── App & Lifecycle ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(); task = asyncio.create_task(retry_worker())
    log.info("🚀 Geo-Deferred Notification Server started"); yield
    task.cancel(); log.info("Server shut down")

app = FastAPI(
    title="Geo-Deferred Notification Server",
    description="Queues non-urgent notifications and releases them when device enters high-coverage zone.",
    version="1.0.0", lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def row_to_notif(row) -> NotificationResponse:
    return NotificationResponse(**{k: row[k] for k in ("id","recipient","title","body","priority","status",
        "created_at","deferred_at","delivered_at","retry_count","zone_at_deliver")},
        priority=Priority(row["priority"]), status=NotifStatus(row["status"]),
        metadata=json.loads(row["metadata"]) if row["metadata"] else None)

# ── Routes: Notifications ─────────────────────────────────────────────────────
@app.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=201,
    tags=["Notifications"],
    summary="Queue a notification",
    description="Creates a notification. If signal is weak, it is queued and delivered when the device enters a high-coverage zone.",
    responses={
        201: {"description": "Notification created"},
        400: {"description": "Invalid input"},
        401: {"description": "Unauthorized"},
        500: {"description": "Server error"}
    }
)
async def create_notification(
    payload: NotificationCreate,
    background: BackgroundTasks,
    _t: str = Depends(verify_token)
):
    try:
        conn = get_db()
        nid = str(uuid.uuid4())
        now = time.time()

        # AI assigns priority if caller did not specify one
        assigned_priority = payload.priority if payload.priority is not None else ai_assign_priority(payload.title, payload.body)

        conn.execute(
            "INSERT INTO notifications VALUES (?,?,?,?,?,?,?,NULL,NULL,0,NULL,NULL,?)",
            (
                nid,
                payload.recipient,
                payload.title,
                payload.body,
                assigned_priority.value,
                NotifStatus.QUEUED.value,
                now,
                json.dumps(payload.metadata) if payload.metadata else None
            )
        )
        conn.commit()

        # ✅ Fix WebSocket payload
        await ws_manager.broadcast(
            "notification_created",
            {
                "id": nid,
                "priority": assigned_priority.value,
                "title": payload.title,
                "ai_assigned": payload.priority is None,
            }
        )

        lat, lon = current_position["lat"], current_position["lon"]
        signal = get_signal_at(lat, lon, conn)

        # ✅ FIX: do NOT pass DB connection
        background.add_task(attempt_delivery, nid, lat, lon, signal)

        return NotificationResponse(
            id=nid,
            recipient=payload.recipient,
            title=payload.title,
            body=payload.body,
            priority=assigned_priority,
            status=NotifStatus.QUEUED,
            created_at=now,
            deferred_at=None,
            delivered_at=None,
            retry_count=0,
            zone_at_deliver=None,
            metadata=payload.metadata
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()
@app.post("/zones", status_code=201, tags=["Coverage"], summary="Create a coverage zone")
def create_zone(payload: CoverageZoneCreate, _t: str=Depends(verify_token)):
    zid = str(uuid.uuid4()); conn = get_db()
    conn.execute("INSERT INTO coverage_zones VALUES (?,?,?,?,?,?,?)",
                 (zid, payload.name, payload.lat_center, payload.lon_center,
                  payload.radius_km, payload.quality.value, payload.description))
    conn.commit(); conn.close(); return {"id": zid, **payload.dict()}

@app.get("/zones/query", tags=["Coverage"], summary="Get signal quality at a lat/lon")
def query_signal(lat: float, lon: float, _t: str=Depends(verify_token)):
    conn = get_db(); sig = get_signal_at(lat, lon, conn); conn.close()
    return {"lat": lat, "lon": lon, "signal": sig}

# ── Routes: Location & Trip Simulation ───────────────────────────────────────
@app.post("/location", tags=["Trip"], summary="Update device location (triggers queue flush)")
async def update_location(payload: LocationUpdate, _t: str=Depends(verify_token)):
    global current_position
    conn = get_db(); signal = get_signal_at(payload.lat, payload.lon, conn)
    prev_signal = current_position.get("signal")
    current_position = {"lat": payload.lat, "lon": payload.lon, "signal": signal}
    conn.execute("INSERT INTO trip_events VALUES (?,?,?,?,?,?,?)",
                 (str(uuid.uuid4()), payload.trip_id, payload.lat, payload.lon, signal.value, time.time(), payload.speed_kmh))
    conn.commit(); conn.close()
    await ws_manager.broadcast("position_update",
        {"trip_id":payload.trip_id,"lat":payload.lat,"lon":payload.lon,"signal":signal,"speed_kmh":payload.speed_kmh})
    if signal != prev_signal:
        log.info("Signal: %s → %s at (%.4f, %.4f)", prev_signal, signal, payload.lat, payload.lon)
        await ws_manager.broadcast("signal_transition", {"from":prev_signal,"to":signal,"lat":payload.lat,"lon":payload.lon})
    await flush_queue(payload.lat, payload.lon, signal)
    return {"signal": signal, "lat": payload.lat, "lon": payload.lon}

@app.post("/trip/simulate", tags=["Trip"], summary="Simulate a full drive from A→B and watch notifications flush")
async def simulate_trip(payload: TripSimRequest, _t: str=Depends(verify_token)):
    global current_position
    conn, n, log_entries = get_db(), payload.waypoints, []
    for i in range(n+1):
        t = i / n
        lat = payload.start_lat + t*(payload.end_lat-payload.start_lat) + random.uniform(-0.008, 0.008)
        lon = payload.start_lon + t*(payload.end_lon-payload.start_lon) + random.uniform(-0.008, 0.008)
        signal = get_signal_at(lat, lon, conn); current_position = {"lat":lat,"lon":lon,"signal":signal}
        before = conn.execute("SELECT COUNT(*) FROM notifications WHERE status IN ('QUEUED','DEFERRED','RETRYING')").fetchone()[0]
        await flush_queue(lat, lon, signal)
        after  = conn.execute("SELECT COUNT(*) FROM notifications WHERE status IN ('QUEUED','DEFERRED','RETRYING')").fetchone()[0]
        entry = {"step":i,"lat":round(lat,5),"lon":round(lon,5),"signal":signal,
                 "pending_before":before,"pending_after":after,"delivered_here":before-after}
        log_entries.append(entry)
        await ws_manager.broadcast("trip_step", entry); await asyncio.sleep(0.05)
    conn.close()
    return {"trip_id":payload.trip_id,"waypoints":len(log_entries),"trip_log":log_entries,"summary":{
        "total_steps":len(log_entries),
        "green_steps":sum(1 for e in log_entries if e["signal"]=="GREEN"),
        "yellow_steps":sum(1 for e in log_entries if e["signal"]=="YELLOW"),
        "red_steps":sum(1 for e in log_entries if e["signal"]=="RED"),
        "total_deliveries":sum(e["delivered_here"] for e in log_entries),
    }}

# ── Routes: Analytics ─────────────────────────────────────────────────────────
@app.get("/analytics", response_model=AnalyticsResponse, tags=["Analytics"],
         summary="Delivery analytics — rates, deferral durations, zone breakdowns")
def get_analytics(_t: str=Depends(verify_token)):
    conn = get_db()
    total     = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    by_status = {r["status"]:r["cnt"] for r in conn.execute("SELECT status,COUNT(*) cnt FROM notifications GROUP BY status").fetchall()}
    by_prio   = {r["priority"]:r["cnt"] for r in conn.execute("SELECT priority,COUNT(*) cnt FROM notifications GROUP BY priority").fetchall()}
    by_zone   = {r["zone_at_deliver"]:r["cnt"] for r in conn.execute(
        "SELECT zone_at_deliver,COUNT(*) cnt FROM notifications WHERE zone_at_deliver IS NOT NULL GROUP BY zone_at_deliver").fetchall()}
    avg_defer = conn.execute("SELECT AVG(delivered_at-deferred_at) FROM notifications WHERE deferred_at IS NOT NULL AND delivered_at IS NOT NULL").fetchone()[0]
    recent    = [dict(r) for r in conn.execute(
        "SELECT id,title,priority,status,created_at,delivered_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()]
    delivered = by_status.get("DELIVERED", 0); conn.close()
    return AnalyticsResponse(total_notifications=total, delivered=delivered, deferred=by_status.get("DEFERRED",0),
        failed=by_status.get("FAILED",0), queued=by_status.get("QUEUED",0), retrying=by_status.get("RETRYING",0),
        delivery_rate_pct=round(delivered/total*100,2) if total else 0.0,
        avg_defer_duration_s=round(avg_defer,2) if avg_defer else None,
        priority_breakdown=by_prio, zone_delivery_counts=by_zone, recent_activity=recent)

@app.get("/analytics/delivery-prediction", tags=["Analytics"], summary="Predict delivery time for deferred notifications based on analytics")
def delivery_prediction(_t: str=Depends(verify_token)):
    conn = get_db()
    avg_defer = conn.execute(
        "SELECT AVG(delivered_at - deferred_at) FROM notifications WHERE deferred_at IS NOT NULL AND delivered_at IS NOT NULL"
    ).fetchone()[0]
    pending_count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE status IN ('QUEUED','DEFERRED','RETRYING')"
    ).fetchone()[0]
    conn.close()
    lat, lon = current_position["lat"], current_position["lon"]
    signal = current_position.get("signal", SignalQuality.RED)
    signal_val = {"GREEN": 100, "YELLOW": 55, "RED": 10}.get(str(signal).split(".")[-1], 10)
    # Base estimate from analytics history; fall back to heuristic if no data yet
    if avg_defer and avg_defer > 0:
        base_s = avg_defer
    else:
        # Heuristic: poor signal → longer wait
        base_s = 240 if signal_val < 30 else 90 if signal_val < 65 else 20
    # Scale by how bad signal is right now
    scale = 1.0 if signal_val >= 65 else (1.5 if signal_val >= 30 else 3.0)
    estimated_s = round(base_s * scale)
    return {
        "estimated_delivery_s": estimated_s,
        "avg_defer_duration_s": round(avg_defer, 2) if avg_defer else None,
        "current_signal": str(signal).split(".")[-1],
        "signal_strength_pct": signal_val,
        "pending_count": pending_count,
        "will_deliver_immediately": signal_val >= 65,
    }

@app.get("/analytics/vehicle-components", tags=["Analytics"], summary="Vehicle component message dataset")
def vehicle_components(_t: str=Depends(verify_token)):
    """Returns the autonomous vehicle component dataset used for simulation."""
    return {
        "components": [
            {
                "id": "ecu",
                "name": "ECU",
                "full_name": "Engine Control Unit",
                "icon": "⚙️",
                "color": "#00e5ff",
                "messages": [
                    {"title": "Engine RPM spike detected", "body": "RPM exceeded 6800 — possible throttle sensor fault"},
                    {"title": "Throttle response anomaly", "body": "Electronic throttle actuator response 340ms above baseline"},
                    {"title": "Misfire detected — Cylinder 3", "body": "Combustion misfire on cylinder 3, reducing power output"},
                    {"title": "Engine temp critical", "body": "Coolant temperature at 118°C — thermal shutdown imminent"},
                    {"title": "ECU self-test complete", "body": "All ECU modules nominal, firmware v4.2.1"},
                ]
            },
            {
                "id": "lidar",
                "name": "LIDAR",
                "full_name": "LIDAR Sensor Array",
                "icon": "📡",
                "color": "#b388ff",
                "messages": [
                    {"title": "Obstacle detected at 12m", "body": "Static obstacle in lane — emergency braking pre-armed"},
                    {"title": "LIDAR calibration drift", "body": "Point cloud offset 2.4cm — recalibration recommended"},
                    {"title": "Pedestrian trajectory conflict", "body": "Predicted pedestrian path intersects vehicle route in 3.2s"},
                    {"title": "LIDAR sensor occlusion", "body": "Front-left sensor partially occluded — reduced FOV 18°"},
                    {"title": "360° scan nominal", "body": "All 128 beam LIDAR channels operational, 100ms refresh"},
                ]
            },
            {
                "id": "gps",
                "name": "GPS/IMU",
                "full_name": "GPS & Inertial Nav",
                "icon": "🛰️",
                "color": "#00e676",
                "messages": [
                    {"title": "GPS signal lost", "body": "Satellite fix dropped — switching to dead reckoning via IMU"},
                    {"title": "Position accuracy degraded", "body": "HDOP 4.8 — position error ±8m, reducing autonomous speed"},
                    {"title": "Route deviation detected", "body": "Vehicle 34m off planned route — recalculating trajectory"},
                    {"title": "IMU calibration complete", "body": "Accelerometer and gyro bias corrected, accuracy ±0.02°"},
                    {"title": "GPS fix acquired — 14 satellites", "body": "RTK correction active, position accuracy ±2cm"},
                ]
            },
            {
                "id": "brake",
                "name": "Brake ECU",
                "full_name": "Brake Control System",
                "icon": "🔴",
                "color": "#ff3b3b",
                "messages": [
                    {"title": "Emergency brake activated", "body": "AEB triggered — collision avoidance braking at 1.2G"},
                    {"title": "Brake fluid pressure low", "body": "Hydraulic pressure 87 bar — below 95 bar threshold"},
                    {"title": "Brake pad wear critical", "body": "Front-left pad at 2mm — immediate replacement required"},
                    {"title": "ABS module fault", "body": "ABS solenoid valve 3 non-responsive — manual braking only"},
                    {"title": "Brake temperature nominal", "body": "Rotor temperature 142°C, within safe operating range"},
                ]
            },
            {
                "id": "bms",
                "name": "BMS",
                "full_name": "Battery Management",
                "icon": "🔋",
                "color": "#ffb300",
                "messages": [
                    {"title": "Battery SOC critical — 8%", "body": "State of charge below minimum — initiating emergency stop"},
                    {"title": "Cell voltage imbalance", "body": "Cell group 7 voltage 3.12V vs avg 3.67V — balancing needed"},
                    {"title": "Battery temp elevated", "body": "Pack temperature 52°C — thermal management active"},
                    {"title": "Charging port fault", "body": "Onboard charger communication failure — CAN bus timeout"},
                    {"title": "BMS health check passed", "body": "All 96 cells nominal, SOH 94%, estimated range 280km"},
                ]
            },
            {
                "id": "radar",
                "name": "RADAR",
                "full_name": "Radar Fusion Unit",
                "icon": "〰️",
                "color": "#00e5ff",
                "messages": [
                    {"title": "Vehicle ahead closing fast", "body": "Relative velocity -28 km/h at 6m — emergency brake armed"},
                    {"title": "Radar interference detected", "body": "Cross-talk from adjacent vehicle radar — filter activated"},
                    {"title": "Blind spot object detected", "body": "Object in right blind spot, lane change blocked"},
                    {"title": "Adaptive cruise disengaged", "body": "ACC deactivated — radar target lost in heavy rain"},
                    {"title": "RADAR self-test passed", "body": "77GHz radar array nominal, range 200m, update rate 20Hz"},
                ]
            },
            {
                "id": "tpms",
                "name": "TPMS",
                "full_name": "Tyre Pressure Monitor",
                "icon": "🔘",
                "color": "#ff9100",
                "messages": [
                    {"title": "Tyre pressure low — FL", "body": "Front-left at 24 PSI, recommended 32 PSI — stop advised"},
                    {"title": "Rapid pressure loss — RR", "body": "Rear-right pressure drop 8 PSI/min — possible puncture"},
                    {"title": "Tyre temp warning", "body": "Rear axle tyre temperature 98°C — reduce speed"},
                    {"title": "TPMS sensor battery low", "body": "Front-right TPMS sensor battery at 12% — replace soon"},
                    {"title": "All tyres nominal", "body": "FL:32 FR:31 RL:32 RR:31 PSI — within spec"},
                ]
            },
            {
                "id": "adas",
                "name": "ADAS",
                "full_name": "Advanced Driver Assist",
                "icon": "🤖",
                "color": "#b388ff",
                "messages": [
                    {"title": "Lane departure warning", "body": "Vehicle drifting left 0.3m — steering correction applied"},
                    {"title": "Traffic sign recognition", "body": "Speed limit 40 km/h detected — cruise adjusted"},
                    {"title": "Drowsiness alert", "body": "Driver attention score below threshold — rest recommended"},
                    {"title": "ADAS camera obstruction", "body": "Forward camera partially blocked by debris — clean windshield"},
                    {"title": "Autopilot handoff requested", "body": "Road conditions exceed system confidence — manual takeover"},
                ]
            },
        ]
    }

@app.get("/analytics/delivery-log/{nid}", tags=["Analytics"], summary="Full delivery attempt log for one notification")
def delivery_log(nid: str, _t: str=Depends(verify_token)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM delivery_log WHERE notification_id=? ORDER BY attempt", (nid,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

# ── Routes: WebSocket ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        conn = get_db(); sig = get_signal_at(current_position["lat"], current_position["lon"], conn)
        pending = conn.execute("SELECT COUNT(*) FROM notifications WHERE status IN ('QUEUED','DEFERRED','RETRYING')").fetchone()[0]
        conn.close()
        await websocket.send_text(json.dumps({"event":"connected","data":{
            "current_position":current_position,"signal":sig,"pending_count":pending,
            "server_time":datetime.now(timezone.utc).isoformat()},"ts":time.time()}))
        while True:
            msg = await websocket.receive_text()
            if msg == "ping": await websocket.send_text(json.dumps({"event":"pong","ts":time.time()}))
    except WebSocketDisconnect: ws_manager.disconnect(websocket)

# ── Health & Root ─────────────────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
def health(): return {"status":"ok","ts":time.time()}

@app.get("/", include_in_schema=False)
def root(): return JSONResponse({"service":"Geo-Deferred Notification Server","version":"1.0.0",
    "docs":"/docs","redoc":"/redoc","websocket":"ws://localhost:8000/ws","demo_token":DEMO_API_KEY,
    "endpoints":{"notifications":"POST/GET /notifications","zones":"GET/POST /zones",
                 "location":"POST /location","trip_simulate":"POST /trip/simulate",
                 "analytics":"GET /analytics","signal_query":"GET /zones/query?lat=&lon="}})

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
@app.get("/")
def serve_dashboard():
    return FileResponse("auto_dashboard.html")