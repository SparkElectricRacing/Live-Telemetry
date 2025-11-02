""" 
App-level layout with tab navigation
"""

from dash import html, dcc
from tabs import tab_dashboard
def create_app_layout():
    """Create the overall app layout with tabs"""
    return html.Div([
        dcc.Store(id='page-load-trigger', data=0),
        dcc.Tabs(
            id="tabs",
            value="dashboard",  # default selected tab
            children=[
                dcc.Tab(label="Live Dashboard", value="dashboard"),
                dcc.Tab(label="Log Analysis", value="analysis")
            ]
        ),
        html.Div(id="tabs-content")
    ])