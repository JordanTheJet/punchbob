from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import os
import sys
import json
import time
import threading
import requests
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from database import Database
from services.character_generator import CharacterGenerator
from services.punch_handler import PunchHandler

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
DATA_DIR = os.getenv('DATA_DIR', '../data')
DB_PATH = os.getenv('DATABASE_PATH', f'{DATA_DIR}/punching_bag.db')
db = Database(DB_PATH)

# Initialize character generator
generator = CharacterGenerator(db, DATA_DIR)

# Active workout sessions
active_sessions = {}  # {session_id: PunchHandler}

# Create a default handler for when no workout is active (just plays hit sounds)
default_handler = None

def init_default_handler():
    """Initialize default handler for hit sounds when no workout is active"""
    global default_handler
    from services.punch_handler import PunchHandler
    # Use session_id=0 and a dummy character_id for default handler
    default_handler = PunchHandler(
        db=db,
        character_id=0,  # Dummy ID
        session_id=0,    # Default session
        feedback_mode='hit_sounds',  # Always use hit sounds
        data_dir=DATA_DIR
    )
    print("✓ Initialized default hit sound handler")


# ===== Character Management Routes =====

@app.route('/api/characters', methods=['GET'])
def get_characters():
    """Get all characters"""
    characters = db.get_all_characters()
    return jsonify(characters)


@app.route('/api/characters/<int:character_id>', methods=['GET'])
def get_character(character_id):
    """Get single character"""
    character = db.get_character(character_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    return jsonify(character)


@app.route('/api/characters', methods=['POST'])
def create_character():
    """
    Create new character with AI-generated responses.

    Streams progress updates via Server-Sent Events (SSE).

    Body (FormData or JSON):
    - name: Character name
    - relationship: boss/coworker/rival/ex/trainer/fictional/custom
    - personality: Personality traits
    - intensity: 1-5
    - description: Optional additional context
    - voice_id: ElevenLabs voice ID (preset or custom)
    """
    # Handle both JSON and FormData
    if request.content_type and 'multipart/form-data' in request.content_type:
        # FormData
        character_data = {
            'name': request.form.get('name'),
            'relationship': request.form.get('relationship'),
            'personality': request.form.get('personality'),
            'intensity': int(request.form.get('intensity', 3)),
            'description': request.form.get('description', ''),
            'voice_id': request.form.get('voice_id'),  # Direct voice ID
        }

        print(f"📋 Character creation request:")
        print(f"   Name: {character_data['name']}")
        print(f"   Voice ID: {character_data['voice_id']}")
    else:
        # JSON request (backwards compatible)
        character_data = request.json
        print(f"📋 Character creation (JSON): {character_data.get('name')}")
        print(f"   Voice ID: {character_data.get('voice_id')}")

    def generate():
        """SSE generator for progress updates"""
        try:
            for update in generator.generate_character(character_data):
                # Format as SSE
                yield f"data: {json.dumps(update)}\n\n"

                # Flush to ensure client receives immediately
                time.sleep(0.01)

        except Exception as e:
            error_msg = {"status": "error", "message": str(e)}
            yield f"data: {json.dumps(error_msg)}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/characters/<int:character_id>/stats', methods=['GET'])
def get_character_stats(character_id):
    """Get statistics for a character"""
    stats = db.get_character_stats(character_id)
    return jsonify(stats)


@app.route('/api/characters/<int:character_id>', methods=['DELETE'])
def delete_character(character_id):
    """Delete a character"""
    db.delete_character(character_id)
    return jsonify({"success": True})


@app.route('/api/voices/clone', methods=['POST'])
def clone_voice():
    """
    Clone a voice from uploaded audio sample

    Body (FormData):
    - voice_sample: Audio file
    - voice_name: Name for the cloned voice
    """
    try:
        voice_sample = request.files.get('voice_sample')
        voice_name = request.form.get('voice_name')

        if not voice_sample:
            return jsonify({"error": "voice_sample file required"}), 400
        if not voice_name:
            return jsonify({"error": "voice_name required"}), 400

        # Save temp file
        temp_dir = Path(DATA_DIR) / 'temp'
        temp_dir.mkdir(exist_ok=True)
        sample_path = temp_dir / f"sample_{int(time.time())}_{voice_sample.filename}"
        voice_sample.save(str(sample_path))

        print(f"🎤 Voice cloning request:")
        print(f"   Voice name: {voice_name}")
        print(f"   Sample saved to: {sample_path}")

        # Clone voice using ElevenLabs
        from elevenlabs.client import ElevenLabs
        elevenlabs = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

        with open(sample_path, 'rb') as audio_file:
            voice = elevenlabs.voices.ivc.create(
                name=voice_name,
                files=[audio_file]
            )

        print(f"   ✅ Voice cloned: {voice.voice_id}")

        # Clean up temp file
        try:
            os.remove(sample_path)
            print(f"   🗑️  Temp file cleaned up")
        except Exception as e:
            print(f"   ⚠️  Could not delete temp file: {e}")

        return jsonify({
            "success": True,
            "voice_id": voice.voice_id,
            "voice_name": voice_name
        })

    except Exception as e:
        print(f"❌ Voice cloning failed: {str(e)}")
        return jsonify({"error": "Voice cloning failed", "details": str(e)}), 500


@app.route('/api/voices', methods=['GET'])
def get_voices():
    """
    Get available ElevenLabs voices (preset + custom voices from account)

    Returns:
    {
        "voices": [
            {"id": "pNInz6obpgDQGcFmaJgB", "name": "Default", "is_custom": false},
            {"id": "abc123", "name": "My Custom Voice (custom)", "is_custom": true},
            ...
        ]
    }
    """
    try:
        from elevenlabs.client import ElevenLabs
        elevenlabs = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

        # Preset voices (with descriptions)
        preset_voices = [
            {"id": "pNInz6obpgDQGcFmaJgB", "name": "Default", "is_custom": False},
            {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Aggressive Male", "is_custom": False},
            {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Sarcastic Female", "is_custom": False},
            {"id": "VR6AewLTigWG4xSOukaG", "name": "Stern Boss", "is_custom": False},
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Playful", "is_custom": False}
        ]

        voices = preset_voices.copy()

        # Fetch only user-created custom voices from ElevenLabs account
        try:
            all_voices = elevenlabs.voices.get_all()

            # Add only user-created voices (filter out default ElevenLabs voices)
            for voice in all_voices.voices:
                # Only include voices that are user-created (cloned/custom)
                # Default voices like "Clyde", "Bill" etc have category "premade"
                if hasattr(voice, 'category') and voice.category in ['cloned', 'custom']:
                    voices.append({
                        "id": voice.voice_id,
                        "name": f"{voice.name} (custom)",
                        "is_custom": True
                    })

            print(f"✓ Loaded {len(voices)} voices ({len(preset_voices)} preset + {len(voices) - len(preset_voices)} custom)")
        except Exception as e:
            print(f"⚠️  Failed to fetch custom voices from ElevenLabs: {e}")

        return jsonify({"voices": voices})

    except Exception as e:
        return jsonify({"error": "Failed to fetch voices", "details": str(e)}), 500


# ===== Workout Session Routes =====

@app.route('/api/sessions', methods=['POST'])
def start_session():
    """
    Start a new workout session

    Body:
    {
        "character_id": 1
    }
    """
    data = request.json
    character_id = data.get('character_id')

    if not character_id:
        return jsonify({"error": "character_id required"}), 400

    # Verify character exists
    character = db.get_character(character_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404

    # Create session
    session_id = db.create_session(character_id)

    # Get feedback mode preference (default: grunts)
    feedback_mode = data.get('feedback_mode', 'grunts')

    # Initialize punch handler
    handler = PunchHandler(db, character_id, session_id, feedback_mode=feedback_mode, data_dir=DATA_DIR)
    active_sessions[session_id] = handler

    # Register session with punch API for immediate notifications
    try:
        requests.post(f'{PUNCH_API_URL}/register-session',
                     json={'session_id': session_id},
                     timeout=2)
        print(f"✓ Registered session {session_id} with punch API")
    except Exception as e:
        print(f"⚠️  Failed to register session with punch API: {e}")

    return jsonify({
        "session_id": session_id,
        "character_id": character_id,
        "character_name": character['name'],
        "feedback_mode": feedback_mode,
        "started_at": time.time()
    })


@app.route('/api/sessions/<int:session_id>/feedback-mode', methods=['POST'])
def update_feedback_mode(session_id):
    """
    Update feedback mode for active session

    Body:
    {
        "feedback_mode": "grunts" | "hit_sounds" | "silent"
    }
    """
    handler = active_sessions.get(session_id)
    if not handler:
        return jsonify({"error": "Session not found or ended"}), 404

    data = request.json
    new_mode = data.get('feedback_mode')

    if new_mode not in ['grunts', 'hit_sounds', 'silent']:
        return jsonify({"error": "Invalid feedback mode"}), 400

    handler.set_feedback_mode(new_mode)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "feedback_mode": new_mode
    })


@app.route('/api/sessions/<int:session_id>/end', methods=['POST'])
def end_session(session_id):
    """End a workout session"""
    if session_id in active_sessions:
        del active_sessions[session_id]

    # Unregister session from punch API
    try:
        requests.post(f'{PUNCH_API_URL}/unregister-session',
                     json={'session_id': session_id},
                     timeout=2)
        print(f"✓ Unregistered session {session_id} from punch API")
    except Exception as e:
        print(f"⚠️  Failed to unregister session from punch API: {e}")

    db.end_session(session_id)

    session = db.get_session(session_id)
    return jsonify(session)


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details"""
    session = db.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session)


# ===== Punch Detection Route =====

@app.route('/api/punch', methods=['POST'])
def handle_punch():
    """
    Handle a punch event from the sensor.

    Body:
    {
        "session_id": 1,  (or 0 for default hit sounds)
        "force": 789.5
    }

    Returns:
    {
        "force": 77.2,
        "tier": 4,
        "text": "Now we're talking!",
        "audio_path": "/path/to/audio.mp3",
        "latency_ms": 15
    }
    """
    data = request.json
    session_id = data.get('session_id')
    force = data.get('force')

    if session_id is None or force is None:
        return jsonify({"error": "session_id and force required"}), 400

    # Use default handler for session_id=0 (no active workout)
    if session_id == 0:
        handler = default_handler
        if not handler:
            init_default_handler()
            handler = default_handler
    else:
        handler = active_sessions.get(session_id)
        if not handler:
            return jsonify({"error": "Session not found or ended"}), 404

    # Handle punch
    result = handler.handle_punch(force)

    # Broadcast to WebSocket clients (if not default session)
    if session_id != 0:
        socketio.emit('punch', result, room=f'session_{session_id}')

    return jsonify(result)


# ===== WebSocket Events (Real-time updates) =====

@socketio.on('join_session')
def on_join_session(data):
    """Client joins a session room for real-time updates"""
    session_id = data.get('session_id')
    room = f'session_{session_id}'
    # Join room logic here if needed
    emit('joined', {"session_id": session_id, "room": room})


@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnect"""
    pass


# ===== Static File Serving =====

@app.route('/')
def serve_frontend():
    """Serve React frontend"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)


# ===== Health Check =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "database": "connected",
        "active_sessions": len(active_sessions)
    })


# ===== Punch API Integration =====

PUNCH_API_URL = 'http://localhost:8081'


@app.route('/api/sensor/config', methods=['GET', 'POST'])
def sensor_config():
    """Proxy to punch API config endpoint for sensitivity settings"""
    try:
        if request.method == 'GET':
            response = requests.get(f'{PUNCH_API_URL}/config', timeout=2)
            return jsonify(response.json())
        else:
            # Update config
            response = requests.post(f'{PUNCH_API_URL}/config', json=request.json, timeout=2)
            return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Punch API not available", "details": str(e)}), 503


@app.route('/api/sensor/status', methods=['GET'])
def sensor_status():
    """Proxy to punch API status endpoint"""
    try:
        response = requests.get(f'{PUNCH_API_URL}/status', timeout=2)
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Punch API not available", "details": str(e)}), 503


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ===== Main =====

if __name__ == '__main__':
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    print(f"""
    ╔════════════════════════════════════════╗
    ║  Trash-Talking Punching Bag Server     ║
    ║  Running on http://{HOST}:{PORT}       ║
    ║  Push-based punch notifications        ║
    ╚════════════════════════════════════════╝
    """)

    # Run with SocketIO
    socketio.run(app, host=HOST, port=PORT, debug=True, allow_unsafe_werkzeug=True)
