# System Architecture

## Overview

This is a **offline-first** punching bag system with AI-generated character rivals. Characters are created once (requires internet), then workouts run 100% offline with <200ms latency.

## Key Design Decisions

### 1. Prebaked Responses (Not Real-Time Generation)
- **Why**: Real-time LLM calls would have 1-3 second latency (unusable for workout)
- **How**: Generate 15 responses per character ahead of time (45 seconds)
- **Benefit**: <30ms response selection, $0.08 per character, fully offline workouts

### 2. 5-Tier Punch Categorization
- **Tier 1**: 0-20% of max force (Weak)
- **Tier 2**: 20-40% (Light)
- **Tier 3**: 40-60% (Medium)
- **Tier 4**: 60-85% (Hard)
- **Tier 5**: 85-100% (Maximum)

Each tier gets 3 unique responses = 15 total per character.

### 3. Simple HTML/CSS/JS Frontend (Not React)
- **Why**: Faster to deploy, smaller bundle, works on any Pi
- **How**: Vanilla JS with fetch API and EventSource for SSE
- **Benefit**: No build step, no node_modules, instant deployment

### 4. Flask + SQLite Backend
- **Why**: Simple, Pi-friendly, no complex setup
- **How**: Flask for API, SQLite for data, mpg123 for audio
- **Benefit**: Runs on Pi 2 with 1GB RAM, easy to debug

---

## Data Flow

### Character Creation (One-Time, Requires Internet)

```
User Input (Name, Personality, Intensity)
    ↓
Flask API receives POST /api/characters
    ↓
CharacterGenerator.generate_character()
    ├─→ Call Claude API (generate 15 text responses)
    ├─→ Call ElevenLabs API (convert to audio)
    └─→ Store in:
        - Database (metadata, response text)
        - Filesystem (MP3 files)
    ↓
Stream progress via Server-Sent Events
    ↓
Frontend updates progress bar
    ↓
Complete (45 seconds)
```

**Storage Layout:**
```
data/characters/boss_steve/
├── responses/
│   ├── tier1_001.mp3  (20KB)
│   ├── tier1_002.mp3
│   ├── tier1_003.mp3
│   ├── tier2_001.mp3
│   ...
│   └── tier5_003.mp3
```

Total: ~300KB per character

### Workout Session (Fully Offline)

```
User clicks character → Start Workout
    ↓
Flask API creates session in database
    ↓
PunchHandler initialized (loads all responses into RAM)
    ↓
[SENSOR DETECTS PUNCH]
    ↓
Force value (0-1023) → POST /api/punch
    ↓
PunchHandler.handle_punch(force)
    ├─→ Normalize to percentage (0-100%)
    ├─→ Calculate tier (1-5)
    ├─→ Select random response for tier (avoid recent repeats)
    ├─→ Play audio (mpg123 subprocess, non-blocking)
    └─→ Log to database (async)
    ↓
Return response to frontend (<30ms total)
    ↓
Frontend updates stats + displays trash talk
```

**Latency Breakdown:**
- Sensor → API: ~10ms (local network)
- Response selection: ~5ms (O(1) lookup in cache)
- Audio playback start: ~10ms (subprocess spawn)
- **Total: ~25ms** (target was <200ms ✅)

---

## Database Schema

### Characters
```sql
CREATE TABLE characters (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    relationship TEXT,
    personality TEXT,
    intensity INTEGER,
    voice_id TEXT,
    created_at TIMESTAMP,
    total_sessions INTEGER DEFAULT 0
);
```

### Responses
```sql
CREATE TABLE responses (
    id INTEGER PRIMARY KEY,
    character_id INTEGER,
    tier INTEGER,              -- 1-5
    text TEXT,                 -- "Is that all you got?"
    audio_path TEXT,           -- /path/to/tier3_001.mp3
    times_played INTEGER
);
```

### Workout Sessions
```sql
CREATE TABLE workout_sessions (
    id INTEGER PRIMARY KEY,
    character_id INTEGER,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    total_punches INTEGER,
    avg_force REAL,
    max_force REAL
);
```

### Punches
```sql
CREATE TABLE punches (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    character_id INTEGER,
    force_value REAL,          -- 0-100%
    tier INTEGER,              -- 1-5
    response_id INTEGER,
    timestamp TIMESTAMP
);
```

---

## API Endpoints

### Character Management

**GET /api/characters**
- Returns: List of all characters

**POST /api/characters**
- Body: `{name, relationship, personality, intensity, voice_style}`
- Returns: Server-Sent Events stream with progress
- Events:
  - `{status: "creating", progress: 5}`
  - `{status: "generating_responses", progress: 15}`
  - `{status: "generating_audio", progress: 45, current: 3, total: 15}`
  - `{status: "completed", progress: 100, character_id: 1}`

**GET /api/characters/:id/stats**
- Returns: Statistics for character

**DELETE /api/characters/:id**
- Soft delete character

### Workout Sessions

**POST /api/sessions**
- Body: `{character_id: 1}`
- Returns: `{session_id, character_name, started_at}`

**POST /api/sessions/:id/end**
- Ends session, calculates stats
- Returns: Session summary

**POST /api/punch**
- Body: `{session_id, force: 789.5}`
- Returns: `{tier, text, audio_path, latency_ms}`

---

## Technology Stack

### Backend
- **Python 3.9+**
- **Flask 3.0**: Web framework
- **Flask-SocketIO**: WebSocket support (future)
- **Anthropic Python SDK**: Claude API client
- **ElevenLabs Python SDK**: TTS API client
- **SQLite3**: Database (built-in)
- **mpg123**: Audio playback (system package)

### Frontend
- **Vanilla JavaScript ES6**
- **Fetch API**: HTTP requests
- **EventSource API**: Server-Sent Events
- **CSS Grid/Flexbox**: Layout

### Infrastructure
- **Nginx**: Reverse proxy + static file serving
- **systemd**: Service management
- **Raspberry Pi OS Lite**: Operating system

---

## Scaling Strategy

### MVP (Current): 15 Responses
- 3 per tier × 5 tiers
- Generation time: ~45 seconds
- Cost: ~$0.08 per character
- Good for 3-4 workout sessions before repetition

### Phase 2: 30 Responses
- 6 per tier × 5 tiers
- Generation time: ~90 seconds
- Cost: ~$0.15 per character
- Good for 8-10 sessions

### Phase 3: 60+ Responses
- 12 per tier × 5 tiers
- Generation time: ~3 minutes
- Cost: ~$0.30 per character
- Virtually no repetition

### Auto-Expansion Feature (Future)
```python
# After user completes 5 sessions with a character:
if character.total_sessions >= 5 and character.response_count < 30:
    # Generate 15 more responses in background
    background_generate_responses(character)
    notify_user("Your rival just got meaner - 15 new responses added!")
```

---

## Performance Optimizations

### Database
- **Indexes**: On `character_id`, `tier`, `session_id`
- **Cache responses in RAM**: O(1) lookup during workout
- **Async writes**: Don't block audio playback

### Audio
- **mpg123** (not pygame): Lowest latency on Pi
- **MP3 format**: Better compression than WAV
- **22kHz sample rate**: Sufficient for voice, smaller files
- **Non-blocking playback**: Subprocess spawning

### Frontend
- **No JavaScript frameworks**: Smaller payload
- **Lazy loading**: Only load character details when needed
- **Local storage**: Cache character list

### Network
- **Server-Sent Events** (not WebSockets): Simpler, unidirectional
- **Nginx reverse proxy**: Offload static files from Flask

---

## Hardware Integration

### Recommended Sensor: ADXL345
- **Interface**: I2C (4 pins: VCC, GND, SDA, SCL)
- **Range**: ±16g (perfect for punches)
- **Cost**: $5-10
- **Sample rate**: 400Hz (more than enough)

### Wiring
```
ADXL345 → Raspberry Pi
VCC     → Pin 1 (3.3V)  ⚠️ NOT 5V!
GND     → Pin 6 (GND)
SDA     → Pin 3 (GPIO 2)
SCL     → Pin 5 (GPIO 3)
```

### Mounting
- **Location**: Center back of punching bag
- **Protection**: Foam padding + waterproof case
- **Attachment**: Industrial velcro or strong adhesive
- **Orientation**: Z-axis perpendicular to striking surface

### Force Calculation
```python
# Read raw values
x, y, z = sensor.read_raw()

# Convert to g's (ADXL345: 4mg per LSB at ±16g)
x_g = x * 0.004
y_g = y * 0.004
z_g = z * 0.004

# Calculate magnitude
magnitude = sqrt(x_g² + y_g² + z_g²)

# Subtract gravity baseline (~1g at rest)
force = abs(magnitude - 1.0)

# Normalize to 0-1023 range for API
force_value = force * 100
```

---

## Security Considerations

### API Keys
- **Storage**: `.env` file (not in git)
- **Permissions**: `chmod 600 backend/.env`
- **Backup**: Store in password manager

### Network
- **Local only**: No external exposure by default
- **Nginx**: Rate limiting (optional)
- **HTTPS**: Can add Let's Encrypt cert (optional)

### Data Privacy
- **All local**: No data sent to cloud during workouts
- **Character data**: Stored only on Pi's SD card
- **Anonymization**: Character names never sent to APIs

---

## Troubleshooting Guide

### Issue: Character generation fails

**Symptoms**: Error after clicking "Generate Character"

**Solutions**:
1. Check API keys in `backend/.env`
2. Verify internet connection
3. Check backend logs: `sudo journalctl -u punchingbag -f`
4. Test APIs directly:
   ```python
   from anthropic import Anthropic
   client = Anthropic(api_key="your_key")
   print(client.messages.create(...))
   ```

### Issue: No audio playing

**Symptoms**: Trash talk text appears but no sound

**Solutions**:
1. Check speaker connection
2. Install mpg123: `sudo apt-get install mpg123`
3. Test audio: `mpg123 /path/to/audio.mp3`
4. Check volume: `alsamixer`

### Issue: Sensor not detected

**Symptoms**: `i2cdetect` shows no devices

**Solutions**:
1. Check wiring (especially 3.3V, not 5V)
2. Enable I2C: `sudo raspi-config` → Interface → I2C
3. Reboot Pi
4. Test: `i2cdetect -y 1` (should show 0x53)

### Issue: High latency (>200ms)

**Symptoms**: Delay between punch and audio

**Causes**:
1. Network congestion (if using WiFi)
2. Database writes blocking
3. Audio file corruption

**Solutions**:
1. Use Ethernet instead of WiFi
2. Check `response_latency_ms` in database
3. Regenerate character
4. Optimize code (profile with `cProfile`)

---

## Future Enhancements

### Phase 1 (Next 2 weeks)
- [ ] Real accelerometer integration
- [ ] Auto-calibration on first use
- [ ] Character editing after creation
- [ ] Session history view

### Phase 2 (Next month)
- [ ] Multi-user profiles
- [ ] Achievement system
- [ ] Combo detection (rapid punches)
- [ ] Voice command support

### Phase 3 (2-3 months)
- [ ] Adaptive difficulty (characters get meaner as you improve)
- [ ] Character evolution (new responses after 20 sessions)
- [ ] Mobile app (React Native)
- [ ] Social features (leaderboards, challenges)

### Advanced (Future)
- [ ] Machine learning punch classification
- [ ] Punch type detection (jab vs hook vs uppercut)
- [ ] Form analysis via additional sensors
- [ ] Cloud sync (optional) for multi-device stats

---

## Development Workflow

### Local Development
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python app.py

# Terminal 2: Frontend
cd frontend
python3 -m http.server 8000

# Test
open http://localhost:8000
```

### Testing Without Hardware
```bash
# Test character generation
python3 backend/services/character_generator.py

# Test punch handling (simulated)
python3 backend/services/punch_handler.py

# Frontend: Click "Simulate Punch" button
```

### Deployment to Pi
```bash
# Package for deployment
cd ..
tar -czf punching-bag.tar.gz punching-bag/

# Copy to Pi
scp punching-bag.tar.gz pi@raspberrypi.local:/home/pi/

# On Pi
ssh pi@raspberrypi.local
tar -xzf punching-bag.tar.gz
cd punching-bag
sudo bash scripts/setup.sh
```

---

## Cost Analysis

### Development Costs
- Raspberry Pi 2: $0 (already owned)
- ADXL345 sensor: $5-10
- USB speaker: $10 (optional, use 3.5mm)
- MicroSD card: $5-10
- **Total hardware: $20-30**

### API Costs (Per Character)
- Claude API (15 responses): ~$0.001
- ElevenLabs TTS (15 audio files): ~$0.08
- **Total per character: $0.08**

### Scaling
- 20 characters: $1.60
- 100 characters: $8.00
- 1000 characters: $80.00

**Runtime costs: $0** (fully offline)

---

## Maintenance

### Regular Tasks
- **Daily**: Check logs for errors
- **Weekly**: Backup database (`cp punching_bag.db backup/`)
- **Monthly**: Update Python packages
- **Quarterly**: Update Raspberry Pi OS

### Monitoring
```bash
# Service status
sudo systemctl status punchingbag

# Logs (last 50 lines)
sudo journalctl -u punchingbag -n 50

# Follow logs in real-time
sudo journalctl -u punchingbag -f

# Disk usage
df -h
du -sh data/characters/*
```

### Backup Strategy
```bash
# Database
cp data/punching_bag.db backups/punching_bag_$(date +%Y%m%d).db

# All characters
tar -czf backups/characters_$(date +%Y%m%d).tar.gz data/characters/

# Entire system
sudo dd if=/dev/mmcblk0 of=/path/to/backup.img bs=4M
```

---

## License

MIT License - See LICENSE file for details.
