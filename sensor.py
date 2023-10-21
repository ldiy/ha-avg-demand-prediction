"""Platform for sensor integration."""
from __future__ import annotations
import voluptuous as vol
from collections import deque
import logging
import numpy as np
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    PLATFORM_SCHEMA,
    ENTITY_ID_FORMAT,
)
from homeassistant.const import (
    CONF_NAME,
    UnitOfPower,
    UnitOfTime,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, EventType
import homeassistant.helpers.config_validation as cv
from homeassistant.util.dt import utcnow

__LOGGER = logging.getLogger(__name__)

CONF_CURRENT_AVG_DEMAND_SENSOR = "current_avg_demand_sensor"
CONF_POWER_CONSUMED_SENSOR = "power_consumed_sensor"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_CURRENT_AVG_DEMAND_SENSOR): cv.entity_id,
        vol.Optional(CONF_POWER_CONSUMED_SENSOR): cv.entity_id,
        vol.Optional(CONF_NAME): cv.string,
    }
)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
) -> None:
    # Set up the sensor platform.
    avg_demand_prediction = AvgDemandPredictionSensor(
        hass,
        name=config.get(CONF_NAME),
        current_avg_demand_sensor=config.get(CONF_CURRENT_AVG_DEMAND_SENSOR),
    )
    async_add_entities([avg_demand_prediction])


class AvgDemandPredictionSensor(SensorEntity):

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER

    def __init__(
            self,
            hass: HomeAssistant,
            name: str | None,
            current_avg_demand_sensor: str,
    ) -> None:
        self.current_avg_demand_sensor = current_avg_demand_sensor
        self.__attr_name = name if name is not None else f"{current_avg_demand_sensor} prediction"
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, name, hass=hass)
        self.samples: deque = deque(maxlen=900)
        self.prediction: float | None = None


    async def async_added_to_hass(self) -> None:
        # Complete device setup after being added to hass.
        global __LOGGER
        @callback
        def sensor_state_listener(
                event: EventType[EventStateChangedData],
        ) -> None:
            # Handle state changes on the input sensor.
            if (new_state := event.data.get("new_state")) is None:
                return
            try:
                if new_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    sample = (new_state.last_updated.timestamp(), float(new_state.state))
                    self.samples.append(sample)
                    self.async_schedule_update_ha_state(True)
            except (ValueError, TypeError) as err:
                __LOGGER.error(
                    "Unable to update sensor %s from %s: %s",
                    self.entity_id,
                    new_state.entity_id,
                    err,
                )

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.current_avg_demand_sensor], sensor_state_listener
            )
        )

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        if len(self.samples) <  2:
            return

        # Calculate the prediction
        await self.hass.async_add_executor_job(self._calc_prediction)
        self._attr_native_value = round(self.prediction, 3)


    def _calc_prediction(self) -> None:
        if len(self.samples) > 0:
            # Get the current time
            current_time = utcnow().timestamp()

            # Get the timestamp of the start of this quarter-hour
            quarter_hour_start = current_time - (current_time % 900)

            # Get the timestamp of the end of this quarter-hour
            quarter_hour_end = quarter_hour_start + 900

            # Get the samples that fall within this quarter-hour
            samples_in_quarter_hour = [sample for sample in self.samples if
                                       quarter_hour_start <= sample[0] < quarter_hour_end]

            # Calculate the regression line (what will the value be at the end of the quarter-hour)
            if len(samples_in_quarter_hour) > 1:
                x = np.array([sample[0] for sample in samples_in_quarter_hour])
                y = np.array([sample[1] for sample in samples_in_quarter_hour])
                m, b = np.polyfit(x, y, 1)
                self.prediction = m * quarter_hour_end + b
            else:
                self.prediction = None
        else:
            self.prediction = None