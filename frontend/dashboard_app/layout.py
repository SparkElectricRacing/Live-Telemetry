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
            
            # Log Management Section
            html.Div([
                html.H3("Log Management", className="section-title"),
                html.Div([
                    html.Div([
                        html.H4("Available Log Files"),
                        html.Div(id="log-files-list"),
                        # File Management Actions
                        html.Div([
                            html.H5("File Actions", className="file-actions-title"),
                            
                            # File Selection Section
                            html.Div([
                                html.Label("Select File:", className="file-action-label"),
                                dcc.Dropdown(
                                    id="selected-file-for-action", 
                                    placeholder="Choose a file to delete or rename",
                                    className="file-selection-dropdown"
                                )
                            ], className="file-action-section"),
                            
                            # Delete Single File Section
                            html.Div([
                                html.Label("Delete Selected File:", className="file-action-label"),
                                html.Div([
                                    html.Button("Delete Selected File", id="delete-file-btn", n_clicks=0, className="file-action-btn delete-btn", style={"width": "100%"})
                                ], className="file-action-row")
                            ], className="file-action-section"),
                            
                            # Rename File Section
                            html.Div([
                                html.Label("Rename Selected File:", className="file-action-label"),
                                html.Div([
                                    dcc.Input(
                                        id="new-name-input", 
                                        type="text", 
                                        placeholder="Enter new filename", 
                                        className="file-input"
                                    ),
                                    html.Button("Rename", id="rename-file-btn", n_clicks=0, className="file-action-btn rename-btn")
                                ], className="file-action-row")
                            ], className="file-action-section"),
                            
                            # Delete All Section
                            html.Div([
                                html.Button("Delete All Files", id="delete-all-btn", n_clicks=0, className="file-action-btn delete-all-btn")
                            ], className="file-action-section"),
                            
                            html.Div(id="file-operation-status", className="operation-status")
                        ], className="file-management-actions")
                    ], className="log-list-container"),
                    html.Div([
                        html.H4("Playback Controls"),
                        
                        # Playback Actions
                        html.Div([
                            html.H5("Playback Actions", className="playback-actions-title"),
                            
                            # Instructions
                            html.Div([
                                html.P("Select a log file and click Play to replay recorded telemetry data:",
                                       className="playback-instruction")
                            ], className="playback-instruction-section"),
                            
                            # File Selection Section
                            html.Div([
                                html.Label("Select Log File:", className="playback-action-label"),
                                dcc.Dropdown(
                                    id="selected-log-file", 
                                    placeholder="Choose a log file for playback",
                                    className="playback-dropdown"
                                )
                            ], className="playback-action-section"),
                            
                            # Control Buttons Section
                            html.Div([
                                html.Label("Playback Controls:", className="playback-action-label"),
                                html.Div([
                                    html.Button("Play", id="play-btn", n_clicks=0, className="playback-action-btn play-btn"),
                                    html.Button("Pause", id="pause-btn", n_clicks=0, className="playback-action-btn pause-btn"),
                                    html.Button("Stop", id="stop-playback-btn", n_clicks=0, className="playback-action-btn stop-btn"),
                                ], className="playback-button-row")
                            ], className="playback-action-section"),
                            
                            # Status Section
                            html.Div([
                                html.Div(id="playback-status", className="playback-status-display")
                            ], className="playback-status-section")
                        ], className="playback-management-actions")
                    ], className="playback-container")
                ], className="log-management-row")
            ], className="log-management-section"),

            # Log File Summary Section
            html.Div([
                html.H3("Log File Analysis", className="section-title"),
                html.Div([
                    html.P("Click on a log file above to view detailed analysis and summary statistics",
                           className="summary-instruction")
                ], className="summary-instruction-section"),

                # Summary Statistics Cards
                html.Div(id="summary-stats-container", className="summary-stats-container"),

                # Summary Plots
                html.Div([
                    dcc.Graph(id="summary-timeseries-plot")
                ], className="chart-container-full", id="summary-plot-container")
            ], className="log-summary-section", id="log-summary-section")
        ], className="dashboard-content"),

        dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),
        dcc.Store(id='telemetry-store'),
        dcc.Store(id='page-load-trigger', data=0),  # Trigger initial load
        dcc.Store(id='file-action-store'),
        dcc.Store(id='selected-log-for-summary'),  # Store for selected log file
        html.Div(id='delete-trigger', style={'display': 'none'})
    ], className="main-container")