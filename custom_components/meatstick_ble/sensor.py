"""MeatStick BLE sensors."""

from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import UnitOfTemperature, CONF_PLATFORM
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_ADDRESS, CONF_NAME

_LOGGER = logging.getLogger(__name__)

# YAML config:
# sensor:
#   - platform: meatstick_ble
#     address: "40:51:6C:09:A2:00"
#     name: "MeatStick Yellow"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ADDRESS): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info: Dict[str, Any] | None = None,
) -> None:
    """Set up a MeatStick BLE sensor from YAML."""
    address = config[CONF_ADDRESS].upper()
    name = config.get(CONF_NAME, f"MeatStick {address}")

    _LOGGER.debug("Setting up MeatStick BLE sensor for %s", address)
    async_add_entities([MeatStickTemperatureSensor(address, name)])


class MeatStickTemperatureSensor(SensorEntity):
    """Temperature sensor based on MeatStick BLE advertisements."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, address: str, name: str) -> None:
        """Initialize the sensor."""
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{address}_temperature"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Register Bluetooth callback when entity is added."""

        @callback
        def _async_handle_ble_event(
            service_info: BluetoothServiceInfoBleak,
            change: BluetoothChange,
        ) -> None:
            """Handle BLE advertisements."""
            # Extra guard, even though matcher already filters by address
            if service_info.address.upper() != self._address:
                return

            temp = self._parse_temperature_from_advertisement(service_info)
            if temp is None:
                return

            # Update state
            if temp != self._attr_native_value:
                _LOGGER.debug(
                    "MeatStick %s temperature update: %s °C (RSSI %s)",
                    self._address,
                    temp,
                    service_info.rssi,
                )
                self._attr_native_value = temp
                self.async_write_ha_state()

        # Register callback, filtered by the specific MAC
        cancel = bluetooth.async_register_callback(
            self.hass,
            _async_handle_ble_event,
            {
                "address": self._address,
                # MeatStick advertisements come from non connectable devices
                # set to False so we also get ads via BLE proxies
                "connectable": False,
            },
            BluetoothScanningMode.ACTIVE,
        )

        # Ensure callback is removed when entity is removed
        self.async_on_remove(cancel)

    def _parse_temperature_from_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> float | None:
        """Extract temperature from MeatStick BLE payload.

        This is a placeholder. You will replace the parsing logic
        based on the real service_data / manufacturer_data format.
        """

        # service_info.manufacturer_data: dict[int, bytes]
        # service_info.service_data: dict[str, bytes]
        # service_info.service_uuids: list[str]

        # Example strategy:
        # 1. Take the first service_data value
        # 2. Assume bytes 2-3 (big endian) are temperature * 10
        if not service_info.service_data:
            return None

        # Grab first service_data payload
        payload = next(iter(service_info.service_data.values()))

        if not payload or len(payload) < 4:
            return None

        # Example decoding: bytes[2:4] as big endian, divide by 10
        raw = int.from_bytes(payload[2:4], byteorder="big", signed=False)
        temp_c = raw / 10.0

        return float(temp_c)
