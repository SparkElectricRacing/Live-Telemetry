"""
Dashboard layout components
"""

import dash
from dash import html, dcc

from config import UPDATE_INTERVAL


def create_dashboard_layout():
    """Create the main dashboard layout"""
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
                                {"label": "Mock", "value": "mock"},
                                {"label": "Live", "value": "live"}, 
                                {"label": "Playback", "value": "playback"}
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
            
            # Log Management Section
            html.Div([
                html.H3("Log Management", className="section-title"),
                html.Div([
                    html.Div([
                        html.H4("Available Log Files"),
                        html.Div(id="log-files-list"),
                        html.Div([
                            dcc.Input(id="file-operation-input", type="text", placeholder="Enter filename to delete/rename", style={"width": "200px"}),
                            html.Button("Delete", id="delete-file-btn", n_clicks=0, className="control-btn stop-btn"),
                            html.Button("Rename", id="rename-file-btn", n_clicks=0, className="control-btn"),
                            dcc.Input(id="new-name-input", type="text", placeholder="New name", style={"width": "150px"}),
                            html.Button("Delete All", id="delete-all-btn", n_clicks=0, className="control-btn stop-btn", 
                                      style={"margin-left": "20px", "background-color": "#8B0000"})
                        ], className="file-operations", style={"margin-top": "10px"}),
                        html.Div(id="file-operation-status", className="operation-status")
                    ], className="log-list-container"),
                    html.Div([
                        html.H4("Playback Controls"),
                        html.Div([
                            html.P("Set 'Data Source' to '▶️ Playback' mode above, then select a log file:", 
                                   style={"color": "#95a5a6", "font-style": "italic", "margin-bottom": "10px"}),
                            dcc.Dropdown(id="selected-log-file", placeholder="Select a log file for playback"),
                            html.Div([
                                html.Button("Play", id="play-btn", n_clicks=0, className="control-btn start-btn"),
                                html.Button("Pause", id="pause-btn", n_clicks=0, className="control-btn"),
                                html.Button("Stop", id="stop-playback-btn", n_clicks=0, className="control-btn stop-btn"),
                            ], className="playback-controls"),
                            html.Div(id="playback-status", className="playback-status")
                        ])
                    ], className="playback-container")
                ], className="log-management-row")
            ], className="log-management-section")
        ], className="dashboard-content"),
        
        dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),
        dcc.Store(id='telemetry-store'),
        dcc.Store(id='page-load-trigger', data=0),  # Trigger initial load
        dcc.Store(id='file-action-store'),
        html.Div(id='delete-trigger', style={'display': 'none'})
    ], className="main-container")