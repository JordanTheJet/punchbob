import random
import time
import subprocess
import threading
from typing import Dict, List, Optional
from database import Database
from services.hit_sounds import HitSoundPlayer

class PunchHandler:
    """
    Handles real-time punch detection and response selection.

    Features:
    - 3 feedback modes: voice grunts, hit sounds, or silent
    - Combo detection (punches within 2 seconds)
    - Trash talk after combo ends

    Target latency: <200ms from punch to audio playback.
    """

    def __init__(self, db: Database, character_id: int, session_id: int,
                 feedback_mode: str = 'grunts', data_dir: str = '../data'):
        """
        Args:
            feedback_mode: 'grunts' (voice), 'hit_sounds' (cinematic), or 'silent'
        """
        self.db = db
        self.character_id = character_id
        self.session_id = session_id
        self.feedback_mode = feedback_mode
        self.data_dir = data_dir

        # Cache all responses for this character (trash talk)
        self.response_cache = self._load_response_cache()
        self.grunt_cache = self._load_grunt_cache()
        self.hit_sound_player = HitSoundPlayer(data_dir) if feedback_mode == 'hit_sounds' else None
        self.recent_responses = []  # Track to avoid repetition
        self.max_recent = 5  # Remember last 5 responses

        # Combo detection
        self.combo_punches = []
        self.combo_timeout = 2.0  # seconds between punches to consider combo
        self.combo_timer = None

        # Audio player
        self.audio_lock = threading.Lock()
        self.current_process = None

    def _load_response_cache(self) -> Dict[int, List[Dict]]:
        """Load all trash talk responses (tiers 1-5) for character"""
        cache = {1: [], 2: [], 3: [], 4: [], 5: []}

        responses = self.db.get_responses_by_character(self.character_id)

        for response in responses:
            tier = response['tier']
            if tier >= 1:  # Only positive tiers (trash talk)
                cache[tier].append(response)

        print(f"Loaded {sum(len(v) for v in cache.values())} trash talk responses")
        return cache

    def _load_grunt_cache(self) -> Dict[str, List[Dict]]:
        """Load all grunt sounds (negative tiers) for character"""
        cache = {'light': [], 'medium': [], 'heavy': []}

        responses = self.db.get_responses_by_character(self.character_id)

        for response in responses:
            tier = response['tier']
            if tier == -1:
                cache['light'].append(response)
            elif tier == -2:
                cache['medium'].append(response)
            elif tier == -3:
                cache['heavy'].append(response)

        total_grunts = sum(len(v) for v in cache.values())
        print(f"Loaded {total_grunts} grunt sounds")

        if total_grunts == 0:
            print("⚠️  Warning: This character has no grunt sounds (created before grunt feature)")
            print("   Fallback: Voice grunts mode will work silently, use hit_sounds or silent mode instead")
            print("   Or recreate the character to get grunt sounds")

        return cache

    def handle_punch(self, force_value: float, max_force: float = 1023.0) -> Dict:
        """
        Main handler called when accelerometer detects a punch.

        Flow:
        1. Play grunt immediately (if enabled)
        2. Add punch to combo
        3. Start/reset combo timer
        4. When combo ends (after timeout), play trash talk

        Args:
            force_value: Raw force reading from accelerometer (0-1023)
            max_force: Maximum force value for normalization

        Returns:
            Dict with response details including grunt and whether combo ended
        """
        start_time = time.time()

        # Normalize force to percentage
        force_pct = (force_value / max_force) * 100

        # Determine tier (1-5)
        tier = self._calculate_tier(force_pct)

        # Play immediate feedback based on mode (if force > 20%)
        feedback_played = None
        if force_pct >= 20:
            if self.feedback_mode == 'grunts':
                # Play character voice grunt
                grunt = self._select_grunt(force_pct)
                if grunt:
                    self._play_audio(grunt['audio_path'])
                    feedback_played = grunt['text']

            elif self.feedback_mode == 'hit_sounds':
                # Play cinematic hit sound
                hit_sound = self.hit_sound_player.get_sound(force_pct)
                if hit_sound:
                    self._play_audio(hit_sound)
                    feedback_played = f"HIT ({force_pct:.0f}%)"

            # else: silent mode - no immediate feedback

        # Add to combo
        self.combo_punches.append({
            'force': force_pct,
            'tier': tier,
            'timestamp': time.time()
        })

        # Cancel previous combo timer
        if self.combo_timer:
            self.combo_timer.cancel()

        # Start new combo timer
        self.combo_timer = threading.Timer(self.combo_timeout, self._end_combo)
        self.combo_timer.start()

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Log punch
        self.db.log_punch(
            session_id=self.session_id,
            character_id=self.character_id,
            force_value=force_pct,
            tier=tier,
            response_id=None,  # Will be set when combo ends
            latency_ms=latency_ms
        )

        return {
            "force": force_pct,
            "tier": tier,
            "text": feedback_played or "",  # For compatibility with old frontend code
            "feedback": feedback_played,
            "feedback_mode": self.feedback_mode,
            "combo_count": len(self.combo_punches),
            "latency_ms": latency_ms,
            "timestamp": time.time()
        }

    def _end_combo(self):
        """Called when combo timer expires - play trash talk based on combo"""
        if not self.combo_punches:
            return

        # Calculate combo stats
        avg_force = sum(p['force'] for p in self.combo_punches) / len(self.combo_punches)
        max_force = max(p['force'] for p in self.combo_punches)
        combo_length = len(self.combo_punches)

        # Determine tier based on best punch in combo
        tier = self._calculate_tier(max_force)

        # Select and play trash talk
        response = self._select_response(tier)
        if response:
            self._play_audio(response['audio_path'])

            print(f"Combo ended: {combo_length} punches, avg {avg_force:.1f}%, max {max_force:.1f}%")
            print(f"  → \"{response['text']}\"")

        # Clear combo
        self.combo_punches.clear()
        self.combo_timer = None

    def _calculate_tier(self, force_pct: float) -> int:
        """
        Map force percentage to tier (1-5)

        Tier 1: 0-20% (Weak)
        Tier 2: 20-40% (Light)
        Tier 3: 40-60% (Medium)
        Tier 4: 60-85% (Hard)
        Tier 5: 85-100% (Maximum)
        """
        if force_pct < 20:
            return 1
        elif force_pct < 40:
            return 2
        elif force_pct < 60:
            return 3
        elif force_pct < 85:
            return 4
        else:
            return 5

    def _select_grunt(self, force_pct: float) -> Optional[Dict]:
        """
        Select appropriate grunt based on punch force

        light: 20-50%
        medium: 50-75%
        heavy: 75%+

        Returns None if character doesn't have grunt sounds (old characters)
        """
        if force_pct < 50:
            level = 'light'
        elif force_pct < 75:
            level = 'medium'
        else:
            level = 'heavy'

        candidates = self.grunt_cache.get(level, [])
        if not candidates:
            # Old character without grunts - fallback gracefully
            return None

        return random.choice(candidates)

    def _select_response(self, tier: int) -> Optional[Dict]:
        """
        Select appropriate response for tier, avoiding recent repeats.

        Returns random response from tier, excluding recently played ones.
        """
        candidates = self.response_cache.get(tier, [])

        if not candidates:
            return None

        # Filter out recently used responses
        available = [r for r in candidates if r['id'] not in self.recent_responses]

        # If all used recently, reset and use all
        if not available:
            available = candidates
            self.recent_responses.clear()

        # Select random response
        response = random.choice(available)

        # Track usage
        self.recent_responses.append(response['id'])
        if len(self.recent_responses) > self.max_recent:
            self.recent_responses.pop(0)

        return response

    def _play_audio(self, audio_path: str):
        """
        Play audio file using mpg123 (lowest latency on Pi).
        Non-blocking - returns immediately.
        """
        with self.audio_lock:
            # Stop current audio if playing
            if self.current_process:
                try:
                    self.current_process.terminate()
                except:
                    pass

            # Start new audio playback
            # mpg123 is pre-installed on Raspberry Pi OS and very fast
            try:
                self.current_process = subprocess.Popen(
                    ['mpg123', '-q', audio_path],  # -q for quiet (no output)
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except FileNotFoundError:
                # Fallback to pygame if mpg123 not available (development)
                print(f"mpg123 not found, install with: sudo apt-get install mpg123")
                print(f"Would play: {audio_path}")

    def set_feedback_mode(self, mode: str):
        """
        Change feedback mode dynamically during workout

        Args:
            mode: 'grunts', 'hit_sounds', or 'silent'
        """
        print(f"🔄 Changing feedback mode: {self.feedback_mode} → {mode}")
        self.feedback_mode = mode

        # Initialize hit sound player if switching to hit_sounds
        if mode == 'hit_sounds' and not self.hit_sound_player:
            self.hit_sound_player = HitSoundPlayer(self.data_dir)
            print(f"   Loaded hit sound player")

    # def stop_audio(self):
    #     """Stop current audio playback"""
    #     with self.audio_lock:
    #         if self.current_process:
    #             try:
    #                 self.current_process.terminate()
    #                 self.current_process = None
    #             except:
    #                 pass


class MockSensorSimulator:
    """Simulates punch sensor for testing without hardware"""

    def __init__(self, punch_handler: PunchHandler):
        self.handler = punch_handler
        self.max_force = 1023.0

    def simulate_workout(self, num_punches: int = 20):
        """Simulate a workout session with random punch strengths"""
        print(f"\n=== Starting simulated workout ({num_punches} punches) ===\n")

        for i in range(num_punches):
            # Random force (weighted toward medium punches)
            force = random.triangular(0, self.max_force, self.max_force * 0.5)

            print(f"Punch {i+1}/{num_punches}: Force = {force:.0f}")

            result = self.handler.handle_punch(force, self.max_force)

            print(f"  → Tier {result['tier']}: \"{result['text']}\"")
            print(f"  → Latency: {result['latency_ms']}ms\n")

            # Wait between punches (realistic timing)
            time.sleep(random.uniform(1.5, 3.0))

        print("=== Workout complete ===")


def test_punch_handler():
    """Test punch handling with mock data"""
    from dotenv import load_dotenv
    load_dotenv()

    db = Database('../data/punching_bag.db')

    # Get first character
    characters = db.get_all_characters()
    if not characters:
        print("No characters found. Run character_generator.py first.")
        return

    character = characters[0]
    print(f"Using character: {character['name']}")

    # Create session
    session_id = db.create_session(character['id'])
    print(f"Session ID: {session_id}")

    # Initialize handler
    handler = PunchHandler(db, character['id'], session_id)

    # Simulate workout
    simulator = MockSensorSimulator(handler)
    simulator.simulate_workout(num_punches=10)

    # End session
    db.end_session(session_id)

    # Show stats
    stats = db.get_character_stats(character['id'])
    print(f"\n=== Character Stats ===")
    print(f"Total sessions: {stats['total_sessions']}")
    print(f"Total punches: {stats['total_punches']}")
    print(f"Avg force: {stats['avg_force']:.1f}%")
    print(f"Max force: {stats['max_force']:.1f}%")


if __name__ == '__main__':
    test_punch_handler()
