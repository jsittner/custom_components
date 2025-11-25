"""MeatStick BLE custom integration."""

from __future__ import annotations

import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the MeatStick BLE integration from YAML."""
    # Nothing global to do. Sensor platform is set up by sensor.py
    _LOGGER.debug("Setting up %s from YAML", DOMAIN)
    return True
