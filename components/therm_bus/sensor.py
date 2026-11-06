import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLUME_FLOW_RATE,
    DEVICE_CLASS_WATER,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    UNIT_CELSIUS,
    UNIT_LITRE,
)

from . import CONF_THERM_BUS_ID, ThermBus


def _temperature():
    return sensor.sensor_schema(
        unit_of_measurement=UNIT_CELSIUS,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    )


def _raw(icon):
    return sensor.sensor_schema(
        accuracy_decimals=0, state_class=STATE_CLASS_MEASUREMENT, icon=icon
    )


# Keys map to set_<key>_sensor() on ThermBus.
SENSORS = {
    "setpoint": _temperature(),
    "outlet_temperature": _temperature(),
    "inlet_temperature": _temperature(),
    "casing_temperature": _temperature(),
    "flow": sensor.sensor_schema(
        unit_of_measurement="L/min",
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_VOLUME_FLOW_RATE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    "fan": _raw("mdi:fan"),
    "modulation": _raw("mdi:fire"),
    # Counts up during one tap opening and drops back to 0 afterwards, which
    # total_increasing treats as a meter reset, so HA still sums consumption.
    "litres": sensor.sensor_schema(
        unit_of_measurement=UNIT_LITRE,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_WATER,
        state_class=STATE_CLASS_TOTAL_INCREASING,
    ),
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_THERM_BUS_ID): cv.use_id(ThermBus),
        **{cv.Optional(key): schema for key, schema in SENSORS.items()},
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_THERM_BUS_ID])
    for key in SENSORS:
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(getattr(hub, f"set_{key}_sensor")(sens))
