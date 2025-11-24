import os
import json
import time
from pathlib import Path
from typing import Dict, List, Generator
from anthropic import Anthropic
from elevenlabs.client import ElevenLabs
from database import Database

class CharacterGenerator:
    """Generates AI characters with personalized trash talk using Claude + ElevenLabs"""

    def __init__(self, db: Database, data_dir: str):
        self.db = db
        self.data_dir = data_dir
        self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.elevenlabs = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

        # Voice mapping for different character types
        # Using common ElevenLabs voice IDs (these are example IDs - update with your account's voices)
        self.voice_map = {
            'aggressive_male': 'pNInz6obpgDQGcFmaJgB',  # Adam
            'sarcastic_female': 'EXAVITQu4vr4xnSDxMaL',  # Sarah
            'playful_male': 'TxGEqnHWrfWFTfGW9XjX',  # Josh
            'stern_boss': 'VR6AewLTigWG4xSOukaG',  # Arnold
            'cheerful_coach': '21m00Tcm4TlvDq8ikWAM',  # Rachel
            'default': 'pNInz6obpgDQGcFmaJgB'  # Adam (default)
        }

    def generate_character(self, character_data: Dict) -> Generator[Dict, None, None]:
        """
        Main pipeline: Character data → LLM responses → TTS audio → Storage

        Yields progress updates for real-time UI feedback
        """
        start_time = time.time()

        # Step 0: Handle voice cloning if needed
        voice_id = None
        if character_data.get('voice_mode') == 'clone':
            yield {"status": "cloning_voice", "progress": 3, "message": "Cloning voice from sample..."}
            try:
                voice_id = self._clone_voice(character_data)
                print(f"✅ Voice cloned successfully! Voice ID: {voice_id}")
                yield {"status": "voice_cloned", "progress": 8, "message": f"Voice cloned: {voice_id}"}
            except Exception as e:
                print(f"❌ Voice cloning failed: {str(e)}")
                print(f"   Falling back to default voice")
                yield {"status": "voice_clone_failed", "progress": 8, "message": f"Clone failed, using default voice"}
                voice_id = self._get_voice_id({'voice_style': 'default'})
        else:
            voice_id = self._get_voice_id(character_data)
            print(f"Using preset voice ID: {voice_id}")

        # Step 1: Create character record
        yield {"status": "creating", "progress": 10, "message": "Creating character..."}

        slug = self._slugify(character_data['name'])
        character_id = self.db.create_character(
            name=character_data['name'],
            slug=slug,
            description=character_data.get('description', ''),
            relationship=character_data.get('relationship', 'rival'),
            personality=character_data.get('personality', 'competitive'),
            intensity=character_data.get('intensity', 3),
            voice_id=voice_id
        )

        # Create character directory
        char_dir = Path(self.data_dir) / 'characters' / slug
        char_dir.mkdir(parents=True, exist_ok=True)
        (char_dir / 'responses').mkdir(exist_ok=True)
        (char_dir / 'grunts').mkdir(exist_ok=True)

        yield {"status": "character_created", "progress": 10, "character_id": character_id}

        # Step 2: Generate responses via Claude
        yield {"status": "generating_responses", "progress": 15, "message": "Generating trash talk..."}

        responses = self._generate_responses_llm(character_data)

        yield {"status": "responses_generated", "progress": 40, "message": f"Generated {len(responses)} responses"}

        # Step 3: Convert to audio via ElevenLabs
        yield {"status": "generating_audio", "progress": 45, "message": "Creating voice audio..."}

        voice_id = self._get_voice_id(character_data)
        audio_files = []

        for i, response in enumerate(responses):
            # Progress update
            audio_progress = 45 + int((i / len(responses)) * 45)
            yield {
                "status": "generating_audio",
                "progress": audio_progress,
                "message": f"Generating audio {i+1}/{len(responses)}..."
            }

            # Generate audio
            audio_data = self._generate_audio(response['text'], voice_id)

            # Save audio file
            filename = f"tier{response['tier']}_{i % 3:03d}.mp3"
            audio_path = char_dir / 'responses' / filename

            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            # Store in database
            self.db.create_response(
                character_id=character_id,
                tier=response['tier'],
                text=response['text'],
                audio_path=str(audio_path),
                duration_ms=response.get('duration_ms', 2500)
            )

            audio_files.append(str(audio_path))

        yield {"status": "audio_complete", "progress": 90, "message": "Audio generated"}

        # Step 4: Generate grunt sounds
        yield {"status": "generating_grunts", "progress": 92, "message": "Creating grunt sounds..."}
        grunt_files = self._generate_grunts(character_id, slug, voice_id, char_dir)
        yield {"status": "grunts_complete", "progress": 95, "message": f"Generated {len(grunt_files)} grunt sounds"}

        # Step 5: Finalize
        elapsed = time.time() - start_time
        yield {
            "status": "completed",
            "progress": 100,
            "character_id": character_id,
            "slug": slug,
            "message": f"Character created in {elapsed:.1f}s",
            "audio_files": len(audio_files)
        }

    def _generate_responses_llm(self, character_data: Dict) -> List[Dict]:
        """Use Claude to generate personalized trash talk responses"""

        prompt = self._build_prompt(character_data)

        response = self.anthropic.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast and cheap
            max_tokens=2000,
            temperature=0.9,  # High creativity
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse JSON response
        response_text = response.content[0].text

        # Extract JSON from response (Claude sometimes adds markdown)
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()

        data = json.loads(response_text)
        return data['responses']

    def _build_prompt(self, character_data: Dict) -> str:
        """Build Claude prompt for response generation"""

        name = character_data['name']
        relationship = character_data.get('relationship', 'rival')
        personality = character_data.get('personality', 'competitive, trash-talking')
        intensity = character_data.get('intensity', 3)
        description = character_data.get('description', '')

        intensity_desc = {
            1: "playful and friendly, mostly encouraging",
            2: "lightly teasing but supportive",
            3: "competitive trash talk with some edge",
            4: "harsh and cutting, minimal encouragement",
            5: "brutal and relentless, zero mercy"
        }.get(intensity, "competitive")

        prompt = f"""You are creating trash talk responses for a smart punching bag system.

CHARACTER PROFILE:
- Name: {name}
- Relationship to user: {relationship}
- Personality: {personality}
- Intensity level: {intensity}/5 ({intensity_desc})
{f'- Additional context: {description}' if description else ''}

TASK: Generate exactly 15 unique trash talk responses across 5 punch strength tiers (3 per tier).

TIER DEFINITIONS:
- Tier 1 (Weak): 0-20% of max force - highly mocking, disappointed
- Tier 2 (Light): 20-40% - moderately mocking with some encouragement
- Tier 3 (Medium): 40-60% - acknowledge effort but still challenging
- Tier 4 (Hard): 60-85% - showing respect while staying in character
- Tier 5 (Maximum): 85-100% - genuine reaction, impressed or shocked

REQUIREMENTS:
- Keep responses under 15 words (2-3 seconds of audio)
- Stay in character voice and personality
- Be funny and motivating, never genuinely hurtful
- Vary vocabulary (no repetitive phrases)
- Match the intensity level ({intensity}/5)
- Responses should feel like {name} is actually talking

OUTPUT FORMAT (JSON):
{{
    "responses": [
        {{"tier": 1, "text": "Is that a warm-up tap?"}},
        {{"tier": 1, "text": "My grandma hits harder than that."}},
        {{"tier": 1, "text": "Did you just punch me or sneeze?"}},
        ...
        {{"tier": 5, "text": "WHOA! Okay, you got my attention now!"}},
        {{"tier": 5, "text": "Where did THAT come from?! Do it again!"}}
    ]
}}

Generate 15 responses now (3 per tier, tiers 1-5):"""

        return prompt

    def _generate_grunts(self, character_id: int, slug: str, voice_id: str, char_dir: Path) -> list:
        """
        Generate grunt/impact sounds for immediate punch feedback

        Creates 3 grunt levels:
        - Light (20-50% force): "ugh", "oof"
        - Medium (50-75% force): "ungh!", "agh!"
        - Heavy (75%+ force): "ARGH!", "UGH!"
        """
        grunt_texts = {
            'light': ['ugh', 'oof', 'ah'],
            'medium': ['ungh!', 'agh!', 'ow!'],
            'heavy': ['ARGH!', 'UGH!', 'OOF!']
        }

        grunt_files = []

        for level, texts in grunt_texts.items():
            for i, text in enumerate(texts):
                # Generate audio
                audio_data = self._generate_audio(text, voice_id)

                # Save audio file
                filename = f"{level}_{i}.mp3"
                audio_path = char_dir / 'grunts' / filename

                with open(audio_path, 'wb') as f:
                    f.write(audio_data)

                # Store in database with negative tier to distinguish from trash talk
                # light=-1, medium=-2, heavy=-3
                tier = -(list(grunt_texts.keys()).index(level) + 1)

                self.db.create_response(
                    character_id=character_id,
                    tier=tier,
                    text=text,
                    audio_path=str(audio_path),
                    duration_ms=500  # Grunts are short
                )

                grunt_files.append(str(audio_path))

        return grunt_files

    def _generate_audio(self, text: str, voice_id: str) -> bytes:
        """Convert text to speech using ElevenLabs"""

        audio = self.elevenlabs.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_turbo_v2_5",  # Fastest model
            output_format="mp3_22050_32"  # Optimized for voice, smaller files
        )

        # Convert generator to bytes
        audio_bytes = b''.join(audio)
        return audio_bytes

    def _clone_voice(self, character_data: Dict) -> str:
        """
        Clone a voice from uploaded audio sample using ElevenLabs Instant Voice Cloning API

        Returns: voice_id of the newly cloned voice
        """
        sample_path = character_data.get('voice_sample_path')
        voice_name = character_data.get('clone_voice_name', 'Cloned Voice')

        print(f"🎤 Voice cloning request:")
        print(f"   Sample path: {sample_path}")
        print(f"   Voice name: {voice_name}")
        print(f"   File exists: {os.path.exists(sample_path) if sample_path else False}")

        if not sample_path or not os.path.exists(sample_path):
            raise ValueError(f"Voice sample file not found: {sample_path}")

        # Check file size
        file_size = os.path.getsize(sample_path)
        print(f"   File size: {file_size / 1024:.1f} KB")

        # Use ElevenLabs Instant Voice Cloning (IVC)
        # https://elevenlabs.io/docs/cookbooks/voices/instant-voice-cloning
        # Need to pass file objects, not paths
        print(f"   Uploading to ElevenLabs IVC...")
        with open(sample_path, 'rb') as audio_file:
            voice = self.elevenlabs.voices.ivc.create(
                name=voice_name,
                files=[audio_file]
            )

        print(f"   ✅ Clone created: {voice.voice_id}")

        # Clean up temp file
        try:
            os.remove(sample_path)
            print(f"   🗑️  Temp file cleaned up")
        except Exception as e:
            print(f"   ⚠️  Could not delete temp file: {e}")

        return voice.voice_id

    def _get_voice_id(self, character_data: Dict) -> str:
        """
        Select appropriate ElevenLabs voice based on character

        Accepts either:
        - voice_id: Direct ElevenLabs voice ID (for custom voices)
        - voice_style: Preset voice style key (for backward compatibility)
        """
        # If direct voice_id provided, use it
        if 'voice_id' in character_data and character_data['voice_id']:
            return character_data['voice_id']

        # Otherwise, fall back to voice_style mapping
        voice_style = character_data.get('voice_style', 'default')
        return self.voice_map.get(voice_style, self.voice_map['default'])

    def _slugify(self, text: str) -> str:
        """Convert character name to filesystem-safe slug"""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '_', text)
        return text[:50]  # Limit length


def test_generation():
    """Test character generation locally"""
    from dotenv import load_dotenv
    load_dotenv()

    db = Database('../data/punching_bag.db')
    generator = CharacterGenerator(db, '../data')

    test_character = {
        'name': 'Coach',
        'relationship': 'trainer',
        'personality': 'motivating, drill-sergeant',
        'intensity': 4,
        'voice_style': 'stern_boss',
        'description': 'Tough but fair coach who pushes you to your limits'
    }

    print("Generating test character...")
    for update in generator.generate_character(test_character):
        print(f"[{update['progress']}%] {update.get('message', update['status'])}")

    print("\nCharacter generation complete!")


if __name__ == '__main__':
    test_generation()
