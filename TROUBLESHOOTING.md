# Troubleshooting Guide

## Common Issues & Fixes

### Issue: "undefined" appears as punch text

**Symptom:** When testing punches with old characters, you see "undefined" displayed.

**Cause:** Old characters created before the grunt feature don't have grunt sounds.

**Fix:**
1. **Best solution:** Recreate the character (will include grunts)
2. **Quick workaround:** Use "💥 Hit Sounds" or "🔇 Silent" mode instead
3. **Ignore it:** The audio still plays correctly, just the text display is affected

**Server logs will show:**
```
⚠️  Warning: This character has no grunt sounds (created before grunt feature)
   Fallback: Voice grunts mode will work silently
```

---

### Issue: "An invalid form control is not focusable" error

**Symptom:** When creating a character with preset voice, form won't submit and shows console error about consent checkbox.

**Cause:** Consent checkbox was incorrectly set to `required` for all modes.

**Fix:** Already fixed! Consent checkbox is now only validated when actually in clone mode.

**Workaround (if using old version):**
- Switch to "Clone Voice from Sample" mode
- Check the consent box
- Switch back to "Use Preset Voice"
- Submit form

---

### Issue: No grunt sounds playing

**Symptom:** Selected "🎤 Voice Grunts" but no sounds play on punches.

**Possible causes:**

**1. Old character (most common)**
- Character created before grunt feature
- Solution: Recreate the character

**2. Audio playback issue**
- Check browser console for errors
- Verify audio files exist: `data/characters/{character_slug}/grunts/`
- Test with a different browser

**3. Force too low**
- Punches under 20% force don't trigger feedback
- Solution: Punch harder or adjust threshold

**To verify grunts exist:**
```bash
ls -la data/characters/*/grunts/
```

Should show 9 files per character (light_0.mp3 through heavy_2.mp3)

---

### Issue: Hit sounds mode not working

**Symptom:** Selected "💥 Hit Sounds" but no sounds play.

**Cause:** Hit sounds not generated yet (one-time setup required).

**Fix:**
```bash
cd "/Users/jordantian/Documents/Sundai_hacks/Hardware 11-23/punching-bag"
python3 scripts/setup_hit_sounds.py
```

**Verify hit sounds exist:**
```bash
ls -la data/hit_sounds/
```

Should show 9 files (light_0.mp3 through heavy_2.mp3)

**If still not working:**
- Check ElevenLabs API key in `.env`
- Check console for errors
- Restart Flask server after generation

---

### Issue: Trash talk not playing after combo

**Symptom:** Grunts/hits play, but no trash talk after stopping.

**Causes:**

**1. Combo timeout too short**
- Need to wait full 2 seconds
- Solution: Be patient, or adjust timeout in code

**2. Character has no responses**
- Check character was created successfully
- Verify: `ls data/characters/{slug}/responses/`

**3. Audio already playing**
- Audio player interrupts previous sounds
- Wait for current sound to finish

---

### Issue: Character creation fails with voice cloning

**Symptom:** Error during "Cloning voice from sample..." step.

**Common causes:**

**1. No consent checkbox checked**
- Must check consent box when cloning
- Fix: Check the box before submitting

**2. Audio file format not supported**
- Use MP3, WAV, or M4A
- Convert with: `ffmpeg -i input.mov -acodec libmp3lame output.mp3`

**3. File too large**
- ElevenLabs limit: ~10MB
- Solution: Compress audio or trim to 30-60 seconds

**4. ElevenLabs API error**
- Check API key is valid
- Check you haven't hit voice cloning limit (free tier: 3 clones)
- Check internet connection

**5. Poor audio quality**
- Too much background noise
- Solution: Record in quiet environment

---

### Issue: Combo detection not working

**Symptom:** Each punch plays trash talk immediately instead of grouping into combo.

**Cause:** This shouldn't happen with current version.

**Debug:**
1. Check console logs: `Combo ended: X punches...`
2. Verify server logs show combo detection
3. Check if you're punching slower than 2 seconds apart

**Fix:** Punch more rapidly (under 2 second intervals)

---

### Issue: Feedback mode doesn't persist

**Symptom:** Mode resets to default on each new session.

**Cause:** Browser localStorage not working or disabled.

**Fix:**
1. Check browser allows localStorage
2. Check not in private/incognito mode
3. Manually select mode each session (will work, just won't save)

---

### Issue: mpg123 not found error

**Symptom:** Server logs show `mpg123 not found` or audio doesn't play.

**Cause:** Audio player `mpg123` not installed.

**Fix (macOS):**
```bash
brew install mpg123
```

**Fix (Raspberry Pi):**
```bash
sudo apt-get update
sudo apt-get install mpg123
```

**Workaround:** Audio generation still works, just playback won't work until installed.

---

### Issue: Port already in use

**Symptom:** `Address already in use` error when starting server.

**Cause:** Another process using port 8080.

**Fix:**
1. Find process: `lsof -i :8080`
2. Kill it: `kill -9 <PID>`
3. Or use different port in `.env`: `PORT=8081`

---

### Issue: Character generation takes forever

**Symptom:** Stuck at "Generating audio X/24..."

**Causes:**

**1. ElevenLabs API slow**
- Normal: 60-90 seconds for full character
- Solution: Be patient

**2. API rate limiting**
- Creating too many characters too fast
- Solution: Wait a few minutes, try again

**3. Network timeout**
- Check internet connection
- Check ElevenLabs status page

**If hung for 5+ minutes:**
- Cancel (Ctrl+C server)
- Check logs for specific error
- Try again with simpler character

---

## Getting More Help

**Check logs:**
```bash
# Server terminal shows detailed logs
# Look for errors, warnings, or stack traces
```

**Test components individually:**
```bash
# Test voice cloning
python3 scripts/test_voice_clone.py --list

# Test hit sound generation
python3 scripts/setup_hit_sounds.py

# Test character creation
# (Use web UI with console open)
```

**Report bugs:**
- Include server logs
- Include browser console errors
- Describe exact steps to reproduce
- Mention OS and Python version

---

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| "undefined" text | Use hit sounds mode or recreate character |
| No grunts | Recreate character |
| No hit sounds | Run `setup_hit_sounds.py` |
| Consent error | Already fixed in latest version |
| No trash talk | Wait 2+ seconds after combo |
| Audio not playing | Install mpg123 |
| Slow creation | Normal, wait 60-90 seconds |

---

## Need Help?

Check these docs:
- [FEEDBACK_MODES.md](FEEDBACK_MODES.md) - How feedback modes work
- [VOICE_CLONING.md](VOICE_CLONING.md) - Voice cloning guide
- [WHATS_NEW.md](WHATS_NEW.md) - Recent changes & migration
- [README.md](README.md) - General setup

Still stuck? Check the GitHub issues page.
