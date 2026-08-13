import shutil
import glob
import os

brain_dir = r"C:\Users\vp\.gemini\antigravity\brain\fc414571-467d-485c-85e2-89cb2a435492"
public_dir = r"c:\Users\vp\Documents\antigravity\elegant-hawking\public"

mapping = {
    "art_neutral": "nas_art_neutral_*.jpg",
    "art_green_single": "nas_green_single_*.jpg",
    "art_green_double": "nas_green_double_*.jpg",
    "art_red_single": "nas_red_single_*.jpg",
    "art_red_double": "nas_red_double_*.jpg"
}

for name, pattern in mapping.items():
    matches = glob.glob(os.path.join(brain_dir, pattern))
    if matches:
        dest = os.path.join(public_dir, f"{name}.jpg")
        shutil.copy(matches[-1], dest)
        print(f"Copied {name}.jpg successfully!")
    else:
        print(f"Warning: No match for {pattern}")
