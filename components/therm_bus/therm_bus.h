#pragma once

#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"
#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif
#ifdef USE_BINARY_SENSOR
#include "esphome/components/binary_sensor/binary_sensor.h"
#endif
#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif

namespace esphome {
namespace therm_bus {

// Bosch Therm 5600 O remote bus, read side. 4800 8N1; frames are
// [hdr][len][payload...][chk] with hdr 0xF5 heater->remote, 0xFA
// remote->heater, len = bytes after hdr, and (len + payload + chk) % 256 == 0.
// Byte meanings are in PROTOCOL.md.

static const uint8_t HDR_HEATER = 0xF5;
static const uint8_t HDR_REMOTE = 0xFA;
static const size_t HEATER_FRAME_LEN = 34;
static const size_t MAX_FRAME_LEN = 64;

class ThermBus : public Component, public uart::UARTDevice {
 public:
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

#ifdef USE_SENSOR
  void set_setpoint_sensor(sensor::Sensor *s) { this->setpoint_ = s; }
  void set_outlet_temperature_sensor(sensor::Sensor *s) { this->outlet_temperature_ = s; }
  void set_inlet_temperature_sensor(sensor::Sensor *s) { this->inlet_temperature_ = s; }
  void set_casing_temperature_sensor(sensor::Sensor *s) { this->casing_temperature_ = s; }
  void set_flow_sensor(sensor::Sensor *s) { this->flow_ = s; }
  void set_fan_sensor(sensor::Sensor *s) { this->fan_ = s; }
  void set_modulation_sensor(sensor::Sensor *s) { this->modulation_ = s; }
  void set_litres_sensor(sensor::Sensor *s) { this->litres_ = s; }
#endif
#ifdef USE_BINARY_SENSOR
  void set_power_binary_sensor(binary_sensor::BinarySensor *s) { this->power_ = s; }
  void set_water_flow_binary_sensor(binary_sensor::BinarySensor *s) { this->water_flow_ = s; }
  void set_fan_running_binary_sensor(binary_sensor::BinarySensor *s) { this->fan_running_ = s; }
  void set_flame_binary_sensor(binary_sensor::BinarySensor *s) { this->flame_ = s; }
  void set_bus_connected_binary_sensor(binary_sensor::BinarySensor *s) { this->bus_connected_ = s; }
#endif
#ifdef USE_TEXT_SENSOR
  void set_heater_frame_text_sensor(text_sensor::TextSensor *s) { this->heater_frame_ = s; }
  void set_remote_frame_text_sensor(text_sensor::TextSensor *s) { this->remote_frame_ = s; }
#endif

 protected:
  void handle_frame_(size_t len);
  void handle_heater_frame_();

  uint8_t buf_[MAX_FRAME_LEN];
  size_t pos_{0};
  uint32_t last_byte_ms_{0};
  uint32_t last_heater_ms_{0};
  uint32_t frames_ok_{0};
  uint32_t frames_bad_{0};

#ifdef USE_SENSOR
  sensor::Sensor *setpoint_{nullptr};
  sensor::Sensor *outlet_temperature_{nullptr};
  sensor::Sensor *inlet_temperature_{nullptr};
  sensor::Sensor *casing_temperature_{nullptr};
  sensor::Sensor *flow_{nullptr};
  sensor::Sensor *fan_{nullptr};
  sensor::Sensor *modulation_{nullptr};
  sensor::Sensor *litres_{nullptr};
#endif
#ifdef USE_BINARY_SENSOR
  binary_sensor::BinarySensor *power_{nullptr};
  binary_sensor::BinarySensor *water_flow_{nullptr};
  binary_sensor::BinarySensor *fan_running_{nullptr};
  binary_sensor::BinarySensor *flame_{nullptr};
  binary_sensor::BinarySensor *bus_connected_{nullptr};
#endif
#ifdef USE_TEXT_SENSOR
  text_sensor::TextSensor *heater_frame_{nullptr};
  text_sensor::TextSensor *remote_frame_{nullptr};
#endif
};

}  // namespace therm_bus
}  // namespace esphome
