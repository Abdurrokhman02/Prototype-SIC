import cv2
import requests
from ultralytics import YOLO
import streamlit as st
import time
from PIL import Image
import numpy as np
import pandas as pd

# ===== KONFIGURASI =====
ESP32_IP = "http://192.168.1.32/update"
UBIDOTS_TOKEN = "BBUS-cx7Eyxvf7WOVxkhQiiCDMTQqnsBj5j"
UBIDOTS_DEVICE_LABEL = "ESP32-CAM"
UBIDOTS_VARIABLE_LABEL = "jumlah_kendaraan"
STREAM_URL = "http://192.168.1.32:81/stream"
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
st.title("🚦 Smart Traffic Light - KARI")

# Sidebar menu hanya satu mode
st.sidebar.markdown("### Mode")
menu = "📷 Kamera + Analis"

# ============================
# MODE: KAMERA + ANALIS REAL-TIME
# ============================
placeholder = st.empty()
status_area = st.sidebar.empty()
log_area = st.sidebar.empty()
chart_placeholder = st.sidebar.empty()
info_col1, info_col2 = st.columns(2)

run_detection = st.sidebar.button("▶ Mulai Deteksi")
if run_detection:
    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        st.error("❌ Gagal buka stream dari ESP32-CAM.")
        st.stop()

    last_count = -1
    history_data = []
    timestamps = []
    stop_button = st.sidebar.button("⏹ Stop")

    while True:
        ret, frame = cap.read()
        if not ret:
            st.warning("⚠ Gagal ambil frame.")
            continue

        results = model(frame, verbose=False)[0]
        count = 0

        for box in results.boxes:
            cls = int(box.cls[0])
            if cls in KENDARAAN_CLASSES:
                count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = model.names[cls]
                conf = box.conf[0]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Tampilkan jumlah kendaraan
        cv2.putText(frame, f"Kendaraan: {count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Tampilkan di Streamlit
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(frame_rgb)
        placeholder.image(img_pil, caption=f"Kendaraan terdeteksi: {count}", use_column_width=True)

        # Tambahkan data ke log
        waktu = time.strftime('%H:%M:%S')
        history_data.append(count)
        timestamps.append(waktu)

        if len(history_data) > 30:
            history_data.pop(0)
            timestamps.pop(0)

        df_log = pd.DataFrame({"Waktu": timestamps, "Jumlah": history_data})
        log_area.dataframe(df_log[::-1], use_container_width=True)

        # Rata-rata kendaraan
        rata2 = np.mean(history_data)
        info_col1.metric("Rata-rata (30s)", f"{rata2:.2f} kendaraan")

        # Status lampu otomatis
        status_lampu = "🟢 Hijau" if count < 5 else "🔴 Merah"
        info_col2.metric("Status Lampu", status_lampu)

        # Grafik di sidebar
        chart_df = pd.DataFrame({"Waktu": timestamps, "Jumlah": history_data})
        chart_placeholder.line_chart(chart_df.set_index("Waktu"))

        # Kirim ke ESP dan Ubidots jika berubah
        if count != last_count:
            try:
                r = requests.get(f"{ESP32_IP}?count={count}")
                status_area.success(f"📤 Kirim ke ESP32: {count}, Respon: {r.text}")
            except Exception as e:
                status_area.error(f"Gagal kirim ke ESP32: {e}")
            kirim_ke_ubidots(count)
            last_count = count

        # Analis Real-Time (di bawah video)
        with st.expander("📊 Analis Real-Time", expanded=True):
            st.markdown("#### Tabel dan Grafik Jumlah Kendaraan Real-Time")
            realtime_df = pd.DataFrame({"Waktu": timestamps, "Jumlah Kendaraan": history_data})
            st.dataframe(realtime_df[::-1], use_container_width=True)
            st.line_chart(realtime_df.set_index("Waktu"))

        if stop_button:
            break

    cap.release()
    st.success("✅ Deteksi dihentikan.")