#!/usr/bin/env python3
"""
Setup hit sound effects for the punching bag

Run this once to generate cinematic hit sounds using ElevenLabs Sound Effects API
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from services.hit_sounds import setup_hit_sounds

if __name__ == '__main__':
    load_dotenv()

    # Check API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found in .env")
        print("   Add your ElevenLabs API key to backend/.env")
        sys.exit(1)

    # Get data directory
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)

    print("\n" + "="*60)
    print("  Punching Bag - Hit Sound Effects Setup")
    print("="*60)
    print()
    print("This will generate 9 cinematic hit sound effects:")
    print("  • 3 light hits (20-50% force)")
    print("  • 3 medium hits (50-75% force)")
    print("  • 3 heavy hits (75-100% force)")
    print()
    print("These sounds are reused for all characters.")
    print("Generation takes ~30-60 seconds.")
    print()

    response = input("Generate hit sounds now? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)

    # Generate sounds
    setup_hit_sounds(str(data_dir))

    print("\n✅ Setup complete!")
    print()
    print("Next steps:")
    print("  1. Restart Flask server")
    print("  2. Create a character")
    print("  3. Start workout and select '💥 Hit Sounds' feedback mode")
    print()
