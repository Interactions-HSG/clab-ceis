from dash import Dash

from clab_ceis.ceis_dashboard import ceis_data
from clab_ceis.ceis_dashboard.callbacks import (
    register_co2_callbacks,
    register_dashboard_table_callbacks,
    register_fabric_block_callbacks,
)


def get_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    register_fabric_block_callbacks(app, data)
    register_dashboard_table_callbacks(app, data)
    register_co2_callbacks(app, data)
