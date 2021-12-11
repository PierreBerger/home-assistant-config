"""support for TAG transport API"""
from datetime import timedelta, datetime
import logging

from metromobilite import Metromobilite

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    HTTP_OK,
    STATE_UNKNOWN,
    TIME_MINUTES,
    ATTR_ATTRIBUTION,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.exceptions import PlatformNotReady

_LOGGER = logging.getLogger(__name__)

ATTR_STOP_ID = "stop_id"
ATTR_DESTINATION = "destination"
ATTR_NEXT = "next"
ATTR_NAME = "name"

CONF_NAME = "name"
CONF_STOP_ID = "stop_id"
CONF_ROUTE = "route"
CONF_ROUTES = "routes"
CONF_MODE = "mode"
MODE_DELAY = "delay"
MODE_HOUR = "hour"
DEFAULT_MODE = MODE_DELAY

ATTRIBUTION = "Data provided by data.metromobilite.fr"

TRAM_ROUTES = ['SEM:A', 'SEM:B', 'SEM:C', 'SEM:D', 'SEM:E']
TRAM_ICON = 'mdi:tram'
BUS_ICON = 'mdi:bus'

SCAN_INTERVAL = timedelta(seconds=60)

ROUTE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID): cv.string,
        vol.Required(CONF_ROUTE): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_MODE, default=DEFAULT_MODE): vol.In([MODE_DELAY, MODE_HOUR]),
    }
)

ROUTES_SCHEMA = vol.All(cv.ensure_list, [ROUTE_SCHEMA])

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ROUTES): ROUTES_SCHEMA
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Transport TAG sensor."""
    stop_id = config.get(CONF_STOP_ID)
    route = config.get(CONF_ROUTE)
    name = config.get(CONF_NAME)
    mode = config.get(CONF_MODE)

    client = Metromobilite()

    if client is None:
         raise PlatformNotReady

    sensors = []
    for route in config.get(CONF_ROUTES):
        sensors.append(
            MetromobiliteTransportSensor(
                client,
                route.get(CONF_STOP_ID),
                route.get(CONF_ROUTE),
                route.get(CONF_NAME),
                route.get(CONF_MODE),
            )
        )
    if sensors:
        add_entities(sensors, True)

def due_in_minutes(timestamp):
    """Get the time in minutes from a timestamp"""
    minutes = round((datetime.fromtimestamp(timestamp) - datetime.now()).total_seconds()/60)
    return 0 if minutes < 0 else minutes

def compute_hour(timestamp):
    return  datetime.fromtimestamp(timestamp).strftime("%H:%M")


class MetromobiliteTransportSensor(Entity):

    def __init__(self, client, stop_id, route, name, mode):
        self._client = client
        self._stop_id = stop_id
        self._route = route
        self._name = name
        self._mode = mode
        self._state = None
        self._trips = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._state != None:
            return self._state

    @property
    def icon(self):
        """Return the icon for the frontend"""
        if self._route in TRAM_ROUTES:
            return TRAM_ICON
        else:
            return BUS_ICON

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""

        attributes = {
            ATTR_NAME: self._name,
            ATTR_DESTINATION: STATE_UNKNOWN,
            ATTR_NEXT: STATE_UNKNOWN,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        } 

        for trip in self._trips:
            pattern = trip["pattern"]
            times = trip["times"]

            if self._route in pattern["id"]:               
                attributes[ATTR_DESTINATION] = pattern["desc"]
                if len(times) > 1:
                    timestamp = times[1]["scheduledArrival"] + times[1]["serviceDay"]
                    attributes[ATTR_NEXT] = due_in_minutes(timestamp) if self._mode == "delay" else compute_hour(timestamp)
                    return attributes         
        
        return attributes        

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        if self._mode == MODE_DELAY:
            return TIME_MINUTES

    @Throttle(SCAN_INTERVAL)
    def update(self):
        trips = self._client.get_stoptimes(self._stop_id)

        if len(trips) == 0 or not trips:
            self._state = STATE_UNKNOWN
            return

        for trip in trips:
            pattern = trip["pattern"]
            times = trip["times"]

            if self._route in pattern["id"] and len(times) > 1:
                timestamp = times[0]["scheduledArrival"] + times[0]["serviceDay"]
                self._state = due_in_minutes(timestamp) if self._mode == "delay" else compute_hour(timestamp)

        self._trips = trips