import dash
from dash import html, dcc
from config import UPDATE_INTERVAL

def layout():
    return html.Div([ 
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
            # Title and instruction on same line
            html.Div([
                html.H3("Log File Analysis", className="section-title", style={"display": "inline-block", "margin-right": "20px", "margin-bottom": "0"}),
                html.P("Click on a log file above to view detailed analysis and summary statistics",
                    className="summary-instruction", style={"display": "inline-block", "margin-bottom": "0"})
            ], style={"margin-bottom": "20px"}),

            # Summary Statistics Cards
            html.Div(id="summary-stats-container", className="summary-stats-container"),

            # Summary Plots
            html.Div([
                dcc.Graph(id="summary-timeseries-plot")
            ], className="chart-container-full", id="summary-plot-container")
        ], className="log-summary-section", id="log-summary-section")
    ], className="main-container")