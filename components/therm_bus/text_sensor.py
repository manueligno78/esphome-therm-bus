import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor
from esphome.const import ENTITY_CATEGORY_DIAGNOSTIC

from . import CONF_THERM_BUS_ID, ThermBus

# Raw frames in hex, for mapping the bytes still unknown from HA history.
# Keys map to set_<key>_text_sensor() on ThermBus.
TEXT_SENSORS = {
    "heater_frame": text_sensor.text_sensor_schema(
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC, icon="mdi:code-brackets"
    ),
    "remote_frame": text_sensor.text_sensor_schema(
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC, icon="mdi:code-brackets"
    ),
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_THERM_BUS_ID): cv.use_id(ThermBus),
        **{cv.Optional(key): schema for key, schema in TEXT_SENSORS.items()},
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_THERM_BUS_ID])
    for key in TEXT_SENSORS:
        if key in config:
            sens = await text_sensor.new_text_sensor(config[key])
            cg.add(getattr(hub, f"set_{key}_text_sensor")(sens))
