import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor
from esphome.const import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_HEAT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_RUNNING,
    ENTITY_CATEGORY_DIAGNOSTIC,
)

from . import CONF_THERM_BUS_ID, ThermBus

# Keys map to set_<key>_binary_sensor() on ThermBus.
BINARY_SENSORS = {
    "power": binary_sensor.binary_sensor_schema(device_class=DEVICE_CLASS_POWER),
    "water_flow": binary_sensor.binary_sensor_schema(
        device_class=DEVICE_CLASS_RUNNING, icon="mdi:water"
    ),
    "fan_running": binary_sensor.binary_sensor_schema(
        device_class=DEVICE_CLASS_RUNNING, icon="mdi:fan"
    ),
    "flame": binary_sensor.binary_sensor_schema(
        device_class=DEVICE_CLASS_HEAT, icon="mdi:fire"
    ),
    "bus_connected": binary_sensor.binary_sensor_schema(
        device_class=DEVICE_CLASS_CONNECTIVITY,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ),
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_THERM_BUS_ID): cv.use_id(ThermBus),
        **{cv.Optional(key): schema for key, schema in BINARY_SENSORS.items()},
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_THERM_BUS_ID])
    for key in BINARY_SENSORS:
        if key in config:
            sens = await binary_sensor.new_binary_sensor(config[key])
            cg.add(getattr(hub, f"set_{key}_binary_sensor")(sens))
