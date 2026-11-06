"""Bosch Therm 5600 O remote bus (4800 8N1, F5/FA frames)."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart
from esphome.const import CONF_ID

DEPENDENCIES = ["uart"]

CONF_THERM_BUS_ID = "therm_bus_id"

therm_bus_ns = cg.esphome_ns.namespace("therm_bus")
ThermBus = therm_bus_ns.class_("ThermBus", cg.Component, uart.UARTDevice)

CONFIG_SCHEMA = (
    cv.Schema({cv.GenerateID(): cv.declare_id(ThermBus)})
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)

FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "therm_bus", baud_rate=4800, require_rx=True
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
