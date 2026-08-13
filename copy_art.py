import shutil
import glob

src_pattern = r"C:\Users\vp\.gemini\antigravity\brain\fc414571-467d-485c-85e2-89cb2a435492\nas100_card_art_*.jpg"
matches = glob.glob(src_pattern)
if matches:
    dest = r"c:\Users\vp\Documents\antigravity\elegant-hawking\public\nas100_art.jpg"
    shutil.copy(matches[-1], dest)
    print("Copied card artwork to public/nas100_art.jpg successfully!")
else:
    print("No matching image found.")
