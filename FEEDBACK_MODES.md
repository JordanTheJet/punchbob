# Feedback Modes & Combo System

## Overview

The punching bag now features:
- **3 feedback modes**: Choose how the bag responds to your punches
- **Combo detection**: Punches within 2 seconds are grouped together
- **Smart trash talk**: Character speaks after your combo ends

## Feedback Modes

### 🎤 Voice Grunts (Default)
**What it is:** Character's voice reacts to each punch with grunts, yelps, and impact sounds

**How it works:**
- Light punch (20-50%): "ugh", "oof", "ah"
- Medium punch (50-75%): "ungh!", "agh!", "ow!"
- Heavy punch (75-100%): "ARGH!", "UGH!", "OOF!"

**Best for:** Maximum immersion - feels like you're actually hitting the person

**Example flow:**
```
YOU: *light jab*
BAG: "ugh"
YOU: *medium cross*
BAG: "agh!"
YOU: *heavy hook*
BAG: "ARGH!"
[2 seconds pass]
BAG: "Is that all you got? My grandma hits harder!"
```

---

### 💥 Hit Sounds
**What it is:** Cinematic impact sound effects like in video games and movies

**How it works:**
- Light punch: Quick thud sound
- Medium punch: Powerful impact with echo
- Heavy punch: Explosive boom with bass

**Best for:** Gamers and action movie fans - feels like a fighting game

**Example flow:**
```
YOU: *quick jab-jab-cross combo*
BAG: *thud-thud-BOOM*
[2 seconds pass]
BAG: "Okay, now you're starting to annoy me!"
```

**Setup required:** Run once to generate sounds:
```bash
python3 scripts/setup_hit_sounds.py
```

---

### 🔇 Silent
**What it is:** No immediate feedback - only trash talk after combo ends

**How it works:**
- No sound during punches
- Character speaks only when you stop

**Best for:** Focus mode - concentrate on form, get roasted later

**Example flow:**
```
YOU: *rapid 6-punch combination*
BAG: [silent]
[2 seconds pass]
BAG: "Wow, you actually tried this time. Still weak, but I'll give you a participation trophy."
```

---

## Combo System

### How Combos Work

**Combo definition:** Multiple punches within 2 seconds of each other

**Combo detection:**
1. You throw a punch → immediate feedback plays
2. Timer starts (2 seconds)
3. You throw another punch → feedback plays, timer resets
4. After 2 seconds with no punches → combo ends, trash talk plays

**Trash talk tier:** Based on your **best punch** in the combo

### Example Scenarios

**Single Punch:**
```
YOU: *one hard punch*
BAG: "ARGH!" (grunt)
[2 seconds pass]
BAG: "That's it? One punch and you're done?"
```

**3-Punch Combo:**
```
YOU: punch → punch → punch (within 2 seconds)
BAG: feedback → feedback → feedback
[2 seconds pass]
BAG: "Nice combo! Too bad it tickled."
```

**Long Combo:**
```
YOU: 8 punches in 5 seconds
BAG: grunt → grunt → grunt → ... (8 times)
[2 seconds pass]
BAG: "Okay okay, I get it! You mad bro?"
```

### Combo Tips

- **Rapid fire:** Punch every 0.5-1 second to keep combo going
- **Pause for roast:** Wait 2+ seconds after combo to hear trash talk
- **Power finisher:** End combo with hardest punch for best tier trash talk
- **Reset timer:** Each punch resets the 2-second timer

---

## Changing Feedback Mode

### In-Workout

Select feedback mode **before** starting workout:
1. Go to character selection
2. Click on character to start workout
3. At top of workout screen, select mode from dropdown
4. Your preference is saved for next time

**Note:** Can't change mid-workout - must end and restart session

### Default Setting

The system remembers your last choice using browser localStorage. Your preference persists across sessions.

---

## Technical Details

### Latency Targets

- **Immediate feedback:** <200ms from punch to sound
- **Combo detection:** 2.0 seconds timeout (configurable)
- **Trash talk:** Plays immediately after timeout

### Audio Priorities

1. Feedback sounds (grunts/hits) can interrupt each other
2. Trash talk waits for combo to finish
3. Latest sound always plays (interrupts previous)

### Storage

**Voice grunts:**
- Stored per-character in `data/characters/{slug}/grunts/`
- Generated during character creation
- 9 files total (3 per level × 3 levels)

**Hit sounds:**
- Stored globally in `data/hit_sounds/`
- Shared across all characters
- Generated once via setup script
- 9 files total (3 per level × 3 levels)

---

## Frequently Asked Questions

**Q: Can I use different modes for different characters?**
A: No, feedback mode is a global preference. All characters use the same mode.

**Q: Can I change mode during workout?**
A: Not currently - must end workout and restart with new mode.

**Q: Why no sound on very light punches (<20% force)?**
A: Light taps don't trigger feedback to avoid constant noise. Punch harder!

**Q: Can I adjust the 2-second combo timeout?**
A: Yes, edit `combo_timeout` in `backend/services/punch_handler.py`

**Q: Do hit sounds use ElevenLabs credits?**
A: Yes, generation uses ElevenLabs Sound Effects API. But you only generate once, then reuse forever.

**Q: Can I replace hit sounds with my own?**
A: Yes! Add MP3 files to `data/hit_sounds/` with naming: `light_0.mp3`, `medium_1.mp3`, `heavy_2.mp3`, etc.

**Q: What happens if hit sounds aren't generated?**
A: Mode falls back to silent until you run `scripts/setup_hit_sounds.py`

---

## Best Practices

### For Maximum Immersion
- Use **🎤 Voice Grunts** mode
- Create characters with intense personalities
- Clone voices of actual people you know

### For Gaming Experience
- Use **💥 Hit Sounds** mode
- Create competitive rival characters
- Focus on combo chains

### For Serious Training
- Use **🔇 Silent** mode
- Focus on form and technique
- Get feedback between sets via trash talk

### For Comedy
- Use **🎤 Voice Grunts** mode
- Create characters with hilarious personalities
- Do rapid-fire combos for maximum chaos

---

Enjoy your enhanced punching bag experience! 🥊
