#include "therm_bus.h"
#include "esphome/core/log.h"

namespace esphome {
namespace therm_bus {

static const char *const TAG = "therm_bus";

// Frames are separated by tens of ms of idle bus; bytes inside a frame
// arrive back to back (~2 ms each at 4800 baud).
static const uint32_t FRAME_GAP_MS = 10;
static const uint32_t BUS_TIMEOUT_MS = 5000;

static std::string to_hex(const uint8_t *data, size_t len) {
  static const char *const DIGITS = "0123456789ABCDEF";
  std::string out;
  out.reserve(len * 3);
  for (size_t i = 0; i < len; i++) {
    if (i) out += ' ';
    out += DIGITS[data[i] >> 4];
    out += DIGITS[data[i] & 0x0F];
  }
  return out;
}

#ifdef USE_SENSOR
static void publish_if_changed(sensor::Sensor *s, float value) {
  if (s != nullptr && (!s->has_state() || s->get_raw_state() != value))
    s->publish_state(value);
}
#endif

#ifdef USE_TEXT_SENSOR
static void publish_if_changed(text_sensor::TextSensor *s, const std::string &value) {
  if (s != nullptr && (!s->has_state() || s->get_raw_state() != value))
    s->publish_state(value);
}
#endif

void ThermBus::loop() {
  const uint32_t now = millis();

  if (this->pos_ > 0 && !this->available() && now - this->last_byte_ms_ > FRAME_GAP_MS) {
    ESP_LOGV(TAG, "Dropping incomplete frame: %s", to_hex(this->buf_, this->pos_).c_str());
    this->frames_bad_++;
    this->pos_ = 0;
  }

  uint8_t c;
  while (this->available() && this->read_byte(&c)) {
    this->last_byte_ms_ = now;
    if (this->pos_ == 0 && c != HDR_HEATER && c != HDR_REMOTE)
      continue;  // hunting for a header
    this->buf_[this->pos_++] = c;
    if (this->pos_ < 2)
      continue;
    const size_t total = this->buf_[1] + 1;
    if (total < 3 || total > MAX_FRAME_LEN) {
      this->frames_bad_++;
      this->pos_ = 0;
      continue;
    }
    if (this->pos_ == total) {
      this->handle_frame_(total);
      this->pos_ = 0;
    }
  }

#ifdef USE_BINARY_SENSOR
  // Fresh millis(): a frame handled above is stamped after `now`, and
  // `now - last_heater_ms_` would wrap around and flash "disconnected".
  if (this->bus_connected_ != nullptr)
    this->bus_connected_->publish_state(this->last_heater_ms_ != 0 &&
                                        millis() - this->last_heater_ms_ < BUS_TIMEOUT_MS);
#endif
}

void ThermBus::handle_frame_(size_t len) {
  uint8_t sum = 0;
  for (size_t i = 1; i < len; i++)
    sum += this->buf_[i];
  if (sum != 0) {
    this->frames_bad_++;
    ESP_LOGD(TAG, "Bad checksum: %s", to_hex(this->buf_, len).c_str());
    return;
  }
  this->frames_ok_++;
  ESP_LOGV(TAG, "Frame: %s", to_hex(this->buf_, len).c_str());

  if (this->buf_[0] == HDR_HEATER && len == HEATER_FRAME_LEN) {
    this->handle_heater_frame_();
  } else if (this->buf_[0] == HDR_REMOTE) {
#ifdef USE_TEXT_SENSOR
    publish_if_changed(this->remote_frame_, to_hex(this->buf_, len));
#endif
  }
}

void ThermBus::handle_heater_frame_() {
  const uint8_t *b = this->buf_;
  this->last_heater_ms_ = millis();

#ifdef USE_SENSOR
  publish_if_changed(this->setpoint_, b[11]);
  publish_if_changed(this->outlet_temperature_, b[12]);
  publish_if_changed(this->inlet_temperature_, b[13]);
  publish_if_changed(this->casing_temperature_, b[14]);
  publish_if_changed(this->flow_, b[16]);
  publish_if_changed(this->fan_, b[17]);
  publish_if_changed(this->modulation_, b[19]);
  publish_if_changed(this->litres_, b[27]);
#endif

#ifdef USE_BINARY_SENSOR
  // Binary sensors already drop repeated states.
  const uint8_t flags = b[7];
  if (this->power_ != nullptr)
    this->power_->publish_state(b[4] == 0x01);
  if (this->water_flow_ != nullptr)
    this->water_flow_->publish_state(flags & 0x01);
  if (this->fan_running_ != nullptr)
    this->fan_running_->publish_state(flags & 0x02);
  if (this->flame_ != nullptr)
    this->flame_->publish_state(flags & 0x04);
#endif

#ifdef USE_TEXT_SENSOR
  // Byte 2 cycles through pages 20..23; page 21 is enough and keeps the
  // state from changing on every frame.
  if (b[2] == 0x21)
    publish_if_changed(this->heater_frame_, to_hex(b, HEATER_FRAME_LEN));
#endif
}

void ThermBus::dump_config() {
  ESP_LOGCONFIG(TAG, "Therm bus:");
  ESP_LOGCONFIG(TAG, "  Frames ok: %u, bad: %u", (unsigned) this->frames_ok_, (unsigned) this->frames_bad_);
}

}  // namespace therm_bus
}  // namespace esphome
