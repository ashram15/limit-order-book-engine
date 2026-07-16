import socket
import time
import os
import threading
import random
import json
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

ENGINE_HOST = os.getenv('ENGINE_HOST', '127.0.0.1')

bids = {}
asks = {}
trades = []
stats = {"throughput": 0, "total_orders": 0, "total_matches": 0}
state_lock = threading.Lock()
start_time = time.time()
step_mode = False
next_order_event = threading.Event()
latest_incoming = None
latest_event = None
is_running = False
market_maker_thread = None
active_ws_session = 0
live_delay = 0.3

app = FastAPI()

# MARKET MAKER


def market_maker():
    global latest_incoming, latest_event
    print("✅ Trader Algorithm Started...")
    with state_lock:
        bids.clear()
        asks.clear()
        trades.clear()
        stats["throughput"] = 0
        stats["total_orders"] = 0
        stats["total_matches"] = 0
        latest_incoming = None
        latest_event = None
    while is_running:
        try:
            if step_mode:
                next_order_event.wait()
                next_order_event.clear()

            side = random.choice(["B", "S"])
            if side == "B":
                price = random.randint(95, 102)
            else:
                price = random.randint(98, 105)
            qty = random.randint(1, 10)
            incoming = {"side": side, "price": price, "qty": qty}

            # Send to C++ engine (your existing protocol, unchanged)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ENGINE_HOST, 8080))
            msg = f"{side} {price} {qty}"
            client.send(msg.encode('utf-8'))
            response = client.recv(1024).decode(
                'utf-8').strip()  # NOW we read response
            client.close()

            # Update state based on response
            with state_lock:
                latest_incoming = incoming
                best_bid_before = max(bids.keys()) if bids else None
                best_ask_before = min(asks.keys()) if asks else None
                stats["total_orders"] += 1
                elapsed = time.time() - start_time
                stats["throughput"] = round(stats["total_orders"] / elapsed, 1)

                if response.startswith("MATCH"):
                    parts = response.split()
                    matched_price = int(float(parts[1]))
                    matched_qty = int(parts[2])

                    stats["total_matches"] += 1
                    trades.append({
                        "price": matched_price,
                        "qty": matched_qty,
                        "side": side,
                        "time": time.strftime("%H:%M:%S")
                    })
                    if len(trades) > 20:
                        trades.pop(0)
                    latest_event = {
                        "type": "match",
                        "incoming": incoming,
                        "matched_price": matched_price,
                        "matched_qty": matched_qty,
                        "best_bid_before": best_bid_before,
                        "best_ask_before": best_ask_before
                    }

                    # now we know EXACTLY which price level to remove from
                    if matched_price in bids:
                        bids[matched_price] = max(
                            0, bids[matched_price] - matched_qty)
                        if bids[matched_price] == 0:
                            del bids[matched_price]
                    if matched_price in asks:
                        asks[matched_price] = max(
                            0, asks[matched_price] - matched_qty)
                        if asks[matched_price] == 0:
                            del asks[matched_price]
                else:
                    # Order resting in book — add to local state
                    book = bids if side == "B" else asks
                    book[price] = book.get(price, 0) + qty
                    latest_event = {
                        "type": "rest",
                        "incoming": incoming,
                        "best_bid_before": best_bid_before,
                        "best_ask_before": best_ask_before
                    }

                # Keep only top 15 levels per side
                if len(bids) > 15:
                    for p in sorted(bids)[:-15]:
                        del bids[p]
                if len(asks) > 15:
                    for p in sorted(asks, reverse=True)[:-15]:
                        del asks[p]

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)
            continue

        time.sleep(2.0 if step_mode else live_delay)


# --- WEBSOCKET (instead of matplotlib) ---~
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global is_running, market_maker_thread, start_time, latest_incoming, latest_event, active_ws_session
    await websocket.accept()
    active_ws_session += 1
    my_session = active_ws_session
    is_running = True
    start_time = time.time()
    market_maker_thread = threading.Thread(target=market_maker, daemon=True)
    market_maker_thread.start()
    try:
        while True:
            with state_lock:
                payload = {
                    "bids": dict(sorted(bids.items(), reverse=True)[:10]),
                    "asks": dict(sorted(asks.items())[:10]),
                    "trades": list(trades),
                    "throughput": stats["throughput"],
                    "total_orders": stats["total_orders"],
                    "total_matches": stats["total_matches"],
                    "incoming": latest_incoming,
                    "event": latest_event,
                    "step_mode": step_mode
                }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.2)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if my_session != active_ws_session:
            return
        is_running = False
        next_order_event.set()
        with state_lock:
            bids.clear()
            asks.clear()
            trades.clear()
            stats["throughput"] = 0
            stats["total_orders"] = 0
            stats["total_matches"] = 0
            latest_incoming = None
            latest_event = None


@app.get("/")
async def dashboard():
    return HTMLResponse(open("dashboard.html").read())


class ModeRequest(BaseModel):
    step_mode: bool


class SpeedRequest(BaseModel):
    speed_ms: int


@app.post("/mode")
async def set_mode(req: ModeRequest):
    global step_mode
    step_mode = req.step_mode
    if not step_mode:
        next_order_event.set()
    return {"step_mode": step_mode}


@app.post("/next")
async def next_order():
    if step_mode:
        next_order_event.set()
        return {"queued": True}
    return {"queued": False, "message": "Step mode is not enabled"}


@app.post("/speed")
async def set_speed(req: SpeedRequest):
    global live_delay
    speed_ms = max(50, min(2000, req.speed_ms))
    live_delay = speed_ms / 1000.0
    return {"speed_ms": speed_ms}


@app.on_event("startup")
async def startup():
    next_order_event.set()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
