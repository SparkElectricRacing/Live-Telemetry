import dash
from dash import dcc, html, Input, Output, callback, State, ALL, MATCH, ctx
from dash.dependencies import State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import requests 
import threading
import queue
import time
from datetime import datetime, timedelta
import logging
import os
import pathlib
import uuid

# --- Original Configuration and TelemetryReceiver Class (Unchanged) ---
API_ENDPOINT = 'http://localhost:5000/api/telemetry'
API_TIMEOUT = 2
API_POLL_RATE = 0.05
LOG_DIRECTORY = 'telemetry_logs'
UPDATE_INTERVAL = 50
CHART_FONT = 'Arial'
CHART_FONT_SIZE = 12
TITLE_FONT_SIZE = 16
BORDER_RADIUS = 20
MAX_POINTS = 100
initial_data = {
    'timestamp': [datetime.now().isoformat()] * MAX_POINTS,
    'vehicle_speed': [0] * MAX_POINTS,
    'battery_voltage': [0] * MAX_POINTS,
    'battery_soc': [0] * MAX_POINTS,
    'min_cell_temp': [0] * MAX_POINTS,
    'max_cell_temp': [0] * MAX_POINTS,
    'inverter_temp': [0] * MAX_POINTS
}
os.makedirs(LOG_DIRECTORY, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIRECTORY}/telemetry_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
class TelemetryReceiver:
    def __init__(self):
        self.data_queue = queue.Queue()
        self.api_available = False
        self.running = False
        self.mock_mode = True
        self.max_points = 100
        self.data_history = {'timestamp': [], 'vehicle_speed': [], 'battery_voltage': [], 'battery_soc': [], 'min_cell_temp': [], 'max_cell_temp': [], 'inverter_temp': []}
    def test_api_connection(self):
        try:
            response = requests.get(API_ENDPOINT, timeout=API_TIMEOUT)
            if response.status_code == 200:
                self.api_available = True
                self.mock_mode = False
                logging.info(f"Connected to API at {API_ENDPOINT}")
                return True
            else:
                logging.warning(f"API returned status code: {response.status_code}")
                return False
        except Exception as e:
            logging.warning(f"Failed to connect to API: {e}")
            logging.info("Running in mock mode")
            self.mock_mode = True
            self.api_available = False
            return False
    def generate_mock_data(self):
        import random
        now = datetime.now()
        data = {
            'timestamp': now.isoformat(), 'vehicle_speed': random.uniform(0, 120), 'battery_voltage': random.uniform(320, 400),
            'battery_soc': random.uniform(20, 100), 'min_cell_temp': random.uniform(20, 45), 'max_cell_temp': random.uniform(25, 50),
            'inverter_temp': random.uniform(30, 80)
        }
        return data
    def fetch_api_data(self):
        try:
            response = requests.get(API_ENDPOINT, timeout=API_TIMEOUT)
            response.raise_for_status()
            json_data = response.json()
            data = {
                'timestamp': json_data.get('timestamp', datetime.now().isoformat()), 'vehicle_speed': float(json_data.get('vehicle_speed', 0)),
                'battery_voltage': float(json_data.get('battery_voltage', 0)), 'battery_soc': float(json_data.get('battery_soc', 0)),
                'min_cell_temp': float(json_data.get('min_cell_temp', 0)), 'max_cell_temp': float(json_data.get('max_cell_temp', 0)),
                'inverter_temp': float(json_data.get('inverter_temp', 0))
            }
            if not data['timestamp']: data['timestamp'] = datetime.now().isoformat()
            return data
        except requests.exceptions.RequestException as e: logging.error(f"API request failed: {e}"); return None
        except (ValueError, KeyError) as e: logging.error(f"Error parsing API response: {e}"); return None
    def data_receiver_thread(self):
        while self.running:
            try:
                if self.mock_mode: data = self.generate_mock_data(); time.sleep(API_POLL_RATE)
                else:
                    data = self.fetch_api_data()
                    if data is None: time.sleep(1); continue
                    time.sleep(API_POLL_RATE)
                if data: self.data_queue.put(data)
            except Exception as e:
                logging.error(f"Error in data receiver: {e}"); time.sleep(1)
    def start(self):
        self.running = True; self.test_api_connection()
        self.thread = threading.Thread(target=self.data_receiver_thread, daemon=True)
        self.thread.start()
        logging.info("Telemetry receiver started")
    def stop(self): self.running = False; logging.info("Telemetry receiver stopped")

telemetry = TelemetryReceiver()
telemetry.start()
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Zephyrus Live Telemetry"

try:
    template_path = str(pathlib.Path(__file__).parent / "templates" / "index.html")
    with open(template_path, 'r') as f: app.index_string = f.read()
except FileNotFoundError:
    logging.warning("templates/index.html not found. Using default Dash index.")

# --- Configuration for Dynamic Layout ---
AVAILABLE_VARIABLES = {
    'vehicle_speed': 'Vehicle Speed (km/h)', 'battery_voltage': 'Battery Voltage (V)', 'battery_soc': 'Battery SOC (%)',
    'min_cell_temp': 'Min Cell Temp (°C)', 'max_cell_temp': 'Max Cell Temp (°C)', 'inverter_temp': 'Inverter Temp (°C)',
}
AVAILABLE_CHARTS = {'gauge': 'Gauge', 'timeseries': 'Time Series', 'bar': 'Bar (Current)'}
initial_layout_config = {
    'rows': [
        {'id': str(uuid.uuid4()), 'columns': [{'id': str(uuid.uuid4()), 'variable': 'vehicle_speed', 'chart': 'gauge'}, {'id': str(uuid.uuid4()), 'variable': 'battery_voltage', 'chart': 'gauge'}]},
        {'id': str(uuid.uuid4()), 'columns': [{'id': str(uuid.uuid4()), 'variable': 'battery_soc', 'chart': 'timeseries'}]}
    ]
}

# --- MODIFIED: App Layout now has 3 Tabs ---
app.layout = html.Div([
    html.Div([
        html.H1("Zephyrus Live Telemetry Dashboard", className="header-title"),
        html.Div([
            html.Div(id="connection-status", className="status-indicator"),
            html.Div(f"Mode: {'Mock Data' if telemetry.mock_mode else 'Live API'}", className="mode-indicator"),
            html.Div([
                html.Button("Stop Collection", id="stop-btn", n_clicks=0, className="control-btn stop-btn"),
                html.Button("Start Collection", id="start-btn", n_clicks=0, className="control-btn start-btn")
            ], className="control-buttons")
        ], className="status-bar"),
        html.Div(id="error-notification", className="error-notification hidden")
    ], className="header"),

    dcc.Store(id='layout-config-store', data=initial_layout_config, storage_type='session'),

    dcc.Tabs(id="dashboard-tabs", value='tab-static', children=[
        dcc.Tab(label='Static Dashboard', value='tab-static', children=[
            # --- ORIGINAL STATIC LAYOUT ---
            html.Div([
                html.Div([
                    html.Div([dcc.Graph(id="speed-gauge")], className="gauge-container"),
                    html.Div([dcc.Graph(id="voltage-gauge"), html.Div(id="voltage-status-indicator")], className="gauge-container"),
                ], className="gauge-row"),
                html.Div([
                    html.Div([dcc.Graph(id="soc-gauge"), html.Div(id="soc-status-indicator")], className="gauge-container"),
                    html.Div([
                        html.Div([html.Button("Switch to Time Series", id='toggle-temp-chart-btn', n_clicks=0)], className="chart-header"),
                        dcc.Graph(id="temp-overview"),
                    ], className="chart-container"),
                ], className="mixed-row"),
                html.Div([
                    html.Div([dcc.Graph(id="speed-timeseries")], className="chart-container"),
                    html.Div([dcc.Graph(id="battery-timeseries")], className="chart-container"),
                ], className="chart-row"),
                html.Div([html.Div([dcc.Graph(id="temperature-timeseries")], className="chart-container-full")], className="chart-row"),
            ], className="dashboard-content"),
        ]),
        dcc.Tab(label='Custom Dashboard', value='tab-custom-view', children=[
            html.Div(id='custom-dashboard-view-container', className="dashboard-content"),
        ]),
        dcc.Tab(label='Layout Editor', value='tab-editor', children=[
            html.Div(id='layout-editor-container', className="layout-editor-content"),
        ]),
    ]),
    
    dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),
    dcc.Store(id='telemetry-store', data=initial_data),
    dcc.Download(id="download-layout-json")

], className="main-container")

# --- NEW: Callbacks for the Customizable Dashboard ---

# Helper function to generate figures dynamically
def create_dynamic_figure(variable, chart_type, data):
    # This function is the same as before, generates a figure based on inputs
    fig = go.Figure()
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), xaxis=dict(color='#e8e8e8', gridcolor='#34495e'), yaxis=dict(color='#e8e8e8', gridcolor='#34495e'))
    if not data or not data.get(variable): return fig
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    y_data = data[variable]
    current_value = y_data[-1] if y_data else 0
    title = AVAILABLE_VARIABLES.get(variable, 'Unknown Variable')
    if chart_type == 'gauge':
        ranges = {'vehicle_speed': [0, 150], 'battery_voltage': [300, 420], 'battery_soc': [0, 100]}
        range_val = ranges.get(variable, [0, 100])
        fig = go.Figure(go.Indicator(mode="gauge+number", value=current_value, domain={'x': [0, 1], 'y': [0, 1]}, title={'text': title}, gauge={'axis': {'range': range_val}, 'bar': {'color': "#27ae60"}}))
    elif chart_type == 'timeseries':
        fig.add_trace(go.Scatter(x=timestamps, y=y_data, mode='lines', name=title, line=dict(color='#ffd700'))); fig.update_layout(title=title, xaxis_title="Time")
    elif chart_type == 'bar':
        fig.add_trace(go.Bar(x=[title], y=[current_value], text=[f'{current_value:.1f}'], textposition='auto', marker_color='#3498db')); fig.update_layout(title=f"Current {title}")
    fig.update_layout(height=300, margin=dict(l=40, r=20, t=60, b=40), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

# Callback to render the VIEW-ONLY custom dashboard
@callback(
    Output('custom-dashboard-view-container', 'children'),
    Input('dashboard-tabs', 'value'),
    State('layout-config-store', 'data')
)
def render_custom_dashboard_view(active_tab, layout_config):
    # Only render when actually on the custom tab
    if active_tab != 'tab-custom-view':
        raise dash.exceptions.PreventUpdate
    
    if not layout_config or 'rows' not in layout_config:
        return []
    
    rows = []
    for row_data in layout_config['rows']:
        columns = []
        num_cols = len(row_data['columns'])
        col_width = f"{100 / num_cols:.2f}%"
        
        for col_data in row_data['columns']:
            columns.append(
                html.Div([
                    dcc.Graph(
                        id={'type': 'dynamic-graph', 'index': col_data['id']},
                        config={'displayModeBar': False}  # Optional: cleaner UI
                    )
                ], className="chart-container", style={'width': col_width})
            )
        
        rows.append(html.Div(columns, className="chart-row-content"))
    
    return rows

# Callback to render the new LAYOUT EDITOR tab
# Callback to render the new LAYOUT EDITOR tab
@callback(Output('layout-editor-container', 'children'), Input('layout-config-store', 'data'))
def render_layout_editor(layout_config):
    if not layout_config or 'rows' not in layout_config: return []
    
    # --- MODIFICATION START ---
    editor_header = html.Div([
        html.H2("Layout Editor"),
        html.Button("Export to settings.json", id="export-layout-btn", className="control-btn")
    ], className="editor-header")
    # --- MODIFICATION END ---

    editor_rows = []
    for row_data in layout_config['rows']:
        row_id = row_data['id']
        column_editors = []
        for col_data in row_data['columns']:
            col_id = col_data['id']
            column_editors.append(html.Div([
                dcc.Dropdown(id={'type': 'variable-select', 'index': col_id}, options=[{'label': v, 'value': k} for k,v in AVAILABLE_VARIABLES.items()], value=col_data['variable'], clearable=False),
                dcc.Dropdown(id={'type': 'chart-select', 'index': col_id}, options=[{'label': v, 'value': k} for k,v in AVAILABLE_CHARTS.items()], value=col_data['chart'], clearable=False),
                html.Button("－", id={'type': 'remove-col-btn', 'index': col_id}, n_clicks=0)
            ], className="editor-col"))
        
        editor_rows.append(html.Div([
            html.H4(f"Row {len(editor_rows) + 1}"), # Corrected row numbering
            html.Div(column_editors, className="editor-row-content"),
            html.Div([
                html.Button("＋ Add Column", id={'type': 'add-col-btn', 'index': row_id}, n_clicks=0),
                html.Button("× Remove Row", id={'type': 'remove-row-btn', 'index': row_id}, n_clicks=0, className="stop-btn")
            ], className="editor-row-controls")
        ], className="editor-row"))
        
    add_row_button = html.Button("＋ Add Row", id={'type': 'add-row-btn', 'index': 'main'}, n_clicks=0, className="editor-add-row-btn")
    
    return html.Div([editor_header] + editor_rows + [add_row_button])
# --- ADD THIS NEW CALLBACK ---
# --- REPLACE your old export_layout callback with THIS ONE ---
@callback(
    Output("download-layout-json", "data"),
    Input("export-layout-btn", "n_clicks"),
    State("layout-config-store", "data"),
    prevent_initial_call=True,
)
def export_layout(n_clicks, layout_config):
    # This condition is the key. It checks that the button was
    # specifically clicked and is not just being rendered for the first time.
    if n_clicks is None or ctx.triggered_id != 'export-layout-btn':
        return dash.no_update

    # 1. Transform the internal config into your desired format
    output_list = []
    for row in layout_config.get('rows', []):
        row_list = []
        for col in row.get('columns', []):
            row_list.append([col.get('chart'), col.get('variable')])
        output_list.append(row_list)

    # 2. Convert the list to a JSON string and prepare it for download
    json_string = json.dumps(output_list, indent=4)
    
    # 3. Return a dictionary that tells dcc.Download to serve the file
    return dict(content=json_string, filename="settings.json")
# Central callback to modify the layout configuration (now driven by the editor tab)
# Central callback to modify the layout configuration (now driven by the editor tab)
@callback(
    Output('layout-config-store', 'data', allow_duplicate=True),
    # This simplified signature is more robust
    Input({'type': ALL, 'index': ALL}, 'n_clicks'),
    Input({'type': ALL, 'index': ALL}, 'value'),
    State('layout-config-store', 'data'),
    prevent_initial_call=True
)
def modify_layout_config(n_clicks, values, config):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return dash.no_update

    new_config = config.copy()
    
    # Check if the trigger is a dictionary (from our pattern-matching IDs)
    if not isinstance(triggered_id, dict):
        return dash.no_update

    trigger_type = triggered_id.get('type')
    trigger_index = triggered_id.get('index')

    if trigger_type == 'add-row-btn':
        new_config['rows'].append({'id': str(uuid.uuid4()), 'columns': [{'id': str(uuid.uuid4()), 'variable': 'vehicle_speed', 'chart': 'gauge'}]})
    
    elif trigger_type == 'remove-row-btn':
        new_config['rows'] = [row for row in new_config['rows'] if row['id'] != trigger_index]

    elif trigger_type == 'add-col-btn':
        for row in new_config['rows']:
            if row['id'] == trigger_index:
                row['columns'].append({'id': str(uuid.uuid4()), 'variable': 'battery_soc', 'chart': 'timeseries'})
                break

    elif trigger_type == 'remove-col-btn':
        for row in new_config['rows']:
            original_cols = len(row['columns'])
            row['columns'] = [col for col in row['columns'] if col['id'] != trigger_index]
            # If a column was removed and the row is now empty, remove the row too
            if len(row['columns']) < original_cols and not row['columns']:
                new_config['rows'] = [r for r in new_config['rows'] if r['id'] != row['id']]
                break

    elif trigger_type in ['variable-select', 'chart-select']:
        prop = 'variable' if trigger_type == 'variable-select' else 'chart'
        
        # --- THIS IS THE FIXED LINE ---
        # We add ".value" to correctly look up the input's value property
        value = ctx.inputs[f'{{"index":"{trigger_index}","type":"{trigger_type}"}}.value']
        
        for row in new_config['rows']:
            for col in row['columns']:
                if col['id'] == trigger_index:
                    col[prop] = value
                    return new_config # Exit early

    return new_config

# Pattern-matching callback to update ALL dynamic graphs
# Pattern-matching callback to update ALL dynamic graphs
@callback(
    Output({'type': 'dynamic-graph', 'index': ALL}, 'figure'),
    Input('interval-component', 'n_intervals'),  # Changed from telemetry-store
    Input('dashboard-tabs', 'value'),
    State('telemetry-store', 'data'),
    State('layout-config-store', 'data'),
    State({'type': 'dynamic-graph', 'index': ALL}, 'id')
)
def update_all_dynamic_graphs(n_intervals, active_tab, telemetry_data, layout_config, graph_ids):
    """Update all dynamic graphs, but only when custom tab is active"""
    # Skip if not on custom tab
    if active_tab != 'tab-custom-view':
        raise dash.exceptions.PreventUpdate
    
    # Skip if no graphs exist yet
    if not graph_ids:
        raise dash.exceptions.PreventUpdate
    
    if not layout_config:
        return [go.Figure()] * len(graph_ids)
    
    # Build mapping
    col_config_map = {}
    for row in layout_config['rows']:
        for col in row['columns']:
            col_config_map[col['id']] = (col['variable'], col['chart'])
    
    # Generate figures
    figures = []
    for graph_id in graph_ids:
        col_id = graph_id['index']
        if col_id in col_config_map:
            variable, chart_type = col_config_map[col_id]
            figures.append(create_dynamic_figure(variable, chart_type, telemetry_data))
        else:
            figures.append(go.Figure())
    
    return figures

# --- ORIGINAL CALLBACKS (Unchanged) ---
# All original callbacks for the static dashboard remain here, untouched.
# They will only work when the static dashboard tab is active.
@callback(Output('telemetry-store', 'data'),Input('interval-component', 'n_intervals'),State('telemetry-store', 'data'))
def update_telemetry_store(n, existing_data):
    if existing_data is None: return initial_data
    updated_data = existing_data.copy()
    new_data_points = []
    while not telemetry.data_queue.empty():
        try: data_point = telemetry.data_queue.get_nowait(); new_data_points.append(data_point)
        except queue.Empty: break
    for data_point in new_data_points:
        for key, value in data_point.items():
            if key in updated_data: updated_data[key].append(value)
    if new_data_points:
        for key in updated_data: updated_data[key] = updated_data[key][-MAX_POINTS:]
    return updated_data
@callback(Output('connection-status', 'children'),Input('telemetry-store', 'data'))
def update_connection_status(data):
    if not telemetry.running: return "🔴 Collection Stopped"
    elif data and data['timestamp']:
        latest_time = datetime.fromisoformat(data['timestamp'][-1]); time_diff = (datetime.now() - latest_time).total_seconds()
        if time_diff < 2: return "🟢 Live Data"
        else: return f"🟡 Stale Data ({time_diff:.1f}s old)"
    else:
        if telemetry.api_available: return "🟡 Server Not Responding"
        else: return "🔴 No Data"
@callback(Output('start-btn', 'disabled'),Output('stop-btn', 'disabled'),Input('start-btn', 'n_clicks'),Input('stop-btn', 'n_clicks'),prevent_initial_call=True)
def handle_collection_controls(start_clicks, stop_clicks):
    ctx = dash.callback_context
    if not ctx.triggered: return not telemetry.running, telemetry.running
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'start-btn':
        if not telemetry.running: telemetry.start(); logging.info("Data collection started by user")
        return True, False
    elif button_id == 'stop-btn':
        if telemetry.running: telemetry.stop(); logging.info("Data collection stopped by user")
        return False, True
    return not telemetry.running, telemetry.running
@callback(Output('error-notification', 'children'),Output('error-notification', 'className'),Input('telemetry-store', 'data'),Input('start-btn', 'n_clicks'),Input('stop-btn', 'n_clicks'))
def update_error_notification(data, start_clicks, stop_clicks):
    if not telemetry.running: return "", "error-notification hidden"
    if telemetry.mock_mode: return "", "error-notification hidden"
    if data and data['timestamp']:
        latest_time = datetime.fromisoformat(data['timestamp'][-1]); time_diff = (datetime.now() - latest_time).total_seconds()
        if time_diff > 5: return "⚠️ Server connection lost - data may be stale", "error-notification warning"
    else:
        if telemetry.api_available: return "⚠️ No data received from server", "error-notification warning"
    return "", "error-notification hidden"
@callback(Output('voltage-status-indicator', 'children'),Output('voltage-status-indicator', 'className'),Output('soc-status-indicator', 'children'),Output('soc-status-indicator', 'className'),Input('telemetry-store', 'data'))
def update_status_indicators(data):
    if not data or not data['timestamp'] or not data['battery_voltage']: return dash.no_update
    voltage = data['battery_voltage'][-1]
    if voltage >= 380: v_status, v_class = "OK", "status-good"
    elif voltage >= 340: v_status, v_class = "Caution", "status-caution"
    else: v_status, v_class = "Warning", "status-warning"
    v_text = f"Voltage: {v_status}"; v_classname = f"status-indicator {v_class}"; soc = data['battery_soc'][-1]
    if soc >= 50: s_status, s_class = "OK", "status-good"
    elif soc >= 20: s_status, s_class = "Caution", "status-caution"
    else: s_status, s_class = "Warning", "status-warning"
    s_text = f"SOC: {s_status}"; s_classname = f"status-indicator {s_class}"
    return v_text, v_classname, s_text, s_classname
@callback(Output('temp-overview', 'figure'),Output('toggle-temp-chart-btn', 'children'),Input('telemetry-store', 'data'),Input('toggle-temp-chart-btn', 'n_clicks'))
def update_temp_overview(data, n_clicks):
    if n_clicks is None: n_clicks = 0
    if n_clicks % 2 == 1:
        button_text = "Switch to Current Values"; timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]; fig = go.Figure()
        fig.add_trace(go.Scatter(x=timestamps, y=data['min_cell_temp'], mode='lines', name='Min Cell', line=dict(color='#3498db'))); fig.add_trace(go.Scatter(x=timestamps, y=data['max_cell_temp'], mode='lines', name='Max Cell', line=dict(color='#e74c3c'))); fig.add_trace(go.Scatter(x=timestamps, y=data['inverter_temp'], mode='lines', name='Inverter', line=dict(color='#ffd700')))
        fig.update_layout(title=dict(text="Temperatures Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)), yaxis_title="Temperature (°C)", xaxis_title="Time", yaxis=dict(color='#e8e8e8', gridcolor='#34495e'), xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True), height=260, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        return fig, button_text
    else:
        button_text = "Switch to Time Series"; current_min_temp = data['min_cell_temp'][-1] if data['min_cell_temp'] else 0; current_max_temp = data['max_cell_temp'][-1] if data['max_cell_temp'] else 0; current_inv_temp = data['inverter_temp'][-1] if data['inverter_temp'] else 0
        fig = go.Figure(go.Bar(x=['Min Cell', 'Max Cell', 'Inverter'], y=[current_min_temp, current_max_temp, current_inv_temp], marker_color=['#3498db', '#e74c3c', '#ffd700'], text=[f'{temp:.1f}°C' for temp in [current_min_temp, current_max_temp, current_inv_temp]], textposition='auto', textfont=dict(color='#1e2329', size=CHART_FONT_SIZE, family=CHART_FONT)))
        fig.update_layout(autosize=False, title=dict(text="Current Temperatures", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)), yaxis_title="Temperature (°C)", yaxis=dict(color='#e8e8e8', gridcolor='#34495e', range=[0,80], fixedrange=True), xaxis=dict(color='#e8e8e8', fixedrange=True), height=260, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
        return fig, button_text
@callback(Output('speed-gauge', 'figure'),Input('telemetry-store', 'data'))
def update_speed_gauge(data):
    current_speed = data['vehicle_speed'][-1] if data['vehicle_speed'] else 0
    fig = go.Figure(go.Indicator(mode = "gauge+number+delta", value = current_speed, domain = {'x': [0, 1], 'y': [0, 1]}, title = {'text': "Vehicle Speed (km/h)"}, delta = {'reference': data['vehicle_speed'][-2] if len(data['vehicle_speed']) > 1 else current_speed}, gauge = {'axis': {'range': [None, 150]}, 'bar': {'color': "darkblue"}, 'steps': [{'range': [0, 50], 'color': "lightgray"}, {'range': [50, 100], 'color': "gray"}, {'range': [100, 150], 'color': "red"}], 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 120}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig
@callback(Output('voltage-gauge', 'figure'),Input('telemetry-store', 'data'))
def update_voltage_gauge(data):
    current_voltage = data['battery_voltage'][-1] if data['battery_voltage'] else 0
    fig = go.Figure(go.Indicator(mode = "gauge+number+delta", value = current_voltage, domain = {'x': [0, 1], 'y': [0, 1]}, title = {'text': "Battery Voltage (V)"}, delta = {'reference': data['battery_voltage'][-2] if len(data['battery_voltage']) > 1 else current_voltage}, gauge = {'axis': {'range': [300, 420]}, 'bar': {'color': "#27ae60"}, 'steps': [{'range': [300, 340], 'color': "#e74c3c"}, {'range': [340, 380], 'color': "#f39c12"}, {'range': [380, 420], 'color': "#2c3e50"}], 'threshold': {'line': {'color': "#e74c3c", 'width': 4}, 'thickness': 0.75, 'value': 320}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig
@callback(Output('soc-gauge', 'figure'),Input('telemetry-store', 'data'))
def update_soc_gauge(data):
    current_soc = data['battery_soc'][-1] if data['battery_soc'] else 0
    fig = go.Figure(go.Indicator(mode = "gauge+number+delta", value = current_soc, domain = {'x': [0, 1], 'y': [0, 1]}, title = {'text': "Battery SOC (%)"}, delta = {'reference': data['battery_soc'][-2] if len(data['battery_soc']) > 1 else current_soc}, gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#ffd700"}, 'steps': [{'range': [0, 20], 'color': "#e74c3c"}, {'range': [20, 50], 'color': "#f39c12"}, {'range': [50, 100], 'color': "#2c3e50"}], 'threshold': {'line': {'color': "#e74c3c", 'width': 4}, 'thickness': 0.75, 'value': 15}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig
@callback(Output('speed-timeseries', 'figure'),Input('telemetry-store', 'data'))
def update_speed_timeseries(data):
    if not data['timestamp']: return go.Figure()
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]; fig = go.Figure(go.Scatter(x=timestamps, y=data['vehicle_speed'], mode='lines+markers', name='Vehicle Speed', line=dict(color='#ffd700', width=3), marker=dict(color='#ffd700', size=4)))
    fig.update_layout(title=dict(text="Vehicle Speed Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)), xaxis_title="Time", yaxis_title="Speed (km/h)", xaxis=dict(color='#e8e8e8', gridcolor='#34495e'), yaxis=dict(color='#e8e8e8', gridcolor='#34495e'), height=300, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT)), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig
@callback(Output('battery-timeseries', 'figure'),Input('telemetry-store', 'data'))
def update_battery_timeseries(data):
    if not data['timestamp']: return go.Figure()
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]; fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=data['battery_voltage'], mode='lines+markers', name='Voltage (V)', yaxis='y', line=dict(color='#27ae60', width=3), marker=dict(color='#27ae60', size=4))); fig.add_trace(go.Scatter(x=timestamps, y=data['battery_soc'], mode='lines+markers', name='SOC (%)', yaxis='y2', line=dict(color='#ffd700', width=3), marker=dict(color='#ffd700', size=4)))
    fig.update_layout(title=dict(text="Battery Parameters Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)), xaxis_title="Time", yaxis=dict(title="Voltage (V)", side="left", color='#e8e8e8', gridcolor='#34495e'), yaxis2=dict(title="SOC (%)", side="right", overlaying="y", color='#e8e8e8'), xaxis=dict(color='#e8e8e8', gridcolor='#34495e'), height=300, margin=dict(l=20, r=20, t=80, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT)), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig
@callback(Output('temperature-timeseries', 'figure'),Input('telemetry-store', 'data'))
def update_temperature_timeseries(data):
    if not data['timestamp']: return go.Figure()
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]; fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=data['min_cell_temp'], mode='lines+markers', name='Min Cell Temp', line=dict(color='#3498db', width=3), marker=dict(color='#3498db', size=4))); fig.add_trace(go.Scatter(x=timestamps, y=data['max_cell_temp'], mode='lines+markers', name='Max Cell Temp', line=dict(color='#e74c3c', width=3), marker=dict(color='#e74c3c', size=4))); fig.add_trace(go.Scatter(x=timestamps, y=data['inverter_temp'], mode='lines+markers', name='Inverter Temp', line=dict(color='#ffd700', width=3), marker=dict(color='#ffd700', size=4)))
    fig.update_layout(title=dict(text="Temperature Monitoring Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)), xaxis_title="Time", yaxis_title="Temperature (°C)", xaxis=dict(color='#e8e8e8', gridcolor='#34495e'), yaxis=dict(color='#e8e8e8', gridcolor='#34495e'), height=300, margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e8e8e8', family=CHART_FONT), legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT)), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

if __name__ == '__main__':
    try: app.run(debug=True, host='0.0.0.0', port=8050)
    except KeyboardInterrupt: telemetry.stop(); print("\nTelemetry dashboard stopped.")