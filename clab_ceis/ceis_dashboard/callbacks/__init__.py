from ceis_dashboard.callbacks.co2 import register_co2_callbacks
from ceis_dashboard.callbacks.dashboard_table import register_dashboard_table_callbacks
from ceis_dashboard.callbacks.fabric_blocks import register_fabric_block_callbacks
from ceis_dashboard.callbacks.recipe_types import register_recipe_type_callbacks

__all__ = [
    "register_co2_callbacks",
    "register_dashboard_table_callbacks",
    "register_fabric_block_callbacks",
    "register_recipe_type_callbacks",
]
