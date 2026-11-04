import os
import sys
# Asegurar que las importaciones resuelvan siempre dentro del propio paquete backend
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from game import GameEngine, TXT_LOG_FILE, LOG_FILE
from ai_client import IterationRunner, get_active_model_name, get_lm_studio_host, set_lm_studio_host

app = FastAPI(title="Mundo Hexagonal - IA Explorer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

game = GameEngine()
runner = IterationRunner(game)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

VERSION_FILE = os.path.join(os.path.dirname(__file__), "..", "VERSION.txt")

@app.get("/api/version")
def get_version():
    ver = "V1.261104.5"
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            ver = f.read().strip()
    return {"version": ver}

@app.get("/api/config/llm")
def get_llm_config():
    return {
        "host": get_lm_studio_host(),
        "model": get_active_model_name()
    }

@app.post("/api/config/llm")
async def update_llm_config(request: Request):
    data = await request.json()
    host = data.get("host", "http://127.0.0.1:1234")
    result = set_lm_studio_host(host)
    return result

@app.get("/")
def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Cargando interfaz...</h1>")

@app.get("/api/model")
def get_model():
    return {"model": get_active_model_name(), "host": get_lm_studio_host()}

@app.get("/api/state")
def get_state():
    return {
        "hexes": game.hexes,
        "robot": game.robot,
        "world_summary": game.get_world_summary_for_ai(),
        "recent_history": game.history[-10:] if game.history else [],
        "model": get_active_model_name(),
        "llm_host": get_lm_studio_host()
    }

@app.get("/api/run_iteration_stream")
async def run_iteration_stream():
    """
    Transmite en tiempo real cada paso de la iteración mediante Server-Sent Events (SSE).
    """
    async def event_generator():
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def step_callback(step_data):
            # Notificar al bucle asíncrono
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "step", "data": step_data, "robot": game.robot, "hexes": game.hexes})

        async def worker():
            try:
                # Ejecutar la iteración en un hilo separado para no bloquear FastAPI
                result = await asyncio.to_thread(runner.run_10_actions, step_callback)
                await queue.put({"type": "complete", "data": result, "robot": game.robot, "hexes": game.hexes})
            except Exception as e:
                await queue.put({"type": "error", "message": str(e)})

        asyncio.create_task(worker())

        yield f"data: {json.dumps({'type': 'start', 'iteracion': game.robot['iteracion'] + 1})}\n\n"

        while True:
            msg = await queue.get()
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            if msg.get("type") in ("complete", "error"):
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/memoria")
def get_memoria():
    return {"memoria": game.get_memoria_robot()}

@app.get("/api/log")
def get_log_json():
    return {
        "history": game.history
    }

@app.get("/api/log/text")
def get_log_text():
    if os.path.exists(TXT_LOG_FILE):
        with open(TXT_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            return PlainTextResponse(content)
    return PlainTextResponse("El archivo de log aún no contiene eventos.")

@app.post("/api/reset")
def reset_game():
    game.reset()
    return {"status": "ok", "message": "Juego reiniciado correctamente.", "state": get_state()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
