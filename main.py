import os
import random
import string
from datetime import datetime
from pathlib import Path
from PIL import Image
import streamlit as st
import shutil

# ---------------- CONFIG ----------------
QUALITY = 60         # JPEG/WebP quality
MAX_WIDTH = 1280     # Resize max width
MAX_HEIGHT = 1280    # Resize max height
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# Destination = local folder (safe for Render)
DOWNLOADS = "processed_images"
os.makedirs(DOWNLOADS, exist_ok=True)

# ---------------- UTILS ----------------
def generate_new_name(ext):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    rand_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"{timestamp}-{rand_code}{ext}"

def resize_image(img):
    img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
    return img

def compress_and_rename(input_path, output_folder):
    ext = os.path.splitext(input_path)[1].lower()
    if ext not in ALLOWED_EXT:
        return None, None, None

    try:
        img = Image.open(input_path)
        img = resize_image(img)

        final_ext = ext
        temp_output = os.path.join(output_folder, "temp_" + os.path.basename(input_path))

        # ---- Compress & strip metadata ----
        if ext in [".jpg", ".jpeg"]:
            img.save(temp_output, "JPEG", optimize=True, quality=QUALITY, progressive=True)
        elif ext == ".png":
            rgb_img = img.convert("RGB")
            temp_output = temp_output.replace(".png", ".jpg")
            rgb_img.save(temp_output, "JPEG", optimize=True, quality=QUALITY, progressive=True)
            final_ext = ".jpg"
        elif ext == ".webp":
            img.save(temp_output, "WEBP", quality=QUALITY, method=6)

        # ---- Rename after compression ----
        new_filename = generate_new_name(final_ext)
        final_output = os.path.join(output_folder, new_filename)
        os.rename(temp_output, final_output)

        old_size = os.path.getsize(input_path) // 1024
        new_size = os.path.getsize(final_output) // 1024

        return new_filename, (old_size, new_size), final_output
    except Exception as e:
        st.error(f"❌ Error with {input_path}: {e}")
        return None, None, None

# ---------------- STREAMLIT APP ----------------
st.title("📸 Image Compressor + Renamer")

uploaded_files = st.file_uploader(
    "Upload images", 
    type=["jpg", "jpeg", "png", "webp"], 
    accept_multiple_files=True
)

if uploaded_files and st.button("Process Uploads"):
    output_folder = DOWNLOADS
    os.makedirs(output_folder, exist_ok=True)

    results = []

    # Temporary folder for uploaded files
    temp_folder = os.path.join(output_folder, "temp_uploads")
    os.makedirs(temp_folder, exist_ok=True)

    for file in uploaded_files:
        temp_path = os.path.join(temp_folder, file.name)
        with open(temp_path, "wb") as f:
            f.write(file.read())

        # Compress and rename → save only to final output folder
        new_name, sizes, final_output = compress_and_rename(temp_path, output_folder)
        if new_name and sizes:
            results.append((file.name, new_name, sizes, final_output))

    # Remove temp folder
    shutil.rmtree(temp_folder)

    if results:
        st.success(f"✅ Processed {len(results)} images. Ready for download below:")
        for orig, new, (old_kb, new_kb), final_output in results:
            st.write(f"{orig} → {new} | {old_kb}KB → {new_kb}KB")

            # ---- Add Download Button ----
            with open(final_output, "rb") as f:
                img_bytes = f.read()
            st.download_button(
                label=f"⬇️ Download {new}",
                data=img_bytes,
                file_name=new,
                mime="image/jpeg" if new.endswith(".jpg") else "image/webp"
            )
    else:
        st.warning("No valid images uploaded.")
