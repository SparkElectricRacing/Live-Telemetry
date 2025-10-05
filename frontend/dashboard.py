import dash
from dash import dcc, html, Input, Output, callback
from dash.dependencies import State, ALL
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

# Configuration
API_ENDPOINT = 'http://localhost:5000/api/telemetry'  # Your API endpoint
API_TIMEOUT = 2  # seconds
API_POLL_RATE = 0.05  # seconds between API calls (2 Hz)
LOG_DIRECTORY = 'telemetry_logs'
UPDATE_INTERVAL = 50  # milliseconds (2 Hz)

CHART_FONT = 'Arial'
CHART_FONT_SIZE = 12
TITLE_FONT_SIZE = 16

# UI Configuration
BORDER_RADIUS = 20  # Corner rounding for containers (px)

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

# Ensure log directory exists
os.makedirs(LOG_DIRECTORY, exist_ok=True)

# Set up logging
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
        
        # Playback mode
        self.playback_mode = False
        self.playback_file = None
        self.playback_data = []
        self.playback_index = 0
        self.playback_paused = False

        # Data storage for plotting
        self.max_points = 100
        self.data_history = {
            'timestamp': [],
            'vehicle_speed': [],
            'battery_voltage': [],
            'battery_soc': [],
            'min_cell_temp': [],
            'max_cell_temp': [],
            'inverter_temp': []
        }
        
    def test_api_connection(self):
        """Test if API endpoint is available"""
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
        """Generate mock telemetry data for testing"""
        import random
        now = datetime.now()
        
        # Simulate realistic vehicle data
        data = {
            'timestamp': now.isoformat(),
            'vehicle_speed': random.uniform(0, 120),  # km/h
            'battery_voltage': random.uniform(320, 400),  # V
            'battery_soc': random.uniform(20, 100),  # %
            'min_cell_temp': random.uniform(20, 45),  # °C
            'max_cell_temp': random.uniform(25, 50),  # °C
            'inverter_temp': random.uniform(30, 80)  # °C
        }
        return data
    
    def fetch_api_data(self):
        """Fetch telemetry data from API"""
        try:
            response = requests.get(API_ENDPOINT, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            json_data = response.json()
            
            data = {
                'timestamp': json_data.get('timestamp', datetime.now().isoformat()),
                'vehicle_speed': float(json_data.get('vehicle_speed', 0)),
                'battery_voltage': float(json_data.get('battery_voltage', 0)),
                'battery_soc': float(json_data.get('battery_soc', 0)),
                'min_cell_temp': float(json_data.get('min_cell_temp', 0)),
                'max_cell_temp': float(json_data.get('max_cell_temp', 0)),
                'inverter_temp': float(json_data.get('inverter_temp', 0))
            }
            
            if not data['timestamp']:
                data['timestamp'] = datetime.now().isoformat()
            
            return data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            return None
        except (ValueError, KeyError) as e:
            logging.error(f"Error parsing API response: {e}")
            return None
    
    def parse_telemetry_packet(self, raw_data):
        """Parse incoming telemetry packet - customize based on your packet format"""
        try:
            # Example packet format: "SPEED:45.2,VOLT:380.5,SOC:85.3,TEMP_MIN:22.1,TEMP_MAX:28.5,INV_TEMP:55.2"
            data = {}
            data['timestamp'] = datetime.now().isoformat()
            
            pairs = raw_data.strip().split(',')
            for pair in pairs:
                if ':' in pair:
                    key, value = pair.split(':')
                    if key == 'SPEED':
                        data['vehicle_speed'] = float(value)
                    elif key == 'VOLT':
                        data['battery_voltage'] = float(value)
                    elif key == 'SOC':
                        data['battery_soc'] = float(value)
                    elif key == 'TEMP_MIN':
                        data['min_cell_temp'] = float(value)
                    elif key == 'TEMP_MAX':
                        data['max_cell_temp'] = float(value)
                    elif key == 'INV_TEMP':
                        data['inverter_temp'] = float(value)
            
            return data
        except Exception as e:
            logging.error(f"Error parsing telemetry packet: {e}")
            return None
    
    def data_receiver_thread(self):
        """Background thread for receiving data"""
        while self.running:
            try:
                if self.playback_mode:
                    if not self.playback_paused and self.playback_index < len(self.playback_data):
                        data = self.playback_data[self.playback_index]
                        self.playback_index += 1
                        time.sleep(API_POLL_RATE)
                    elif self.playback_index >= len(self.playback_data):
                        # Playback finished
                        self.playback_mode = False
                        logging.info("Playback finished")
                        time.sleep(1)
                        continue
                    else:
                        # Paused
                        time.sleep(0.1)
                        continue
                elif self.mock_mode:
                    data = self.generate_mock_data()
                    time.sleep(API_POLL_RATE)
                else:
                    data = self.fetch_api_data()
                    if data is None:
                        time.sleep(1)
                        continue
                    time.sleep(API_POLL_RATE)

                # The thread's ONLY job is to put data on the queue
                if data:
                    self.data_queue.put(data)
                    if not self.playback_mode:
                        logging.info(f"Telemetry: {data}")

            except Exception as e:
                logging.error(f"Error in data receiver: {e}")
                time.sleep(1)
    
    
    def add_to_history(self, data):
        """Add data point to history for plotting"""
        timestamp = datetime.fromisoformat(data['timestamp'])
        
        # Add new data
        for key in self.data_history:
            if key == 'timestamp':
                self.data_history[key].append(timestamp)
            else:
                self.data_history[key].append(data.get(key, 0))
        
        # Trim to max points
        if len(self.data_history['timestamp']) > self.max_points:
            for key in self.data_history:
                self.data_history[key] = self.data_history[key][-self.max_points:]
    
    def start(self):
        """Start the telemetry receiver"""
        self.running = True
        self.test_api_connection()
        self.thread = threading.Thread(target=self.data_receiver_thread)
        self.thread.daemon = True
        self.thread.start()
        logging.info("Telemetry receiver started")
    
    def stop(self):
        """Stop the telemetry receiver"""
        self.running = False
        self.playback_mode = False
        logging.info("Telemetry receiver stopped")
    
    def load_log_file(self, log_file_path):
        """Load telemetry data from log file for playback"""
        try:
            import re
            import json
            
            self.playback_data = []
            with open(log_file_path, 'r') as f:
                for line in f:
                    # Extract JSON data from log lines
                    if 'Telemetry:' in line:
                        # Find the JSON part after "Telemetry: "
                        json_start = line.find('Telemetry: ') + len('Telemetry: ')
                        json_str = line[json_start:].strip()
                        try:
                            data = json.loads(json_str)
                            self.playback_data.append(data)
                        except json.JSONDecodeError:
                            continue
            
            logging.info(f"Loaded {len(self.playback_data)} data points from {log_file_path}")
            return len(self.playback_data) > 0
        except Exception as e:
            logging.error(f"Error loading log file: {e}")
            return False
    
    def start_playback(self, log_file_path):
        """Start playback from a log file"""
        if self.load_log_file(log_file_path):
            self.playback_mode = True
            self.playback_index = 0
            self.playback_paused = False
            self.playback_file = log_file_path
            if not self.running:
                self.start()
            logging.info(f"Started playback of {log_file_path}")
            return True
        return False
    
    def pause_playback(self):
        """Pause playback"""
        self.playback_paused = True
        logging.info("Playback paused")
    
    def resume_playback(self):
        """Resume playback"""
        self.playback_paused = False
        logging.info("Playback resumed")
    
    def stop_playback(self):
        """Stop playback and return to normal mode"""
        self.playback_mode = False
        self.playback_paused = False
        self.playback_index = 0
        logging.info("Playback stopped")

# Initialize telemetry receiver
telemetry = TelemetryReceiver()
telemetry.start()

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Zephyrus Live Telemetry"

template_path = str(pathlib.Path(__file__).parent / "templates" / "index.html")
with open(template_path, 'r') as f:
    app.index_string = f.read()

# Define the layout
app.layout = html.Div([
    html.Div([
        html.H1("Zephyrus Live Telemetry Dashboard", className="header-title"),
        html.Div([
            html.Div(id="connection-status", className="status-indicator"),
            html.Div(f"Mode: {'Mock Data' if telemetry.mock_mode else 'Live API'}", 
                    className="mode-indicator"),
            html.Div([
                html.Button("Stop Collection", id="stop-btn", n_clicks=0, className="control-btn stop-btn"),
                html.Button("Start Collection", id="start-btn", n_clicks=0, className="control-btn start-btn")
            ], className="control-buttons")
        ], className="status-bar"),
        html.Div(id="error-notification", className="error-notification hidden")
    ], className="header"),
    
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
        
        # Row 2: Battery SOC and Temperature Overview
        html.Div([
            html.Div([
                dcc.Graph(id="soc-gauge"),
                html.Div(id="soc-status-indicator")
            ], className="gauge-container"),
            # MODIFIED: Added a container and a button for toggling the view
            html.Div([
                html.Div([
                    html.Button("Switch to Time Series", id='toggle-temp-chart-btn', n_clicks=0)
                ], className="chart-header"),
                dcc.Graph(id="temp-overview"),
            ], className="chart-container"),
        ], className="mixed-row"),
        
        # Row 3: Time series plots
        html.Div([
            html.Div([
                dcc.Graph(id="speed-timeseries"),
            ], className="chart-container"),
            html.Div([
                dcc.Graph(id="battery-timeseries"),
            ], className="chart-container"),
        ], className="chart-row"),
        
        html.Div([
            html.Div([
                dcc.Graph(id="temperature-timeseries"),
            ], className="chart-container-full"),
        ], className="chart-row"),
        
        # Log Management Section
        html.Div([
            html.H3("Log Management", className="section-title"),
            html.Div([
                html.Div([
                    html.H4("Available Log Files"),
                    html.Div(id="log-files-list"),
                    html.Button("Refresh List", id="refresh-logs-btn", n_clicks=0, className="control-btn"),
                    html.Div([
                        dcc.Input(id="file-operation-input", type="text", placeholder="Enter filename to delete/rename", style={"width": "200px"}),
                        html.Button("Delete", id="delete-file-btn", n_clicks=0, className="control-btn stop-btn"),
                        html.Button("Rename", id="rename-file-btn", n_clicks=0, className="control-btn"),
                        dcc.Input(id="new-name-input", type="text", placeholder="New name", style={"width": "150px"}),
                    ], className="file-operations", style={"margin-top": "10px"}),
                    html.Div(id="file-operation-status", className="operation-status")
                ], className="log-list-container"),
                html.Div([
                    html.H4("Playback Controls"),
                    html.Div([
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

# Callbacks for updating charts
@app.callback(
    Output('telemetry-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('telemetry-store', 'data')
)
def update_telemetry_store(n, existing_data):
    if existing_data is None:
        return initial_data
    updated_data = existing_data.copy()
    new_data_points = []
    while not telemetry.data_queue.empty():
        try:
            data_point = telemetry.data_queue.get_nowait()
            new_data_points.append(data_point)
        except queue.Empty:
            break
    for data_point in new_data_points:
        for key, value in data_point.items():
            if key in updated_data:
                updated_data[key].append(value)
    if new_data_points:
        for key in updated_data:
            updated_data[key] = updated_data[key][-MAX_POINTS:]
    return updated_data

@app.callback(
    Output('connection-status', 'children'),
    Input('telemetry-store', 'data')
)
def update_connection_status(data):
    if not telemetry.running:
        return "🔴 Collection Stopped"
    elif telemetry.playback_mode:
        if telemetry.playback_paused:
            return "⏸️ Playback Paused"
        else:
            return "▶️ Playing Back Data"
    elif data and data['timestamp']:
        latest_time = datetime.fromisoformat(data['timestamp'][-1])
        time_diff = (datetime.now() - latest_time).total_seconds()
        if time_diff < 2:
            return "🟢 Live Data"
        else:
            return f"🟡 Stale Data ({time_diff:.1f}s old)"
    else:
        if telemetry.api_available:
            return "🟡 Server Not Responding"
        else:
            return "🔴 No Data"

@app.callback(
    Output('start-btn', 'disabled'),
    Output('stop-btn', 'disabled'),
    Input('start-btn', 'n_clicks'),
    Input('stop-btn', 'n_clicks'),
    Input('page-load-trigger', 'data')
)
def handle_collection_controls(start_clicks, stop_clicks, page_load):
    ctx = dash.callback_context
    if not ctx.triggered:
        return not telemetry.running, telemetry.running
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'start-btn':
        if not telemetry.running:
            telemetry.start()
            logging.info("Data collection started by user")
        return True, False
    elif button_id == 'stop-btn':
        if telemetry.running:
            telemetry.stop()
            logging.info("Data collection stopped by user")
        return False, True
    
    return not telemetry.running, telemetry.running

@app.callback(
    Output('error-notification', 'children'),
    Output('error-notification', 'className'),
    Input('telemetry-store', 'data'),
    Input('start-btn', 'n_clicks'),
    Input('stop-btn', 'n_clicks')
)
def update_error_notification(data, start_clicks, stop_clicks):
    if not telemetry.running:
        return "", "error-notification hidden"
    
    if telemetry.mock_mode:
        return "", "error-notification hidden"
    
    # Check if we have stale data or no data from API
    if data and data['timestamp']:
        latest_time = datetime.fromisoformat(data['timestamp'][-1])
        time_diff = (datetime.now() - latest_time).total_seconds()
        if time_diff > 5:  # More than 5 seconds old
            return "⚠️ Server connection lost - data may be stale", "error-notification warning"
    else:
        if telemetry.api_available:
            return "⚠️ No data received from server", "error-notification warning"
    
    return "", "error-notification hidden"

@app.callback(
    Output('log-files-list', 'children'),
    Output('selected-log-file', 'options'),
    Input('refresh-logs-btn', 'n_clicks'),
    Input('page-load-trigger', 'data')
)
def update_log_files_list(n_clicks, page_load):
    try:
        log_files = []
        for filename in os.listdir(LOG_DIRECTORY):
            if filename.endswith('.log'):
                filepath = os.path.join(LOG_DIRECTORY, filename)
                file_size = os.path.getsize(filepath) / 1024  # KB
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                log_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'size_kb': file_size,
                    'modified': file_time
                })
        
        # Sort by modification time, newest first
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        # Create display elements
        file_elements = []
        dropdown_options = []
        
        for log_file in log_files:
            file_elements.append(
                html.Div([
                    html.Span(log_file['filename'], className="log-filename"),
                    html.Span(f"{log_file['size_kb']:.1f} KB", className="log-size"),
                    html.Span(log_file['modified'].strftime("%Y-%m-%d %H:%M"), className="log-time")
                ], className="log-file-item")
            )
            
            dropdown_options.append({
                'label': f"{log_file['filename']} ({log_file['size_kb']:.1f}KB)",
                'value': log_file['filepath']
            })
        
        return file_elements, dropdown_options
        
    except Exception as e:
        return [html.Div(f"Error loading log files: {e}")], []

@app.callback(
    Output('log-files-list', 'children', allow_duplicate=True),
    Output('selected-log-file', 'options', allow_duplicate=True),
    Output('file-operation-input', 'value'),
    Output('new-name-input', 'value'),
    Output('file-operation-status', 'children'),
    Input('delete-file-btn', 'n_clicks'),
    Input('rename-file-btn', 'n_clicks'),
    State('file-operation-input', 'value'),
    State('new-name-input', 'value'),
    prevent_initial_call=True
)
def handle_file_operations(delete_clicks, rename_clicks, filename, new_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    status_message = ""
    
    try:
        if button_id == 'delete-file-btn' and filename:
            filepath = os.path.join(LOG_DIRECTORY, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"Deleted log file: {filename}")
                status_message = f"✅ Successfully deleted {filename}"
            else:
                logging.warning(f"File not found: {filename}")
                status_message = f"❌ File not found: {filename}"
        
        elif button_id == 'rename-file-btn' and filename and new_name:
            old_filepath = os.path.join(LOG_DIRECTORY, filename)
            
            # Ensure new name has .log extension if not provided
            if not new_name.endswith('.log'):
                new_name = new_name + '.log'
            
            new_filepath = os.path.join(LOG_DIRECTORY, new_name)
            
            logging.info(f"Attempting to rename {old_filepath} to {new_filepath}")
            
            if os.path.exists(old_filepath):
                if os.path.exists(new_filepath):
                    logging.error(f"Target file already exists: {new_name}")
                    status_message = f"❌ Target file already exists: {new_name}"
                else:
                    os.rename(old_filepath, new_filepath)
                    logging.info(f"Successfully renamed {filename} to {new_name}")
                    status_message = f"✅ Successfully renamed {filename} to {new_name}"
            else:
                logging.error(f"Source file not found: {filename}")
                logging.info(f"Available files: {os.listdir(LOG_DIRECTORY)}")
                status_message = f"❌ Source file not found: {filename}"
        
        # Refresh the list and clear inputs
        files, options = update_log_files_list(1, 0)
        return files, options, "", "", status_message
        
    except Exception as e:
        logging.error(f"Error in file operation: {e}")
        files, options = update_log_files_list(1, 0)
        return files, options, "", "", f"❌ Error: {str(e)}"

@app.callback(
    Output('playback-status', 'children'),
    Output('play-btn', 'disabled'),
    Output('pause-btn', 'disabled'),
    Output('stop-playback-btn', 'disabled'),
    Input('play-btn', 'n_clicks'),
    Input('pause-btn', 'n_clicks'),
    Input('stop-playback-btn', 'n_clicks'),
    Input('interval-component', 'n_intervals'),
    State('selected-log-file', 'value'),
    prevent_initial_call=True
)
def handle_playback_controls(play_clicks, pause_clicks, stop_clicks, n_intervals, selected_file):
    try:
        ctx = dash.callback_context
        
        if ctx.triggered:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if button_id == 'play-btn' and selected_file:
                if telemetry.playback_mode and telemetry.playback_paused:
                    telemetry.resume_playback()
                else:
                    success = telemetry.start_playback(selected_file)
                    if not success:
                        return "Error loading log file", False, True, True
            elif button_id == 'pause-btn':
                telemetry.pause_playback()
            elif button_id == 'stop-playback-btn':
                telemetry.stop_playback()
        
        # Update status and button states
        if telemetry.playback_mode:
            if telemetry.playback_paused:
                status = f"Paused at {telemetry.playback_index}/{len(telemetry.playback_data)}"
                return status, False, False, False  # play enabled, pause enabled, stop enabled
            else:
                status = f"Playing {telemetry.playback_index}/{len(telemetry.playback_data)}"
                return status, True, False, False   # play disabled, pause enabled, stop enabled
        else:
            return "No playback active", False, True, True  # play enabled, pause/stop disabled
    
    except Exception as e:
        logging.error(f"Error in playback controls: {e}")
        return f"Error: {str(e)}", False, True, True
        
@app.callback(
    Output('voltage-status-indicator', 'children'),
    Output('voltage-status-indicator', 'className'),
    Output('soc-status-indicator', 'children'),
    Output('soc-status-indicator', 'className'),
    Input('telemetry-store', 'data')
)
def update_status_indicators(data):
    if not data or not data['timestamp'] or not data['battery_voltage']:
        return dash.no_update
    voltage = data['battery_voltage'][-1]
    if voltage >= 380: v_status, v_class = "OK", "status-good"
    elif voltage >= 340: v_status, v_class = "Caution", "status-caution"
    else: v_status, v_class = "Warning", "status-warning"
    v_text = f"Voltage: {v_status}"
    v_classname = f"status-indicator {v_class}"
    soc = data['battery_soc'][-1]
    if soc >= 50: s_status, s_class = "OK", "status-good"
    elif soc >= 20: s_status, s_class = "Caution", "status-caution"
    else: s_status, s_class = "Warning", "status-warning"
    s_text = f"SOC: {s_status}"
    s_classname = f"status-indicator {s_class}"
    return v_text, v_classname, s_text, s_classname

@app.callback(
    Output('temp-overview', 'figure'),
    Output('toggle-temp-chart-btn', 'children'),
    Input('telemetry-store', 'data'),
    Input('toggle-temp-chart-btn', 'n_clicks')
)
def update_temp_overview(data, n_clicks):
    if n_clicks is None:
        n_clicks = 0

    if n_clicks % 2 == 1:
        button_text = "Switch to Current Values"
        if not data['timestamp']:
            return go.Figure(), button_text
        
        timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=timestamps, y=data['min_cell_temp'], mode='lines', name='Min Cell', line=dict(color='#3498db')))
        fig.add_trace(go.Scatter(x=timestamps, y=data['max_cell_temp'], mode='lines', name='Max Cell', line=dict(color='#e74c3c')))
        fig.add_trace(go.Scatter(x=timestamps, y=data['inverter_temp'], mode='lines', name='Inverter', line=dict(color='#ffd700')))
        
        fig.update_layout(
            title=dict(text="Temperatures Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
            yaxis_title="Temperature (°C)",
            xaxis_title="Time",
            yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
            xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
            height=260,
            margin=dict(l=20, r=20, t=80, b=20), # Adjusted margin
            plot_bgcolor='rgba(0,0,0,0)', # Set plot background to transparent
            paper_bgcolor='rgba(0,0,0,0)', # Set paper background to transparent
            font=dict(color='#e8e8e8', family=CHART_FONT),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig, button_text
    else:
        button_text = "Switch to Time Series"
        if not data['timestamp']:
            return go.Figure(), button_text
        
        current_min_temp = data['min_cell_temp'][-1] if data['min_cell_temp'] else 0
        current_max_temp = data['max_cell_temp'][-1] if data['max_cell_temp'] else 0
        current_inv_temp = data['inverter_temp'][-1] if data['inverter_temp'] else 0
        
        fig = go.Figure(go.Bar(
            x=['Min Cell', 'Max Cell', 'Inverter'],
            y=[current_min_temp, current_max_temp, current_inv_temp],
            marker_color=['#3498db', '#e74c3c', '#ffd700'],
            text=[f'{temp:.1f}°C' for temp in [current_min_temp, current_max_temp, current_inv_temp]],
            textposition='auto',
            textfont=dict(color='#1e2329', size=CHART_FONT_SIZE, family=CHART_FONT),
             
        ))
        
        fig.update_layout(
            autosize=False,
            title=dict(text="Current Temperatures", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
            yaxis_title="Temperature (°C)",
            yaxis=dict(color='#e8e8e8', gridcolor='#34495e', range=[0,80], fixedrange=True),
            xaxis=dict(color='#e8e8e8', fixedrange=True),
            height=260,
            margin=dict(l=20, r=20, t=80, b=20), # Adjusted margin
            plot_bgcolor='rgba(0,0,0,0)', # Set plot background to transparent
            paper_bgcolor='rgba(0,0,0,0)', # Set paper background to transparent
            font=dict(color='#e8e8e8', family=CHART_FONT),
            transition={'duration': 300, 'easing': 'cubic-in-out'}
        )
        return fig, button_text


@app.callback(
    Output('speed-gauge', 'figure'),
    Input('telemetry-store', 'data')
)
def update_speed_gauge(data):
    current_speed = data['vehicle_speed'][-1] if data['vehicle_speed'] else 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta", value = current_speed, domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Vehicle Speed (km/h)"},
        delta = {'reference': data['vehicle_speed'][-2] if len(data['vehicle_speed']) > 1 else current_speed},
        gauge = {'axis': {'range': [None, 150]}, 'bar': {'color': "darkblue"},
                'steps': [{'range': [0, 50], 'color': "lightgray"}, {'range': [50, 100], 'color': "gray"}, {'range': [100, 150], 'color': "red"}],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 120}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=80, b=20), 
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', # Set to transparent
                      font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

@app.callback(
    Output('voltage-gauge', 'figure'),
    Input('telemetry-store', 'data')
)
def update_voltage_gauge(data):
    current_voltage = data['battery_voltage'][-1] if data['battery_voltage'] else 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta", value = current_voltage, domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Battery Voltage (V)"},
        delta = {'reference': data['battery_voltage'][-2] if len(data['battery_voltage']) > 1 else current_voltage},
        gauge = {'axis': {'range': [300, 420]}, 'bar': {'color': "#27ae60"},
                'steps': [{'range': [300, 340], 'color': "#e74c3c"}, {'range': [340, 380], 'color': "#f39c12"}, {'range': [380, 420], 'color': "#2c3e50"}],
                'threshold': {'line': {'color': "#e74c3c", 'width': 4}, 'thickness': 0.75, 'value': 320}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=80, b=20), 
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', # Set to transparent
                      font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

@app.callback(
    Output('soc-gauge', 'figure'),
    Input('telemetry-store', 'data')
)
def update_soc_gauge(data):
    current_soc = data['battery_soc'][-1] if data['battery_soc'] else 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta", value = current_soc, domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Battery SOC (%)"},
        delta = {'reference': data['battery_soc'][-2] if len(data['battery_soc']) > 1 else current_soc},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#ffd700"},
                'steps': [{'range': [0, 20], 'color': "#e74c3c"}, {'range': [20, 50], 'color': "#f39c12"}, {'range': [50, 100], 'color': "#2c3e50"}],
                'threshold': {'line': {'color': "#e74c3c", 'width': 4}, 'thickness': 0.75, 'value': 15}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=80, b=20), 
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', # Set to transparent
                      font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

@app.callback(
    Output('speed-timeseries', 'figure'),
    Input('telemetry-store', 'data')
)
def update_speed_timeseries(data):
    if not data['timestamp']: return go.Figure()
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    fig = go.Figure(go.Scatter(x=timestamps, y=data['vehicle_speed'], mode='lines+markers', name='Vehicle Speed',
                               line=dict(color='#ffd700', width=3), marker=dict(color='#ffd700', size=4)))
    fig.update_layout(title=dict(text="Vehicle Speed Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
                      xaxis_title="Time", yaxis_title="Speed (km/h)", xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
                      yaxis=dict(color='#e8e8e8', gridcolor='#34495e'), height=300, margin=dict(l=20, r=20, t=80, b=20), # Adjusted margin
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', # Set to transparent
                      font=dict(color='#e8e8e8', family=CHART_FONT),
                      legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT)), transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

@app.callback(
    Output('battery-timeseries', 'figure'),
    Input('telemetry-store', 'data')
)
def update_battery_timeseries(data):
    if not data['timestamp']: return go.Figure()
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=data['battery_voltage'], mode='lines+markers', name='Voltage (V)', yaxis='y',
                             line=dict(color='#27ae60', width=3), marker=dict(color='#27ae60', size=4)))
    fig.add_trace(go.Scatter(x=timestamps, y=data['battery_soc'], mode='lines+markers', name='SOC (%)', yaxis='y2',
                             line=dict(color='#ffd700', width=3), marker=dict(color='#ffd700', size=4)))
    fig.update_layout(title=dict(text="Battery Parameters Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
                      xaxis_title="Time", yaxis=dict(title="Voltage (V)", side="left", color='#e8e8e8', gridcolor='#34495e'),
                      yaxis2=dict(title="SOC (%)", side="right", overlaying="y", color='#e8e8e8'), xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
                      height=300, margin=dict(l=20, r=20, t=80, b=20), # Adjusted margin
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', # Set to transparent
                      font=dict(color='#e8e8e8', family=CHART_FONT), legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT)),
                      transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

@app.callback(
    Output('temperature-timeseries', 'figure'),
    Input('telemetry-store', 'data')
)
def update_temperature_timeseries(data):
    if not data['timestamp']: return go.Figure()
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=data['min_cell_temp'], mode='lines+markers', name='Min Cell Temp',
                             line=dict(color='#3498db', width=3), marker=dict(color='#3498db', size=4)))
    fig.add_trace(go.Scatter(x=timestamps, y=data['max_cell_temp'], mode='lines+markers', name='Max Cell Temp',
                             line=dict(color='#e74c3c', width=3), marker=dict(color='#e74c3c', size=4)))
    fig.add_trace(go.Scatter(x=timestamps, y=data['inverter_temp'], mode='lines+markers', name='Inverter Temp',
                             line=dict(color='#ffd700', width=3), marker=dict(color='#ffd700', size=4)))
    fig.update_layout(title=dict(text="Temperature Monitoring Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
                      xaxis_title="Time", yaxis_title="Temperature (°C)", xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
                      yaxis=dict(color='#e8e8e8', gridcolor='#34495e'), height=300, margin=dict(l=20, r=20, t=40, b=20), # Adjusted margin
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', # Set to transparent
                      font=dict(color='#e8e8e8', family=CHART_FONT), legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT)),
                      transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=8050)
    except KeyboardInterrupt:
        telemetry.stop()
        print("\nTelemetry dashboard stopped.")
