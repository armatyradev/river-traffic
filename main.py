import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from simulator import TrafficSimulator

app = FastAPI(title="Smart Fairway Backend (ITS Volga-N)")

# Разрешаем CORS для локального фронтенда на Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim = TrafficSimulator()

class IncidentToggleRequest(BaseModel):
    active: bool

class CargoConsolidateRequest(BaseModel):
    consolidate: bool

@app.get("/api/health")
def health_check():
    return {"status": "ok", "system": "СУДС Волга-Н Core Engine"}

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "СУДС Волга-Н Core Engine",
        "docs_url": "http://localhost:8000/docs",
        "ws_endpoint": "ws://localhost:8000/ws/telemetry"
    }

@app.post("/api/simulation/incident")
def toggle_emergency(req: IncidentToggleRequest):
    sim.emergency_mode = req.active
    return {"status": "success", "emergency_active": sim.emergency_mode}

@app.post("/api/cargo/consolidate")
def toggle_cargo(req: CargoConsolidateRequest):
    sim.cargo_consolidated = req.consolidate
    return {"status": "success", "cargo_consolidated": sim.cargo_consolidated}

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Делаем тик физики в симуляторе
            payload = sim.step()
            # Отправляем GeoJSON клиентам
            await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass