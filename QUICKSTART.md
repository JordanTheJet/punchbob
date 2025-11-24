# Quick Start Guide

## Local Testing (Without Raspberry Pi)

### 1. Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
nano .env
```

Add your keys:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
ELEVENLABS_API_KEY=...
```

### 3. Test Character Generation

```bash
cd backend
python3 services/character_generator.py
```

This will create a test character called "Coach" with 15 responses.

### 4. Test Punch Handler

```bash
python3 services/punch_handler.py
```

This simulates a 10-punch workout session.

### 5. Start Backend Server

```bash
python3 app.py
```

Server runs on `http://localhost:5000`

### 6. Open Frontend

Open `frontend/index.html` in your browser, or use:

```bash
# Serve with Python
cd frontend
python3 -m http.server 8000
```

Then visit: `http://localhost:8000`

---

## Raspberry Pi Deployment

### 1. Copy Files to Pi

```bash
# From your computer:
scp -r punching-bag/ pi@raspberrypi.local:/home/pi/
```

### 2. SSH into Pi

```bash
ssh pi@raspberrypi.local
```

### 3. Run Setup Script

```bash
cd /home/pi/punching-bag
sudo bash scripts/setup.sh
```

This will:
- Install system dependencies (Python, mpg123, nginx, i2c-tools)
- Create Python virtual environment
- Install Python packages
- Setup systemd service
- Configure nginx
- Enable I2C interface

### 4. Configure API Keys

```bash
nano backend/.env
```

Add your keys, then restart:

```bash
sudo systemctl restart punchingbag
```

### 5. Connect Accelerometer

Wire ADXL345 to Raspberry Pi:

```
ADXL345    →    Raspberry Pi
VCC (3.3V) →    Pin 1 (3.3V)
GND        →    Pin 6 (GND)
SDA        →    Pin 3 (GPIO 2)
SCL        →    Pin 5 (GPIO 3)
```

### 6. Test Sensor

```bash
cd /home/pi/punching-bag/scripts
python3 sensor_test.py --duration 30
```

Hit the sensor to see force readings!

### 7. Access Dashboard

Find your Pi's IP:
```bash
hostname -I
```

Open in browser:
- `http://192.168.x.x` (your Pi's IP)
- or `http://raspberrypi.local`

---

## Usage

### Create Your First Character

1. Click **"+ Create New Rival"**
2. Fill in:
   - Name: "Boss Steve"
   - Relationship: Boss
   - Personality: "arrogant, condescending"
   - Intensity: 3/5
3. Click **"Generate Character"**
4. Wait ~45 seconds (15 responses)

### Start Workout

1. Click on a character card
2. Workout screen opens
3. Click **"Simulate Punch"** to test
4. Or punch the bag if sensor connected!

### View Statistics

- Each character card shows total sessions
- Click character → detailed stats

---

## Troubleshooting

### "Character generation failed"

- Check API keys in `backend/.env`
- Verify internet connection
- Check backend logs: `sudo journalctl -u punchingbag -f`

### "No audio playing"

- Install mpg123: `sudo apt-get install mpg123`
- Check speaker connection
- Test: `mpg123 /path/to/audio.mp3`

### "Sensor not detected"

- Check wiring (3.3V, not 5V!)
- Enable I2C: `sudo raspi-config` → Interface → I2C → Enable
- Test: `i2cdetect -y 1` (should show device at 0x53)

### "Service not starting"

```bash
# Check status
sudo systemctl status punchingbag

# View logs
sudo journalctl -u punchingbag -n 50

# Restart
sudo systemctl restart punchingbag
```

### "Frontend not loading"

- Check nginx: `sudo systemctl status nginx`
- Check nginx config: `sudo nginx -t`
- Restart nginx: `sudo systemctl restart nginx`

---

## File Structure Reference

```
punching-bag/
├── backend/
│   ├── app.py                    # Flask API server
│   ├── database.py               # SQLite database layer
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # API keys (create from .env.example)
│   └── services/
│       ├── character_generator.py  # Claude + ElevenLabs integration
│       └── punch_handler.py        # Real-time punch processing
│
├── frontend/
│   ├── index.html                # Main UI
│   ├── css/style.css             # Styling
│   └── js/app.js                 # Frontend logic
│
├── data/
│   ├── punching_bag.db           # SQLite database
│   └── characters/               # Character audio files
│       ├── boss_steve/
│       │   └── responses/
│       │       ├── tier1_001.mp3
│       │       └── ...
│
└── scripts/
    ├── setup.sh                  # Pi setup script
    └── sensor_test.py            # Test accelerometer
```

---

## Next Steps

### Add More Characters

- Create 3-5 characters with different personalities
- Experiment with intensity levels (1-5)
- Try different voice styles

### Hardware Integration

- Connect real accelerometer
- Mount on punching bag with foam padding
- Run `sensor_test.py` to calibrate thresholds

### Scaling Up

- Increase responses per character (15 → 30 → 60)
- Edit `backend/.env`: `RESPONSES_PER_TIER=6` for 30 total
- Regenerate characters for more variety

### Advanced Features

- Add multiple user profiles
- Track progress over time
- Build combo detection
- Add achievements system

---

## Cost Tracking

### Per Character (15 responses):
- Claude API: ~$0.001
- ElevenLabs TTS: ~$0.08
- **Total: ~$0.08 per character**

### Budget for 20 characters: ~$1.60

Very affordable for testing! Scale up later.

---

## Support

- Issues: Create GitHub issue
- Sensor help: See `README.md` hardware section
- API issues: Check provider documentation
  - Claude: https://docs.anthropic.com
  - ElevenLabs: https://docs.elevenlabs.io
