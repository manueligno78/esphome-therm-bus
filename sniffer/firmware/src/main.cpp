// Bosch Therm 5600 O remote-bus sampler for ESP32 DevKit (WROOM-32).
//
// The bus voltage, through a divider, is on GPIO34 (ADC1, usable with Wi-Fi
// on). I2S drives the ADC at SAMPLE_RATE through DMA; blocks of raw 12-bit
// samples are streamed over TCP to sniffer/capture_esp32.py, which finds the
// board through a UDP broadcast beacon.
//
// Wire protocol (little endian):
//   on connect: "THERM32" + uint16 n + n * uint16 mV
//               ADC calibration: pin millivolts for raw 0, 64, ..., 4032, 4095
//   then packets: "TS" + uint16 n + uint32 t_us + n * uint16 raw
//               t_us = micros() when the block left the DMA; the PC derives
//               the real sample rate and any gaps from it.
//
// Wi-Fi credentials go through the WiFiManager portal (AP "therm-sniffer") on
// first boot and are kept in flash.

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <WiFiUdp.h>
#include <driver/adc.h>
#include <driver/i2s.h>
#include <esp_adc_cal.h>

static const adc1_channel_t ADC_CH = ADC1_CHANNEL_6;  // GPIO34
static const uint32_t SAMPLE_RATE = 100000;
static const uint16_t TCP_PORT = 3333;
static const uint16_t BEACON_PORT = 3334;
static const size_t BLOCK = 1024;  // samples per packet

static WiFiServer server(TCP_PORT);
static WiFiClient client;
static WiFiUDP udp;
static esp_adc_cal_characteristics_t adcChars;

static void startAdc() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_MSB;
  cfg.dma_buf_count = 16;
  cfg.dma_buf_len = 1024;
  i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
  i2s_set_adc_mode(ADC_UNIT_1, ADC_CH);
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten(ADC_CH, ADC_ATTEN_DB_11);
  esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_11, ADC_WIDTH_BIT_12, 1100, &adcChars);
  i2s_adc_enable(I2S_NUM_0);
}

static void sendHello() {
  uint8_t out[7 + 2 + 65 * 2];
  memcpy(out, "THERM32", 7);
  uint16_t n = 65;
  memcpy(out + 7, &n, 2);
  for (uint16_t i = 0; i < n; i++) {
    uint32_t raw = i < 64 ? i * 64 : 4095;
    uint16_t mv = esp_adc_cal_raw_to_voltage(raw, &adcChars);
    memcpy(out + 9 + i * 2, &mv, 2);
  }
  client.setNoDelay(true);
  client.write(out, sizeof(out));
}

static void beacon() {
  static uint32_t last = 0;
  if (millis() - last < 1000) return;
  last = millis();
  String msg = "therm-sniffer " + WiFi.localIP().toString() + " " + String(TCP_PORT);
  udp.beginPacket(WiFi.broadcastIP(), BEACON_PORT);
  udp.write(reinterpret_cast<const uint8_t*>(msg.c_str()), msg.length());
  udp.endPacket();
}

void setup() {
  Serial.begin(115200);

  WiFi.mode(WIFI_STA);
  WiFiManager wm;
  wm.setConfigPortalTimeout(300);
  if (!wm.autoConnect("therm-sniffer")) ESP.restart();
  WiFi.setSleep(false);

  server.begin();
  startAdc();
  Serial.printf("\nready: %s:%u\n", WiFi.localIP().toString().c_str(), TCP_PORT);
}

void loop() {
  static uint8_t out[8 + BLOCK * 2];
  uint16_t* samples = reinterpret_cast<uint16_t*>(out + 8);

  size_t got = 0;
  i2s_read(I2S_NUM_0, samples, BLOCK * 2, &got, portMAX_DELAY);
  uint32_t now = micros();
  uint16_t n = got / 2;

  if (!client.connected()) {
    client.stop();
    client = server.available();
    if (client) sendHello();
    else beacon();
    return;
  }

  // The I2S ADC delivers samples swapped in pairs, channel id in the top 4 bits.
  for (uint16_t i = 0; i + 1 < n; i += 2) {
    uint16_t a = samples[i];
    samples[i] = samples[i + 1] & 0x0FFF;
    samples[i + 1] = a & 0x0FFF;
  }
  out[0] = 'T';
  out[1] = 'S';
  memcpy(out + 2, &n, 2);
  memcpy(out + 4, &now, 4);
  client.write(out, 8 + n * 2);
}
