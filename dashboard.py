import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import serial
import threading
import queue
import time
from datetime import datetime, timedelta
import logging
import os

# Configuration
SERIAL_PORT = 'COM3'  # Adjust for your system (Linux: '/dev/ttyUSB0', Mac: '/dev/cu.usbserial-*')
BAUD_RATE = 9600
LOG_DIRECTORY = 'telemetry_logs'
UPDATE_INTERVAL = 100  # milliseconds

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
        self.serial_connection = None
        self.running = False
        self.mock_mode = True  # Set to False when connecting to real hardware
        
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
        
    def connect_serial(self):
        """Connect to serial port for real hardware communication"""
        try:
            self.serial_connection = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            self.mock_mode = False
            logging.info(f"Connected to serial port {SERIAL_PORT}")
            return True
        except Exception as e:
            logging.warning(f"Failed to connect to serial port: {e}")
            logging.info("Running in mock mode")
            self.mock_mode = True
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
                    # Generate mock data
                    data = self.generate_mock_data()
                    time.sleep(0.1)  # 10 Hz update rate
                else:
                    # Read from serial port
                    if self.serial_connection and self.serial_connection.in_waiting:
                        raw_data = self.serial_connection.readline().decode('utf-8')
                        data = self.parse_telemetry_packet(raw_data)
                        if data is None:
                            continue
                
                # Add to queue and history
                self.data_queue.put(data)
                self.add_to_history(data)
                
                # Log data
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
        self.connect_serial()
        self.thread = threading.Thread(target=self.data_receiver_thread)
        self.thread.daemon = True
        self.thread.start()
        logging.info("Telemetry receiver started")
    
    def stop(self):
        """Stop the telemetry receiver"""
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()
        logging.info("Telemetry receiver stopped")

# Initialize telemetry receiver
telemetry = TelemetryReceiver()
telemetry.start()

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Zephyrus Live Telemetry"

# Define the layout
app.layout = html.Div([
    html.Div([
        html.H1("Zephyrus Live Telemetry Dashboard", className="header-title"),
        html.Div([
            html.Div(id="connection-status", className="status-indicator"),
            html.Div(f"Mode: {'Mock Data' if telemetry.mock_mode else 'Live Hardware'}", 
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
    Input('interval-component', 'n_intervals')
)
def update_telemetry_store(n):
    """Update telemetry data store"""
    return {
        'timestamp': [t.isoformat() for t in telemetry.data_history['timestamp']],
        'vehicle_speed': telemetry.data_history['vehicle_speed'],
        'battery_voltage': telemetry.data_history['battery_voltage'],
        'battery_soc': telemetry.data_history['battery_soc'],
        'min_cell_temp': telemetry.data_history['min_cell_temp'],
        'max_cell_temp': telemetry.data_history['max_cell_temp'],
        'inverter_temp': telemetry.data_history['inverter_temp']
    }

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
    
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
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
                'bar': {'color': "green"},
                'steps': [
                    {'range': [300, 340], 'color': "red"},
                    {'range': [340, 380], 'color': "yellow"},
                    {'range': [380, 420], 'color': "lightgreen"}],
                'threshold': {'line': {'color': "red", 'width': 4},
                             'thickness': 0.75, 'value': 320}}))
    
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
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
                'bar': {'color': "orange"},
                'steps': [
                    {'range': [0, 20], 'color': "red"},
                    {'range': [20, 50], 'color': "yellow"},
                    {'range': [50, 100], 'color': "lightgreen"}],
                'threshold': {'line': {'color': "red", 'width': 4},
                             'thickness': 0.75, 'value': 15}}))
    
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
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
        marker_color=['blue', 'red', 'orange'],
        text=[f'{temp:.1f}°C' for temp in [current_min_temp, current_max_temp, current_inv_temp]],
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Current Temperatures",
        yaxis_title="Temperature (°C)",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
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
        line=dict(color='blue', width=2)
    ))
    
    fig.update_layout(
        title="Vehicle Speed Over Time",
        xaxis_title="Time",
        yaxis_title="Speed (km/h)",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40)
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
        line=dict(color='green', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['battery_soc'],
        mode='lines+markers',
        name='SOC (%)',
        yaxis='y2',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title="Battery Parameters Over Time",
        xaxis_title="Time",
        yaxis=dict(title="Voltage (V)", side="left"),
        yaxis2=dict(title="SOC (%)", side="right", overlaying="y"),
        height=300,
        margin=dict(l=40, r=40, t=40, b=40)
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
        line=dict(color='blue', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['max_cell_temp'],
        mode='lines+markers',
        name='Max Cell Temp',
        line=dict(color='red', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['inverter_temp'],
        mode='lines+markers',
        name='Inverter Temp',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title="Temperature Monitoring Over Time",
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    return fig

# Add custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Arial', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .main-container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .header-title {
                margin: 0;
                font-size: 2.5em;
                text-align: center;
            }
            .status-bar {
                display: flex;
                justify-content: space-between;
                margin-top: 10px;
            }
            .gauge-row, .mixed-row, .chart-row {
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }
            .gauge-container {
                flex: 1;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .chart-container {
                flex: 1;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .chart-container-full {
                width: 100%;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=8050)
    except KeyboardInterrupt:
        telemetry.stop()
        print("\nTelemetry dashboard stopped.")