import dash
from dash import dcc, html, Input, Output, callback
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

# Configuration
API_ENDPOINT = 'http://localhost:5000/api/telemetry'  # Your API endpoint
API_TIMEOUT = 2  # seconds
API_POLL_RATE = 1  # seconds between API calls (10 Hz)
LOG_DIRECTORY = 'telemetry_logs'
UPDATE_INTERVAL = 100  # milliseconds

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
    
    # ADD THIS NEW METHOD AFTER generate_mock_data():
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
                if self.mock_mode:
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
        logging.info("Telemetry receiver stopped")

# Initialize telemetry receiver
telemetry = TelemetryReceiver()
telemetry.start()

# Initialize Dash app
app = dash.Dash(__name__)
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
                    className="mode-indicator")
        ], className="status-bar")
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
            ], className="gauge-container"),
        ], className="gauge-row"),
        
        # Row 2: Battery SOC and Temperature Overview
        html.Div([
            html.Div([
                dcc.Graph(id="soc-gauge"),
            ], className="gauge-container"),
            html.Div([
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
    ], className="dashboard-content"),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=UPDATE_INTERVAL,
        n_intervals=0
    ),
    
    # Store component for data
    dcc.Store(id='telemetry-store')
], className="main-container")

# Callbacks for updating charts
@app.callback(
    Output('telemetry-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('telemetry-store', 'data')  # Get the current state of the data
)
def update_telemetry_store(n, existing_data):
    """
    Pull data from the queue and update the store.
    This is the new, robust way to handle state.
    """
    # On first run, initialize the data store
    if existing_data is None:
        return initial_data

    # Create a copy to modify
    updated_data = existing_data.copy()
    
    # Pull all available data from the queue
    while not telemetry.data_queue.empty():
        try:
            data_point = telemetry.data_queue.get_nowait()
            
            # Append new data
            for key, value in data_point.items():
                if key in updated_data:
                    updated_data[key].append(value)

            # Trim the data to MAX_POINTS
            for key in updated_data:
                updated_data[key] = updated_data[key][-MAX_POINTS:]

        except queue.Empty:
            break # Should not happen with the while loop condition but good for safety
            
    return updated_data

@app.callback(
    Output('speed-gauge', 'figure'),
    Input('telemetry-store', 'data')
)
def update_speed_gauge(data):
    """Update speed gauge"""
    current_speed = data['vehicle_speed'][-1] if data['vehicle_speed'] else 0
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = current_speed,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Vehicle Speed (km/h)"},
        delta = {'reference': data['vehicle_speed'][-2] if len(data['vehicle_speed']) > 1 else current_speed},
        gauge = {'axis': {'range': [None, 150]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 100], 'color': "gray"},
                    {'range': [100, 150], 'color': "red"}],
                'threshold': {'line': {'color': "red", 'width': 4},
                             'thickness': 0.75, 'value': 120}}))
    
    fig.update_layout(
        height=300, 
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    return fig

@app.callback(
    Output('voltage-gauge', 'figure'),
    Input('telemetry-store', 'data')
)
def update_voltage_gauge(data):
    """Update battery voltage gauge"""
    current_voltage = data['battery_voltage'][-1] if data['battery_voltage'] else 0
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = current_voltage,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Battery Voltage (V)"},
        delta = {'reference': data['battery_voltage'][-2] if len(data['battery_voltage']) > 1 else current_voltage},
        gauge = {'axis': {'range': [300, 420]},
                'bar': {'color': "#27ae60"},
                'steps': [
                    {'range': [300, 340], 'color': "#e74c3c"},
                    {'range': [340, 380], 'color': "#f39c12"},
                    {'range': [380, 420], 'color': "#2c3e50"}],
                'threshold': {'line': {'color': "#e74c3c", 'width': 4},
                             'thickness': 0.75, 'value': 320}}))
    
    fig.update_layout(
        height=300, 
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    return fig

@app.callback(
    Output('soc-gauge', 'figure'),
    Input('telemetry-store', 'data')
)
def update_soc_gauge(data):
    """Update battery SOC gauge"""
    current_soc = data['battery_soc'][-1] if data['battery_soc'] else 0
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = current_soc,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Battery SOC (%)"},
        delta = {'reference': data['battery_soc'][-2] if len(data['battery_soc']) > 1 else current_soc},
        gauge = {'axis': {'range': [0, 100]},
                'bar': {'color': "#ffd700"},
                'steps': [
                    {'range': [0, 20], 'color': "#e74c3c"},
                    {'range': [20, 50], 'color': "#f39c12"},
                    {'range': [50, 100], 'color': "#2c3e50"}],
                'threshold': {'line': {'color': "#e74c3c", 'width': 4},
                             'thickness': 0.75, 'value': 15}}))
    
    fig.update_layout(
        height=300, 
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    return fig

@app.callback(
    Output('temp-overview', 'figure'),
    Input('telemetry-store', 'data')
)
def update_temp_overview(data):
    """Update temperature overview"""
    if not data['timestamp']:
        return go.Figure()
    
    current_min_temp = data['min_cell_temp'][-1] if data['min_cell_temp'] else 0
    current_max_temp = data['max_cell_temp'][-1] if data['max_cell_temp'] else 0
    current_inv_temp = data['inverter_temp'][-1] if data['inverter_temp'] else 0
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=['Min Cell', 'Max Cell', 'Inverter'],
        y=[current_min_temp, current_max_temp, current_inv_temp],
        marker_color=['#3498db', '#e74c3c', '#ffd700'],
        text=[f'{temp:.1f}°C' for temp in [current_min_temp, current_max_temp, current_inv_temp]],
        textposition='auto',
        textfont=dict(color='#1e2329', size=CHART_FONT_SIZE, family=CHART_FONT)
    ))
    
    fig.update_layout(
        title=dict(text="Current Temperatures", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
        yaxis_title="Temperature (°C)",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        xaxis=dict(color='#e8e8e8'),
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', family=CHART_FONT)
    )
    return fig

@app.callback(
    Output('speed-timeseries', 'figure'),
    Input('telemetry-store', 'data')
)
def update_speed_timeseries(data):
    """Update speed time series"""
    if not data['timestamp']:
        return go.Figure()
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['vehicle_speed'],
        mode='lines+markers',
        name='Vehicle Speed',
        line=dict(color='#ffd700', width=3),
        marker=dict(color='#ffd700', size=4)
    ))
    
    fig.update_layout(
        title=dict(text="Vehicle Speed Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
        xaxis_title="Time",
        yaxis_title="Speed (km/h)",
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', family=CHART_FONT),
        legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT))
    )
    return fig

@app.callback(
    Output('battery-timeseries', 'figure'),
    Input('telemetry-store', 'data')
)
def update_battery_timeseries(data):
    """Update battery time series"""
    if not data['timestamp']:
        return go.Figure()
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['battery_voltage'],
        mode='lines+markers',
        name='Voltage (V)',
        yaxis='y',
        line=dict(color='#27ae60', width=3),
        marker=dict(color='#27ae60', size=4)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['battery_soc'],
        mode='lines+markers',
        name='SOC (%)',
        yaxis='y2',
        line=dict(color='#ffd700', width=3),
        marker=dict(color='#ffd700', size=4)
    ))
    
    fig.update_layout(
        title=dict(text="Battery Parameters Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
        xaxis_title="Time",
        yaxis=dict(title="Voltage (V)", side="left", color='#e8e8e8', gridcolor='#34495e'),
        yaxis2=dict(title="SOC (%)", side="right", overlaying="y", color='#e8e8e8'),
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', family=CHART_FONT),
        legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT))
    )
    return fig

@app.callback(
    Output('temperature-timeseries', 'figure'),
    Input('telemetry-store', 'data')
)
def update_temperature_timeseries(data):
    """Update temperature time series"""
    if not data['timestamp']:
        return go.Figure()
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['min_cell_temp'],
        mode='lines+markers',
        name='Min Cell Temp',
        line=dict(color='#3498db', width=3),
        marker=dict(color='#3498db', size=4)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['max_cell_temp'],
        mode='lines+markers',
        name='Max Cell Temp',
        line=dict(color='#e74c3c', width=3),
        marker=dict(color='#e74c3c', size=4)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['inverter_temp'],
        mode='lines+markers',
        name='Inverter Temp',
        line=dict(color='#ffd700', width=3),
        marker=dict(color='#ffd700', size=4)
    ))
    
    fig.update_layout(
        title=dict(text="Temperature Monitoring Over Time", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
        plot_bgcolor='#1e2329',
        paper_bgcolor='#1e2329',
        font=dict(color='#e8e8e8', family=CHART_FONT),
        legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT))
    )
    return fig

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=8050)
    except KeyboardInterrupt:
        telemetry.stop()
        print("\nTelemetry dashboard stopped.")