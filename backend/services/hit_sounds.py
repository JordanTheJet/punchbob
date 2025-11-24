"""
Hit sound effects generator for punch feedback

Provides 3 feedback modes:
1. Voice grunts (character's voice)
2. Hit sound effects (game/movie style impacts)
3. Silent (trash talk only)
"""

import os
import random
from pathlib import Path
from typing import Dict, List, Optional
from elevenlabs.client import ElevenLabs


class HitSoundGenerator:
    """Generate cinematic hit sound effects using ElevenLabs Sound Effects API"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.elevenlabs = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

    def generate_hit_sounds(self) -> Dict[str, List[str]]:
        """
        Generate 3 levels of hit sound effects

        Returns dict with paths to generated sounds:
        {
            'light': [path1, path2, path3],
            'medium': [path1, path2, path3],
            'heavy': [path1, path2, path3]
        }
        """
        sounds_dir = Path(self.data_dir) / 'hit_sounds'
        sounds_dir.mkdir(parents=True, exist_ok=True)

        # Sound effect prompts for ElevenLabs
        sound_prompts = {
            'light': [
                'light punch impact sound, quick thud',
                'soft boxing glove hitting bag',
                'gentle thump sound effect'
            ],
            'medium': [
                'powerful punch impact with echo',
                'boxing glove heavy hit sound',
                'strong thud with vibration'
            ],
            'heavy': [
                'massive punch impact, dramatic whoosh and boom',
                'cinematic knockout punch sound',
                'explosive boxing hit with deep bass'
            ]
        }

        generated_files = {
            'light': [],
            'medium': [],
            'heavy': []
        }

        for level, prompts in sound_prompts.items():
            for i, prompt in enumerate(prompts):
                filename = f"{level}_{i}.mp3"
                filepath = sounds_dir / filename

                # Check if already exists
                if filepath.exists():
                    print(f"  Using cached: {filename}")
                    generated_files[level].append(str(filepath))
                    continue

                try:
                    print(f"  Generating: {filename}")

                    # Generate sound effect using ElevenLabs
                    audio = self.elevenlabs.text_to_sound_effects.convert(
                        text=prompt,
                        duration_seconds=0.5,
                        prompt_influence=0.5
                    )

                    # Save to file
                    with open(filepath, 'wb') as f:
                        f.write(b''.join(audio))

                    generated_files[level].append(str(filepath))

                except Exception as e:
                    print(f"  Warning: Could not generate {filename}: {e}")
                    # Use a placeholder or skip

        return generated_files


class HitSoundPlayer:
    """Manages playback of hit sound effects"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.sounds_dir = Path(data_dir) / 'hit_sounds'

        # Load available sounds
        self.sound_cache = self._load_sounds()

    def _load_sounds(self) -> Dict[str, List[str]]:
        """Load all available hit sounds from disk"""
        cache = {'light': [], 'medium': [], 'heavy': []}

        if not self.sounds_dir.exists():
            print("Warning: No hit sounds directory found")
            return cache

        for level in ['light', 'medium', 'heavy']:
            for filepath in self.sounds_dir.glob(f"{level}_*.mp3"):
                cache[level].append(str(filepath))

        total = sum(len(v) for v in cache.values())
        print(f"Loaded {total} hit sound effects")
        return cache

    def get_sound(self, force_pct: float) -> Optional[str]:
        """Select appropriate hit sound based on punch force"""
        if force_pct < 50:
            level = 'light'
        elif force_pct < 75:
            level = 'medium'
        else:
            level = 'heavy'

        candidates = self.sound_cache.get(level, [])
        if not candidates:
            return None

        return random.choice(candidates)


def setup_hit_sounds(data_dir: str = '../data'):
    """One-time setup to generate hit sound effects"""
    print("=" * 50)
    print("Hit Sound Effects Setup")
    print("=" * 50)

    generator = HitSoundGenerator(data_dir)

    print("\nGenerating hit sound effects...")
    print("(This uses ElevenLabs Sound Effects API)")

    sounds = generator.generate_hit_sounds()

    print("\n✅ Hit sounds generated:")
    for level, files in sounds.items():
        print(f"  {level}: {len(files)} sounds")

    print("\n💡 Tip: These sounds are cached and reused for all characters")
    print("=" * 50)


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else '../data'

    setup_hit_sounds(data_dir)
