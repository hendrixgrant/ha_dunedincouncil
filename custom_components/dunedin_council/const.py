"""Constants for the Dunedin City Council integration."""

from datetime import timedelta

DOMAIN = "dunedin_council"

# DCC's public ArcGIS layer behind the "Kerbside collection days" search on
# dunedin.govt.nz. Layer 1 = all properties (incl. those with no collection).
API_URL = (
    "https://apps.dunedin.govt.nz/arcgis/rest/services/Public/"
    "Refuse_Collection_Property/MapServer/1/query"
)
USER_AGENT = "HomeAssistant-dunedin_council (custom integration)"

CONF_ADDRESS = "address"
CONF_PROPERTY_ID = "property_id"
CONF_TERTIARY = "tertiary"
CONF_SWAP_WEEKS = "swap_weeks"

# The council's data only changes around local midnight; no need to poll hard.
SCAN_INTERVAL = timedelta(hours=6)
REQUEST_TIMEOUT = 20
