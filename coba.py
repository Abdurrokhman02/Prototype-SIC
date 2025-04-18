import cv2
import requests
from ultralytics import YOLO
import streamlit as st
import time
from PIL import Image
import numpy as np
import pandas as pd

# ===== KONFIGURASI =====
UBIDOTS_TOKEN = "BBUS-cx7Eyxvf7WOVxkhQiiCDMTQqnsBj5j"
UBIDOTS_DEVICE_LABEL = "ESP32-CAM"
UBIDOTS_VARIABLE_LABEL = "jumlah_kendaraan"
model = YOLO("yolo11s")  # Ganti dengan model kamu
model.conf = 0.25
KENDARAAN_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck

# Kirim data ke Ubidots
def kirim_ke_ubidots(jumlah):
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{UBIDOTS_DEVICE_LABEL}"
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {UBIDOTS_VARIABLE_LABEL: jumlah}
    try:
        r = requests.post(url, headers=headers, json=payload)
        st.write(f"✅ [Ubidots] Status: {r.status_code}")
    except Exception as e:
        st.error(f"Gagal kirim ke Ubidots: {e}")

# ========== DASHBOARD ========== #
st.set_page_config(layout="wide")
st.title("🖼️ Deteksi Kendaraan dari Gambar")

# Sidebar menu
st.sidebar.markdown("### Upload Gambar")
uploaded_image = st.sidebar.file_uploader("Unggah gambar JPG", type=["jpg", "jpeg", "png"])

# Tempat tampil
placeholder = st.empty()
log_area = st.sidebar.empty()
info_col1, info_col2 = st.columns(2)

if uploaded_image is not None:
    # Baca gambar
    img_pil = Image.open(uploaded_image).convert("RGB")
    img_np = np.array(img_pil)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    # Deteksi
    results = model(img_bgr, verbose=False)[0]
    count = 0

    for box in results.boxes:
        cls = int(box.cls[0])
        if cls in KENDARAAN_CLASSES:
            count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = model.names[cls]
            conf = box.conf[0]
            cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img_bgr, f"{label} {conf:.2f}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Tambah teks jumlah kendaraan
    cv2.putText(img_bgr, f"Kendaraan: {count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Tampilkan di Streamlit
    img_rgb_result = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    placeholder.image(img_rgb_result, caption=f"Kendaraan terdeteksi: {count}", use_column_width=True)

    # Kirim ke Ubidots
    kirim_ke_ubidots(count)

    # Tampilkan info
    info_col1.metric("Jumlah Kendaraan", f"{count} terdeteksi")
    status_lampu = "🟢 Hijau" if count < 5 else "🔴 Merah"
    info_col2.metric("Status Lampu", status_lampu)
