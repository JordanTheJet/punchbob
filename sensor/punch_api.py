#!/usr/bin/env python3
from flask import Flask, jsonify, request
from flask_cors import CORS
import punch_new
import threading
import time
import math
import requests

app = Flask(__name__)
CORS(app)

# Flask backend URL for immediate punch callbacks
FLASK_BACKEND_URL = 'http://localhost:8080'

state = {
    "monitoring": False,
    "latest_punch": None,
    "last_punch": None,  # Persistent copy for debug display
    "current_accel": {"ax": 0, "ay": 0, "az": 0, "magnitude": 0, "dynamic": 0},
    "punch_count": 0,
    "active_session": None,  # Single active session ID (only one person can use the bag)
    "config": {
        "hit_start_g": 0.7,
        "hit_end_g": 0.3,
        "end_samples": 2,  # Reduced from 5 to 2 for faster detection (20ms vs 50ms)
        "max_force_g": 4.0
    }
}

monitor_thread = None
state_lock = threading.Lock()

def notify_flask_punch(session_id, force_value):
    """
    Immediately notify Flask backend when punch is detected.
    Non-blocking - runs in separate thread.
    """
    try:
        response = requests.post(
            f'{FLASK_BACKEND_URL}/api/punch',
            json={
                'session_id': session_id,
                'force': force_value
            },
            timeout=1
        )
        if response.status_code == 200:
            print(f"  → Notified Flask: session {session_id}")
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  Failed to notify Flask: {e}")

def monitor_punches():
    try:
        sens = punch_new.init_mpu()
        print("Sensor ready: {} LSB/g".format(sens))
    except Exception as e:
        print("Sensor init failed: {}".format(e))
        state["monitoring"] = False
        return
    
    in_hit = False
    hit_peak = 0.0
    hit_end_count = 0
    
    while state["monitoring"]:
        try:
            ax_g, ay_g, az_g = punch_new.read_accel_g(sens)
            if ax_g is None:
                time.sleep(0.01)
                continue

            a_mag = math.sqrt(ax_g**2 + ay_g**2 + az_g**2)
            a_dyn = max(0.0, a_mag - 1.0)

            # Update current acceleration for debug display
            with state_lock:
                state["current_accel"] = {
                    "ax": round(ax_g, 3),
                    "ay": round(ay_g, 3),
                    "az": round(az_g, 3),
                    "magnitude": round(a_mag, 3),
                    "dynamic": round(a_dyn, 3)
                }

            cfg = state["config"]

            if not in_hit:
                if a_dyn > cfg["hit_start_g"]:
                    in_hit = True
                    hit_peak = a_dyn
                    hit_end_count = 0
            else:
                if a_dyn > hit_peak:
                    hit_peak = a_dyn

                if a_dyn < cfg["hit_end_g"]:
                    hit_end_count += 1
                else:
                    hit_end_count = 0

                if hit_end_count >= cfg["end_samples"]:
                    punch_data = {
                        "force_g": round(hit_peak, 2),
                        "force_normalized": round(min(1.0, hit_peak / cfg["max_force_g"]), 3),
                        "force_value": round((hit_peak / cfg["max_force_g"]) * 1023, 1),
                        "timestamp": time.time()
                    }

                    with state_lock:
                        state["latest_punch"] = punch_data
                        state["last_punch"] = punch_data.copy()  # Keep persistent copy
                        state["punch_count"] += 1
                        active_session = state["active_session"]

                    print("Punch #{}: {:.2f}g".format(state["punch_count"], hit_peak))

                    # Immediately notify Flask backend
                    # If there's an active session, use it; otherwise use default (0) for hit sounds
                    session_to_notify = active_session if active_session else 0
                    threading.Thread(
                        target=notify_flask_punch,
                        args=(session_to_notify, punch_data["force_value"]),
                        daemon=True
                    ).start()

                    in_hit = False
                    hit_peak = 0.0
                    hit_end_count = 0

            time.sleep(0.01)
        
        except Exception as e:
            print("Error: {}".format(e))
            time.sleep(0.1)

@app.route("/status", methods=["GET"])
def get_status():
    with state_lock:
        return jsonify({
            "monitoring": state["monitoring"],
            "punch_count": state["punch_count"],
            "last_punch": state["last_punch"],
            "current_accel": state["current_accel"],
            "config": state["config"]
        })

@app.route("/latest-punch", methods=["GET"])
def get_latest():
    with state_lock:
        punch = state["latest_punch"]
        state["latest_punch"] = None
        
        if punch:
            return jsonify({"success": True, "punch": punch})
        return jsonify({"success": False}), 404

@app.route("/start", methods=["POST"])
def start():
    global monitor_thread
    
    if state["monitoring"]:
        return jsonify({"success": False, "message": "Already running"})
    
    state["monitoring"] = True
    monitor_thread = threading.Thread(target=monitor_punches, daemon=True)
    monitor_thread.start()
    
    return jsonify({"success": True})

@app.route("/stop", methods=["POST"])
def stop():
    state["monitoring"] = False
    return jsonify({"success": True})

@app.route("/config", methods=["GET", "POST"])
def config_endpoint():
    if request.method == "GET":
        return jsonify(state["config"])

    data = request.json
    with state_lock:
        for key in ["hit_start_g", "hit_end_g", "end_samples", "max_force_g"]:
            if key in data:
                state["config"][key] = float(data[key]) if "g" in key or "max" in key else int(data[key])

    return jsonify({"success": True, "config": state["config"]})

@app.route("/register-session", methods=["POST"])
def register_session():
    """
    Register a session to receive immediate punch notifications.
    Only ONE session can be active at a time (replaces any existing session).
    """
    data = request.json
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    with state_lock:
        previous_session = state["active_session"]
        state["active_session"] = session_id

        if previous_session and previous_session != session_id:
            print(f"⚠️  Replaced session {previous_session} with {session_id}")
        else:
            print(f"✓ Registered session {session_id} for punch notifications")

    return jsonify({
        "success": True,
        "session_id": session_id,
        "replaced_session": previous_session
    })

@app.route("/unregister-session", methods=["POST"])
def unregister_session():
    """Unregister a session from receiving punch notifications"""
    data = request.json
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    with state_lock:
        if state["active_session"] == session_id:
            state["active_session"] = None
            print(f"✓ Unregistered session {session_id}")
            was_active = True
        else:
            was_active = False

    return jsonify({"success": True, "session_id": session_id, "was_active": was_active})

if __name__ == "__main__":
    print("Punch Detection API - Port 8081")
    
    state["monitoring"] = True
    monitor_thread = threading.Thread(target=monitor_punches, daemon=True)
    monitor_thread.start()
    
    app.run(host="0.0.0.0", port=8081, debug=False)
