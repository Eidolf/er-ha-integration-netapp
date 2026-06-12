"""Constants for the NetApp ONTAP integration."""

DOMAIN = "netapp_ontap"

PLATFORMS = ["sensor", "binary_sensor", "switch", "button"]

DEFAULT_PORT = 443
DEFAULT_UPDATE_INTERVAL = 30

CONF_VERIFY_SSL = "verify_ssl"
CONF_API_TOKEN = "api_token"
CONF_DETAIL_LEVEL = "detail_level"

DETAIL_LEVEL_STANDARD = "standard"
DETAIL_LEVEL_ADVANCED = "advanced"
DETAIL_LEVEL_ALL = "all"

ATTR_CLUSTER_NAME = "cluster_name"
ATTR_VOLUME_NAME = "volume_name"
ATTR_NODE_NAME = "node_name"
ATTR_AGGREGATE_NAME = "aggregate_name"
