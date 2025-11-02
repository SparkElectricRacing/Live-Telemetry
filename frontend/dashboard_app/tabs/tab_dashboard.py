"""
Dashboard layout components
"""

import dash
from dash import html, dcc

from config import UPDATE_INTERVAL


def layout():
    """Layout for Live Dashboard tab"""
    return html.Div([   # main container 
        # Top row with logo, title, and control panel
        html.Div([
            # Left side: Logo
            html.Div([
                html.Img(
                    src="/assets/spark-logo.png",
                    alt="SPARK Electric Racing",
                    className="brand-logo"
                )
            ], className="header-left"),
            
            # Center: Title
            html.Div([
                html.H1("Live Telemetry Dashboard", className="header-title")
            ], className="header-center"),
            
            # Right side: Control Panel (boxed)
            html.Div([
                html.H3("Control Panel", className="control-panel-title"),
                html.Div([
                    html.Div(id="connection-status", className="status-indicator"),
                    html.Div([
                        html.Label("Data Source:", className="control-label"),
                        dcc.Dropdown(
                            id="data-mode-selector",
                            options=[
                                {"label": "Mock Data", "value": "mock"},
                                {"label": "Live API", "value": "live"}
                            ],
                            value="mock",
                            className="data-mode-dropdown"
                        )
                    ], className="mode-selector"),
                    html.Div([
                        html.Button("Start", id="start-btn", n_clicks=0, className="control-btn start-btn"),
                        html.Button("Stop", id="stop-btn", n_clicks=0, className="control-btn stop-btn")
                    ], className="control-buttons")
                ], className="control-panel-content"),
                html.Div(id="error-notification", className="error-notification hidden")
            ], className="control-panel-box")
        ], className="top-row"),
        
        # Main dashboard content
        html.Div([
            # Row 1: Speed and Battery Voltage
            html.Div([
                html.Div([
                    dcc.Graph(id="speed-gauge"),
                ], className="gauge-container"),
                html.Div([
                    dcc.Graph(id="voltage-gauge"),
                    html.Div(id="voltage-status-indicator") 
                ], className="gauge-container"),
            ], className="gauge-row"),
            
            # Row 2: SOC and Temperature Overview
            html.Div([
                html.Div([
                    dcc.Graph(id="soc-gauge"),
                    html.Div(id="soc-status-indicator")
                ], className="gauge-container"),
                html.Div([
                    dcc.Graph(id="temp-overview"),
                    html.Button("Switch to Time Series", id="toggle-temp-chart-btn", n_clicks=0, className="control-btn small")
                ], className="chart-container")
            ], className="mixed-row"),
            
            # Row 3: Time Series Charts
            html.Div([
                html.Div([
                    dcc.Graph(id="speed-timeseries"),
                ], className="chart-container-full"),
            ], className="chart-row"),
            
            html.Div([
                html.Div([
                    dcc.Graph(id="voltage-timeseries"),
                ], className="chart-container"),
                html.Div([
                    dcc.Graph(id="soc-timeseries"),
                ], className="chart-container"),
            ], className="chart-row"),
        ], className="dashboard-content"),

        dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),
        dcc.Store(id='telemetry-store'),
        dcc.Store(id='page-load-trigger', data=0),  # Trigger initial load
        dcc.Store(id='file-action-store'),
        dcc.Store(id='selected-log-for-summary'),  # Store for selected log file
        html.Div(id='delete-trigger', style={'display': 'none'})
    ], className="main-container")