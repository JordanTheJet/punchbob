# Voice Cloning Feature

## Overview

You can now create characters with **cloned voices** using your own audio samples! This makes the trash-talking even more personal and realistic.

## How It Works

1. **Record a Voice Sample**
   - Get a 30-60 second audio recording of the person speaking naturally
   - Quality matters: Clear audio with minimal background noise works best
   - Supported formats: MP3, WAV, M4A, OGG

2. **Create Character with Clone**
   - Go to "Create New Rival"
   - Select "Clone Voice from Sample" under Voice Option
   - Upload your audio file
   - Give the voice a name (e.g., "Steve's Real Voice")
   - Fill out the rest of the character details
   - Click "Generate Character"

3. **Voice Gets Cloned**
   - The system uses ElevenLabs Voice Cloning API
   - Creates a custom voice model from your sample
   - Uses this cloned voice for all 15 trash talk responses
   - Voice is saved and reusable for future characters

## Tips for Best Results

### Recording Quality
- **Environment**: Record in a quiet room with minimal echo
- **Microphone**: Use a decent mic (even phone mic works)
- **Distance**: Stay consistent distance from mic
- **Background**: Avoid music, TV, traffic noise

### Content
- **Natural speech**: Have person speak conversationally
- **Variety**: Include different tones (normal, excited, questioning)
- **Emotion**: Some emotional range helps capture voice personality
- **Avoid**: Yelling, whispering, or exaggerated voices

### Audio File
- **Length**: 30-60 seconds ideal (minimum 10 seconds)
- **Format**: MP3 recommended (WAV, M4A also work)
- **Quality**: At least 128 kbps bitrate
- **File size**: Keep under 10MB

## Example Recording Script

Have the person read this naturally:

> "Hey, how's it going? I wanted to talk to you about something interesting I discovered recently. You know how sometimes you try really hard at something and it just clicks? Well, that happened to me last week. I was working on this project, and after days of struggling, everything suddenly made sense. It felt amazing! Have you ever had that experience? Anyway, I'm really excited to share more about it with you."

This script includes:
- Casual greeting
- Questions (natural tone variation)
- Emotional words (excited, amazing)
- Complete sentences with natural pauses

## Limitations

- ElevenLabs free tier: 10 cloned voices max
- Voice cloning requires internet connection
- First-time cloning takes ~30-60 seconds
- Quality depends on sample audio quality

## Privacy Notes

- Audio samples are sent to ElevenLabs for processing
- Samples are deleted from our server after cloning
- Cloned voices are stored in your ElevenLabs account
- You can delete cloned voices via ElevenLabs dashboard

## Preset Voices vs Cloned Voices

| Feature | Preset Voices | Cloned Voices |
|---------|--------------|---------------|
| Setup time | Instant | 30-60 seconds |
| Quality | Professional | Depends on sample |
| Cost | Free | Uses ElevenLabs quota |
| Personalization | Generic | Highly personal |
| Internet required | Only during generation | During generation + cloning |

## Troubleshooting

**"Voice cloning failed"**
- Check audio file format (MP3/WAV/M4A)
- Ensure file is under 10MB
- Verify ElevenLabs API key is valid
- Check you haven't hit voice cloning limit

**"Cloned voice sounds wrong"**
- Recording may have too much background noise
- Sample might be too short (under 10 seconds)
- Try recording in a quieter environment
- Ensure person speaks naturally (not reading robotically)

**"Upload button not working"**
- Check file format is supported
- Try converting to MP3 if using unusual format
- Ensure file isn't corrupted

## Advanced: Manage Cloned Voices

View all your cloned voices:
```bash
python3 scripts/list_voices.py
```

This shows all voices in your ElevenLabs account with their IDs, including cloned ones.

## Use Cases

- **Boss Mode**: Record your actual boss for maximum realism
- **Ex Mode**: Clone an ex's voice for cathartic punching
- **Coach Mode**: Use a real coach/trainer's voice
- **Friend Mode**: Record a trash-talking friend
- **Celebrity Impressions**: Use impressionist recordings (for personal use)
- **Custom Characters**: Create fictional character voices

## API Permissions & Requirements

### Subscription Requirements

Voice cloning is available on all ElevenLabs tiers:
- **Free Tier**: Up to 3 instant voice clones
- **Starter+**: 10+ instant voice clones
- **Pro/Scale**: Unlimited + professional voice cloning

This project uses **Instant Voice Cloning** via API, which works on all plans.

### API Access

No special API permissions needed! If your ElevenLabs API key works for text-to-speech, it automatically works for voice cloning.

**Note:** This uses **Instant Voice Cloning (IVC)** which works from 30+ second samples.

**Check your plan:**
```bash
python3 scripts/test_voice_clone.py --list
```

If you see existing voices, your API key has voice cloning access.

**API Method Used:** `client.voices.ivc.create()` (Instant Voice Cloning)

## Legal & Ethical Considerations

⚠️ **Important**: Only clone voices with **explicit permission** from the person. Voice cloning for impersonation or harassment is unethical and potentially illegal.

### ElevenLabs Policy

By using voice cloning, you confirm that you:
- Have obtained explicit consent from the voice owner
- Have legal rights to use the voice recordings
- Will not use the cloned voice for harmful purposes
- Accept responsibility for compliance with local laws

**The consent checkbox in the UI is required** - this helps ensure compliance with ElevenLabs terms of service.

### Good Use Cases
- Your own voice
- Friends/family who gave permission
- Your own vocal impressions/characters
- Public domain recordings

### Bad Use Cases
- Anyone without explicit consent
- Celebrities (unless for personal use only)
- Impersonation for malicious purposes
- Commercial use without rights

### Account Risks

Violating ElevenLabs' consent policy can result in:
- Account suspension or termination
- Loss of API access
- Legal liability

---

Have fun creating hyper-personalized trash-talking rivals! 🥊🎤
