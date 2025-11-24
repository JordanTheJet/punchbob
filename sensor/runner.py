#!/usr/bin/env python3
import os
import glob
import random
import subprocess

from punch_new import run_punch_session  # from the punch.py we just built

# Base directory for reaction sounds
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REACTIONS_DIR = os.path.join(SCRIPT_DIR, "Reactions")

# Optional: text lines for console output
RESPONSES = {
    "pathetic": [
        "Did you just bump into it by accident?",
        "I’ve seen stronger taps on a phone screen.",
    ],
    "are you trying": [
        "Effort detected. Barely.",
        "You might scare a feather with that.",
    ],
    "weak": [
        "That would annoy, not injure.",
        "We’re still in warm-up territory.",
    ],
    "not bad": [
        "Not bad. The bag actually noticed.",
        "Okay, starting to look like a real hit.",
    ],
    "good": [
        "Now we’re talking. Solid impact.",
        "That sounded like it hurt something—good.",
    ],
    "great": [
        "ELITE. The sensor flinched.",
        "That’s a highlight-reel punch.",
    ],
}


def classify_peak(a_dyn_g: float):
    """
    Map peak dynamic acceleration (in g) to a label that matches your folder names:
      'pathetic', 'are you trying', 'weak', 'not bad', 'good', 'great'
    Thresholds tuned for ±4 g per axis (sens = 8192.0).
    """
    if a_dyn_g < 0.3:
        return None, None  # too small to care

    if a_dyn_g < 0.75:
        label = "pathetic"
    elif a_dyn_g < 1.5:
        label = "are you trying"
    elif a_dyn_g < 2.5:
        label = "weak"
    elif a_dyn_g < 3.5:
        label = "not bad"
    elif a_dyn_g < 4.5:
        label = "good"
    else:
        label = "great"

    line = random.choice(RESPONSES[label])
    return label, line


def pick_sound_file(label: str):
    """
    Pick a random .wav file from reactions/<label>/.
    Folder names include spaces, e.g. 'are you trying', 'not bad'.
    """
    dir_path = os.path.join(REACTIONS_DIR, label)
    pattern = os.path.join(dir_path, "*.wav")
    files = glob.glob(pattern)

    if not files:
        print(f"No .wav files found for '{label}' in {dir_path}")
        return None

    return random.choice(files)


def play_sound(path: str):
    """Play a .wav file using aplay."""
    if path is None:
        return
    print(f"Playing sound: {path}")
    try:
        subprocess.run(["aplay", path], check=False)
    except FileNotFoundError:
        print("Error: 'aplay' not found. Install with: sudo apt-get install alsa-utils")


def main():
    print("Starting punch session (backend: punch.py).")
    print("Punch as much as you like; end the session with Ctrl+C.\n")

    # 1) Run punch session and get max dynamic g
    session_max_dyn_g = run_punch_session()

    if session_max_dyn_g is None or session_max_dyn_g < 0.3:
        print("No meaningful punch detected. No reaction played.")
        return

    print(f"\nSession max dynamic acceleration: {session_max_dyn_g:.2f} g")

    # 2) Classify into one of your reaction folders
    label, line = classify_peak(session_max_dyn_g)
    if label is None:
        print("Punch too weak to classify. No reaction played.")
        return

    print(f"Reaction class: {label.upper()}  ->  {line}")

    # 3) Pick random sound from reactions/<label>/ and play
    sound_file = pick_sound_file(label)
    play_sound(sound_file)


if __name__ == "__main__":
    main()
