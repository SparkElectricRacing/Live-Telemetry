"""
Dashboard layout components
"""

import dash
from dash import html, dcc
import dash_leaflet as dl
import uuid  # <-- Import uuid

from config import UPDATE_INTERVAL

# --- NEW: Configuration for Dynamic Layout ---
# NOTE: These variables MUST match the keys in your telemetry.py/callbacks.py store
AVAILABLE_VARIABLES = {
    'speedMPH': 'Vehicle Speed (mph)',
    'pack_voltage': 'Battery Voltage (V)',
    'pack_SOC': 'Battery SOC (%)',
    'avg_temp': 'Avg Cell Temp (°C)',
    'max_cell_temp': 'Max Cell Temp (°C)',
    'rpm_speed': 'RPM Speed',
    'avg_cell_voltage': 'Avg Cell Voltage (V)',
    'low_cell_voltage': 'Min Cell Voltage (V)',
    'high_cell_voltage': 'Max Cell Voltage (V)',
    'is_charging': 'Is Charging (Bool)',
    'DTC1': 'DTC Code'
}
AVAILABLE_CHARTS = {'gauge': 'Gauge', 'timeseries': 'Time Series', 'bar': 'Bar (Current)'}
initial_layout_config = {
    'rows': [
        {'id': str(uuid.uuid4()), 'columns': [
            {'id': str(uuid.uuid4()), 'variable': 'speedMPH', 'chart': 'gauge'},
            {'id': str(uuid.uuid4()), 'variable': 'pack_voltage', 'chart': 'gauge'}
        ]},
        {'id': str(uuid.uuid4()), 'columns': [
            {'id': str(uuid.uuid4()), 'variable': 'pack_SOC', 'chart': 'timeseries'}
        ]}
    ]
}
# --- End of New Configuration ---


def create_dashboard_layout():
    """Create the main dashboard layout"""
    
    # This is your entire original layout, now inside a variable
    static_dashboard_content = html.Div([
        # DTC Alert Section
        html.Div(id="dtc-alert", className="dtc-alert hidden"),

        # GPS Map Section (Moved to Top)
        html.Div([
            html.H3("GPS Location", className="section-title"),
            html.Div([
                dl.Map(center=[33.53250, -86.61889], zoom=15, children=[
                    dl.TileLayer(),
                    dl.DivMarker(
                        position=[33.53250, -86.61889], 
                        id="gps-marker", 
                        iconOptions={
                            "className": "gps-puck-wrapper",
                            "html": '<div class="gps-puck"></div>',
                            "iconSize": [24, 24],
                            "iconAnchor": [12, 12]
                        },
                        children=[
                            dl.Tooltip("Current Location")
                        ]
                    )
                ], style={'width': '100%', 'height': '400px'}, id="gps-map"),
            ], className="map-container")
        ], className="map-section"),

        # Row 1: Speed, RPM, and Battery Voltage
        html.Div([
            html.Div([
                dcc.Graph(id="speed-gauge"),
            ], className="gauge-container"),
            html.Div([
                dcc.Graph(id="rpm-gauge"),
            ], className="gauge-container"),
            html.Div([
                dcc.Graph(id="voltage-gauge"),
                html.Div(id="voltage-status-indicator") 
            ], className="gauge-container"),
        ], className="gauge-row"),
        
        # Row 2: SOC, Cell Voltages, and Temperature Overview
        html.Div([
            html.Div([
                dcc.Graph(id="soc-gauge"),
                html.Div(id="soc-status-indicator")
            ], className="gauge-container"),
            html.Div([
                dcc.Graph(id="cell-voltage-chart"),
            ], className="chart-container"),
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
        
                # Log Management Section - REMOVED (Moved to Control Panel)

                # Log Management Section - REMOVED (Moved to Control Panel)
    ], className="dashboard-content")
    
    
    # --- NEW: Main layout with Tabs ---
    return html.Div([   # main container 
        # Top row with logo, title, and control panel (from your original layout.py)
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
                    html.Div(id="charging-status-indicator", className="status-indicator", style={'marginLeft': '10px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '15px'}),
                    
                    # Data Source Selection
                    html.Div([
                        html.Label("Data Source:", className="control-label"),
                        dcc.Dropdown(
                            id="data-mode-selector",
                            options=[
                                {"label": "Mock Data", "value": "mock"},
                                {"label": "Live API", "value": "live"}
                            ],
                            value="mock",
                            className="data-mode-dropdown",
                            clearable=False
                        )
                    ], className="mode-selector", style={'marginBottom': '15px', 'justifyContent': 'center'}),
                    
                    # Connection Actions
                    html.Div([
                        html.Button("Start", id="start-btn", n_clicks=0, className="control-btn start-btn"),
                        html.Button("Stop", id="stop-btn", n_clicks=0, className="control-btn stop-btn")
                    ], className="control-buttons", style={'justifyContent': 'center', 'marginBottom': '15px'}),
                    
                    # Manager Button
                    html.Div([
                         html.Button("Manage Logs ▼", id="manage-logs-btn", n_clicks=0, className="control-btn", style={'marginTop': '10px', 'width': '100%', 'backgroundColor': '#34495e', 'color': 'white'})
                    ], className="control-buttons", style={'justifyContent': 'center'}),
                    

                html.Div(id="error-notification", className="error-notification hidden"),

                # --- Collapsible Log Management Dropdown ---
                html.Div(id="log-management-dropdown", children=[
                    html.Div([
                        html.H4("Log Management", className="section-title", style={'marginBottom': '10px', 'fontSize': '1.2em'}),
                        
                        # Unified Log Management
                        html.Div([
                            html.H5("Log File & Actions", className="section-title"),
                            
                            # Single File Selection
                            html.Div([
                                html.Label("Select Log File:", className="control-label"),
                                dcc.Dropdown(
                                    id="selected-log-file", 
                                    placeholder="Choose log file...",
                                    className="playback-dropdown"
                                )
                            ], className="playback-action-section", style={'marginBottom': '15px'}),
                            
                            # File Actions Row
                            html.Div([
                                html.Button("Delete", id="delete-file-btn", n_clicks=0, className="file-action-btn delete-btn"),
                                dcc.Input(id="new-name-input", type="text", placeholder="New Name", className="file-input", style={'width': '120px'}),
                                html.Button("Rename", id="rename-file-btn", n_clicks=0, className="file-action-btn rename-btn"),
                                html.Button("Delete All", id="delete-all-btn", n_clicks=0, className="file-action-btn delete-all-btn", style={'marginLeft': 'auto'})
                            ], className="file-action-row", style={'marginBottom': '20px', 'display': 'flex', 'gap': '10px', 'alignItems': 'center'}),
                            
                            html.Div(id="file-operation-status", className="operation-status", style={'marginBottom': '15px'}),

                            html.Hr(style={'borderColor': 'rgba(255,255,255,0.1)', 'margin': '0 0 15px 0'}),

                            html.H5("Playback Controls", className="playback-actions-title"),

                            
                            # Control Buttons Section
                            html.Div([
                                html.Label("Speed:", className="playback-action-label", style={'marginRight': '10px'}),
                                dcc.Dropdown(
                                    id="playback-speed-selector",
                                    options=[
                                        {'label': 'Real-time (Fast)', 'value': 'fast'},
                                        {'label': 'Slow (100ms)', 'value': 'slow'},
                                    ],
                                    value='slow',  # Default to slow
                                    clearable=False,
                                    className="playback-dropdown",
                                    style={'width': '150px'}
                                ),
                            ], className="playback-action-section", style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),

                            # Control Buttons Section
                            html.Div([
                                html.Button("⏮", id="prev-step-btn", n_clicks=0, className="playback-action-btn control-btn small", title="Previous Frame", disabled=True),
                                html.Button("Play", id="play-btn", n_clicks=0, className="playback-action-btn play-btn"),
                                html.Button("Pause", id="pause-btn", n_clicks=0, className="playback-action-btn pause-btn"),
                                html.Button("Stop", id="stop-playback-btn", n_clicks=0, className="playback-action-btn stop-btn"),
                                html.Button("⏭", id="next-step-btn", n_clicks=0, className="playback-action-btn control-btn small", title="Next Frame", disabled=True),
                            ], className="playback-button-row"),
                            
                            # Scrubber Slider
                            html.Div([
                                dcc.Slider(
                                    id='playback-slider',
                                    min=0,
                                    max=100, # Will be updated dynamically
                                    step=1,
                                    value=0,
                                    marks=None, # Too cluttered for large files
                                    tooltip={"placement": "bottom", "always_visible": True},
                                    updatemode='drag',
                                    disabled=True
                                )
                            ], style={'marginTop': '20px', 'padding': '0 10px'}),
                            
                            html.Div([
                                html.Span("Frame: ", className="playback-status-label"),
                                dcc.Input(
                                    id="playback-frame-input",
                                    type="number",
                                    placeholder="0",
                                    value=0,
                                    min=0,
                                    step=1,
                                    className="playback-frame-input",
                                    style={'width': '70px', 'marginRight': '5px', 'textAlign': 'right'}
                                ),
                                html.Span("/ 0", id="playback-total-frames", className="playback-total-label"),
                                html.Span("", id="playback-status", style={'marginLeft': '10px', 'fontStyle': 'italic'}) # Status text like "Playing", "Paused"
                            ], className="playback-status-display", style={'marginTop': '10px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
                        ], className="playback-management-actions")

                    ], style={'maxHeight': '600px', 'overflowY': 'auto'})
                ], style={
                    'display': 'none', 
                    'position': 'absolute', 
                    'top': '100%', 
                    'right': '0', 
                    'width': '600px', 
                    'backgroundColor': '#1e2329', 
                    'border': '1px solid #ffd700', 
                    'borderRadius': '10px', 
                    'padding': '15px', 
                    'zIndex': '1000',
                    'boxShadow': '0 10px 30px rgba(0,0,0,0.5)'
                })
            ], className="control-panel-box", style={'position': 'relative'}), # Added relative positioning to parent
        ], className="top-row"),
        
        # --- NEW: Tabs to switch views ---
        dcc.Tabs(id="dashboard-tabs", value='tab-static', className='custom-tabs', children=[
            dcc.Tab(label='Static Dashboard', value='tab-static', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='Custom Dashboard', value='tab-custom-view', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='Layout Editor', value='tab-editor', className='custom-tab', selected_className='custom-tab--selected'),
        ]),

        # --- Content Containers (Controlled by Callback) ---
        html.Div(id='static-dashboard-container', children=[static_dashboard_content]),
        html.Div(id='custom-dashboard-view-container', className="dashboard-content"),
        html.Div(id='layout-editor-container', className="layout-editor-content"),

        # --- Interval and Stores (some are new) ---
        dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),
        dcc.Store(id='telemetry-store'),
        dcc.Store(id='page-load-trigger', data=0),  # Trigger initial load
        dcc.Store(id='file-action-store'),
        dcc.Store(id='selected-log-for-summary'),  # Store for selected log file
        html.Div(id='delete-trigger', style={'display': 'none'}),
        
        # --- NEW: Store and Download for Layout Editor ---
        dcc.Store(id='layout-config-store', data=initial_layout_config, storage_type='session'),
        dcc.Download(id="download-layout-json"),
        
    ], className="main-container")