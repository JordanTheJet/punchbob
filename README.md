# Trash-Talking Punching Bag

AI-powered punching bag with personalized character rivals that trash talk based on punch strength.

## Features

- Create custom AI characters (boss, rival, ex, etc.)
- **Voice cloning**: Upload audio samples to clone any voice
- **3 feedback modes**: Voice grunts, cinematic hit sounds, or silent
- **Combo system**: Immediate feedback per punch, trash talk after combo
- 5 punch tiers (weak to max) with unique responses
- Offline workout mode (all responses pre-generated)
- Real-time statistics dashboard
- Fully runs on Raspberry Pi 2

## Quick Start

### Prerequisites

- Raspberry Pi 2/3/4/5
- **Accelerometer: GY-521 module (MPU-6050)**
- Speaker (USB or 3.5mm)
- Claude API key (for character generation)
- ElevenLabs API key (for voice generation)

### Installation

1. Flash Raspberry Pi OS Lite to microSD
2. Copy this entire folder to Pi: `/home/pi/punching-bag/`
3. Run setup script:
```bash
cd /home/pi/punching-bag
sudo bash scripts/setup.sh
```

4. Configure API keys:
```bash
nano backend/.env
# Add your keys:
# ANTHROPIC_API_KEY=your_key_here
# ELEVENLABS_API_KEY=your_key_here
```

5. Start services:
```bash
sudo systemctl start punchingbag
sudo systemctl start punchingbag-web
```

6. Access dashboard: `http://raspberrypi.local:5000`

## Project Structure

```
punching-bag/
├── backend/           # Python Flask API
│   ├── app.py         # Main API server
│   ├── services/      # Character generation, punch detection
│   ├── models/        # Database models
│   └── requirements.txt
├── frontend/          # React web dashboard
│   ├── src/
│   └── package.json
├── data/
│   ├── characters/    # Generated character audio files
│   └── punching_bag.db
└── scripts/           # Deployment and setup scripts
```

## Architecture

### Character Creation (One-time, requires internet)
1. User fills character form (name, personality, intensity)
2. Backend calls Claude API to generate 15 responses (5 tiers × 3 each)
3. Backend calls ElevenLabs to convert text → audio
4. Files stored locally: `/data/characters/{character_slug}/`

### Workout Mode (Fully offline)
1. Accelerometer detects punch force
2. System categorizes into tier 1-5
3. Selects random pre-generated audio for that tier
4. Plays instantly (<200ms latency)
5. Logs to database for statistics

## Voice Cloning

Upload audio samples to clone any voice for your characters! See [VOICE_CLONING.md](VOICE_CLONING.md) for detailed guide.

**Quick test:**
```bash
# Test voice cloning with sample audio
python3 scripts/test_voice_clone.py --file sample.mp3 --name "Test Voice"

# List available voices
python3 scripts/test_voice_clone.py --list
```

**In dashboard:**
1. Create New Rival → Select "Clone Voice from Sample"
2. Upload 30-60 second audio sample (MP3/WAV/M4A)
3. Name the voice and generate character

Perfect for cloning your actual boss, rival, or friend's voice!

## Feedback Modes

Choose how the bag responds to your punches:

**🎤 Voice Grunts (Default):**
- Character reacts with grunts/yelps to each punch
- Maximum immersion - feels like hitting the actual person
- Generated automatically during character creation

**💥 Hit Sounds:**
- Cinematic impact sounds like in video games
- Three intensity levels
- One-time setup required:
```bash
python3 scripts/setup_hit_sounds.py
```

**🔇 Silent:**
- No immediate feedback
- Character only speaks after combo ends
- Best for focusing on form

**Combo System:**
- Punches within 2 seconds = combo
- Immediate feedback on each hit
- Trash talk plays after combo ends

See [FEEDBACK_MODES.md](FEEDBACK_MODES.md) for detailed guide.

## Hardware Setup

### GY-521 (MPU-6050) Wiring
```
GY-521     →    Raspberry Pi
VCC        →    Pin 2 (5V) or Pin 1 (3.3V)  ⚡ Both work!
GND        →    Pin 6 (GND)
SDA        →    Pin 3 (GPIO 2)
SCL        →    Pin 5 (GPIO 3)
```

**Note**: The GY-521 module has an onboard voltage regulator, so it works with both 3.3V and 5V.

### Testing Sensor

After wiring, test the sensor:

```bash
cd /home/pi/punching-bag/scripts
python3 mpu6050_sensor.py --duration 30
```

You should see force readings. Hit the sensor to test!

Expected output at 0x68 when running:
```bash
i2cdetect -y 1
```

### Mounting
- Attach sensor to center back of punching bag
- Use foam padding for shock absorption
- Waterproof case recommended
- Orientation: Any axis perpendicular to striking surface

## Development

### Backend (Python)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

## Costs

- **Per character**: ~$0.08 (15 responses via Claude + ElevenLabs)
- **Storage**: ~300KB per character
- **Runtime**: $0 (fully offline)

## License

MIT
