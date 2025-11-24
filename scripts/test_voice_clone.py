#!/usr/bin/env python3
"""
Test voice cloning functionality with ElevenLabs API
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from elevenlabs.client import ElevenLabs

def test_voice_clone(audio_file_path: str, voice_name: str = "Test Clone"):
    """
    Test cloning a voice from an audio file

    Args:
        audio_file_path: Path to audio file (MP3, WAV, M4A)
        voice_name: Name for the cloned voice
    """
    load_dotenv()

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found in .env")
        return

    print(f"Testing voice cloning with ElevenLabs...")
    print(f"  Audio file: {audio_file_path}")
    print(f"  Voice name: {voice_name}")

    # Check file exists
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return

    # Initialize client
    client = ElevenLabs(api_key=api_key)

    try:
        print("\n🎤 Uploading and cloning voice...")

        # Clone voice using Instant Voice Cloning (IVC)
        # Need to pass file object, not path
        with open(audio_file_path, 'rb') as audio_file:
            voice = client.voices.ivc.create(
                name=voice_name,
                files=[audio_file]
            )

        print(f"✅ Voice cloned successfully!")
        print(f"   Voice ID: {voice.voice_id}")
        print(f"   Voice Name: {voice.name}")

        # Test generating audio with cloned voice
        print(f"\n🔊 Testing audio generation with cloned voice...")

        test_text = "Hey there! This is a test of the cloned voice."

        audio = client.text_to_speech.convert(
            text=test_text,
            voice_id=voice.voice_id,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_22050_32"
        )

        # Save test audio
        test_output = Path(__file__).parent.parent / 'data' / 'test_clone.mp3'
        test_output.parent.mkdir(exist_ok=True)

        with open(test_output, 'wb') as f:
            f.write(b''.join(audio))

        print(f"✅ Test audio generated: {test_output}")
        print(f"   Play it with: mpg123 {test_output}")

        # Clean up - delete the cloned voice (optional)
        print(f"\n🗑️  Cleaning up test voice...")
        client.voices.delete(voice.voice_id)
        print(f"✅ Test voice deleted")

        print("\n" + "="*50)
        print("✅ Voice cloning test PASSED!")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Error during voice cloning test:")
        print(f"   {str(e)}")
        print("\nPossible issues:")
        print("  - Invalid API key")
        print("  - Audio file format not supported")
        print("  - File too large (>10MB)")
        print("  - Hit ElevenLabs voice cloning limit")
        print("  - Network connection issue")


def list_current_voices():
    """List all voices currently in ElevenLabs account"""
    load_dotenv()

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found in .env")
        return

    client = ElevenLabs(api_key=api_key)

    try:
        print("\n📋 Current voices in your account:")
        print("-" * 50)

        voices = client.voices.get_all()

        for voice in voices.voices:
            print(f"  • {voice.name}")
            print(f"    ID: {voice.voice_id}")
            print(f"    Category: {voice.category if hasattr(voice, 'category') else 'N/A'}")
            print()

        print(f"Total: {len(voices.voices)} voices")

    except Exception as e:
        print(f"❌ Error listing voices: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test ElevenLabs voice cloning')
    parser.add_argument('--file', '-f', help='Audio file to clone (MP3, WAV, M4A)')
    parser.add_argument('--name', '-n', default='Test Clone', help='Name for cloned voice')
    parser.add_argument('--list', '-l', action='store_true', help='List current voices')

    args = parser.parse_args()

    if args.list:
        list_current_voices()
    elif args.file:
        test_voice_clone(args.file, args.name)
    else:
        print("Voice Cloning Test Utility")
        print("=" * 50)
        print("\nUsage:")
        print("  Test cloning:    python3 test_voice_clone.py --file sample.mp3 --name 'Test Voice'")
        print("  List voices:     python3 test_voice_clone.py --list")
        print("\nNote: Test cloning will create and then delete a test voice.")
