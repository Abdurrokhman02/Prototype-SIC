#include "esp_camera.h"
#include <WiFi.h>
#include <Wire.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// wifi
const char *ssid = "Kos ijo";
const char *password = "Aslan199";

// model kamera yang digunakan
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// Definisi pin untuk LED lalu lintas
#define LED_MERAH 12
#define LED_KUNING 13
#define LED_HIJAU 4

// Konfigurasi OLED
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Membuat server web untuk menerima data jumlah kendaraan
WebServer server(80);

// Variabel untuk menyimpan jumlah kendaraan yang diterima dari laptop (OpenCV)
int jumlah_kendaraan = 0;

// Fungsi untuk menghitung durasi lampu merah berdasarkan jumlah kendaraan
int hitungDurasiLampuMerah(int count) {
  if (count == 0) return 30;              // Kendaraan jarang
  else if (count == 1) return 20;  // Kendaraan sedang
  else return 10;                          // Kendaraan padat
}

// Fungsi untuk menghitung durasi lampu hijau berdasarkan jumlah kendaraan
int hitungDurasiLampuHijau(int count) {
  if (count == 0) return 10;              // Kendaraan jarang
  else if (count == 1) return 20;  // Kendaraan sedang
  else return 30;                          // Kendaraan padat
}

void startCameraServer(); // Didefinisikan di app_httpd.cpp

// Fungsi untuk inisialisasi pin LED
void setupLed() {
  pinMode(LED_MERAH, OUTPUT);
  pinMode(LED_KUNING, OUTPUT);
  pinMode(LED_HIJAU, OUTPUT);
}

// Fungsi untuk mengatur siklus lampu lalu lintas berdasarkan jumlah kendaraan
void nyalakanLampuLaluLintas() {
  int durasiMerah = hitungDurasiLampuMerah(jumlah_kendaraan);
  Serial.print("Durasi merah: ");
  Serial.println(durasiMerah);

  // Nyalakan lampu merah
  digitalWrite(LED_MERAH, HIGH);
  digitalWrite(LED_KUNING, LOW);
  digitalWrite(LED_HIJAU, LOW);

  // Tampilkan countdown di OLED
  for (int i = durasiMerah; i >= 0; i--) {
    display.clearDisplay();
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.print("Merah: ");
    display.println(i);
    display.display();
    delay(1000);
  }

  // Lampu kuning sebagai peringatan transisi
  digitalWrite(LED_MERAH, LOW);
  digitalWrite(LED_KUNING, HIGH);
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.print("Hati-hati");
  display.display();
  delay(2000);
  
  int durasiHijau = hitungDurasiLampuHijau(jumlah_kendaraan);
  Serial.print("Durasi hijau: ");
  Serial.println(durasiHijau);

  // Nyalakan lampu hijau
  digitalWrite(LED_KUNING, LOW);
  digitalWrite(LED_HIJAU, HIGH);

  // Tampilkan countdown hijau
  for (int i = durasiHijau; i >= 0; i--) {
    display.clearDisplay();
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.print("Hijau: ");
    display.println(i);
    display.display();
    delay(1000);
  }

  // Kembali ke kuning sebelum siklus ulang
  digitalWrite(LED_HIJAU, LOW);
  digitalWrite(LED_KUNING, HIGH);
  delay(2000);

  digitalWrite(LED_KUNING, LOW); // Reset semua lampu
}

// Handler untuk endpoint root "/"
void handleRoot() {
  server.send(200, "text/plain", "Server ESP aktif.");
}

// Handler untuk endpoint "/update?count=xx"
void handleUpdate() {
  if (server.hasArg("count")) {
    jumlah_kendaraan = server.arg("count").toInt(); // Simpan data dari parameter
    server.send(200, "text/plain", "Jumlah kendaraan diperbarui ke: " + String(jumlah_kendaraan));
  } else {
    server.send(400, "text/plain", "Argumen 'count' tidak ditemukan.");
  }
}

// Fungsi untuk memulai server web custom
void startMyWebServer() {
  server.on("/", handleRoot);         // Endpoint utama
  server.on("/update", handleUpdate); // Endpoint untuk update jumlah kendaraan
  server.begin();
  Serial.println("HTTP Server aktif di port 80");
}

void setup() {
  Serial.begin(115200);
  Wire.begin(14, 15); // Inisialisasi I2C (SDA = 14, SCL = 15)

  // Inisialisasi OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Gagal inisialisasi OLED"));
    while (true); // Berhenti jika gagal
  }
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Siap!");
  display.display();

  // Konfigurasi kamera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_QVGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 10;
  config.fb_count = 2;

  // Inisialisasi kamera
  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Gagal inisialisasi kamera");
    return;
  }

  // Hubungkan ke jaringan WiFi
  WiFi.begin(ssid, password);
  Serial.print("Menyambungkan ke WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nTerhubung ke WiFi!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  setupLed();              // Inisialisasi LED
  startCameraServer();     // Mulai server kamera
  startMyWebServer();      // Mulai server web untuk jumlah kendaraan
}

void loop() {
  server.handleClient();         // Menangani permintaan web client
  nyalakanLampuLaluLintas();     // Jalankan siklus lampu berdasarkan jumlah kendaraan
}
