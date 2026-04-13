import urllib.request
import zipfile
import os
import shutil

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg.zip"

print("Downloading ffmpeg...")
if os.path.exists(zip_path):
    os.remove(zip_path)

urllib.request.urlretrieve(url, zip_path)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall("ffmpeg-temp")

print("Moving binaries...")
for f in ["ffmpeg.exe", "ffprobe.exe"]:
    if os.path.exists(f):
        os.remove(f)
shutil.move(os.path.join("ffmpeg-temp", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe"), "ffmpeg.exe")
shutil.move(os.path.join("ffmpeg-temp", "ffmpeg-master-latest-win64-gpl", "bin", "ffprobe.exe"), "ffprobe.exe")

print("Cleaning up...")
os.remove(zip_path)
shutil.rmtree("ffmpeg-temp")
print("Done!")
