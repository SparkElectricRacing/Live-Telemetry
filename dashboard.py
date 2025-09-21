import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import serial
import threading
import queue
import time
from datetime import datetime, timedelta
import logging
import os
import random

# =========================
# Configuration
# =========================
SERIAL_PORT = 'COM3'   # Adjust for your system
BAUD_RATE = 9600
LOG_DIRECTORY = 'telemetry_logs'
UPDATE_INTERVAL = 500   # ms between UI updates
ROLLING_POINTS = 120    # keep last N points visible in streaming charts

os.makedirs(LOG_DIRECTORY, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIRECTORY}/telemetry_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# =========================
# Telemetry Receiver
# =========================
class TelemetryReceiver:
    def __init__(self):
        self.data_queue = queue.Queue()
        self.serial_connection = None
        self.running = False
        self.mock_mode = True
        self.max_points = 5000
        self.data_history = {
            'timestamp': [], 'vehicle_speed': [], 'battery_voltage': [],
            'battery_soc': [], 'min_cell_temp': [], 'max_cell_temp': [], 'inverter_temp': []
        }

    def connect_serial(self):
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
        now = datetime.now()
        return {
            'timestamp': now.isoformat(),
            'vehicle_speed': random.uniform(0, 120),
            'battery_voltage': random.uniform(320, 400),
            'battery_soc': random.uniform(20, 100),
            'min_cell_temp': random.uniform(20, 45),
            'max_cell_temp': random.uniform(25, 50),
            'inverter_temp': random.uniform(30, 80)
        }

    def parse_telemetry_packet(self, raw_data):
        try:
            data = {'timestamp': datetime.now().isoformat()}
            pairs = raw_data.strip().split(',')
            key_map = {'SPEED': 'vehicle_speed', 'VOLT': 'battery_voltage', 'SOC': 'battery_soc',
                       'TEMP_MIN': 'min_cell_temp', 'TEMP_MAX': 'max_cell_temp', 'INV_TEMP': 'inverter_temp'}
            for pair in pairs:
                if ':' in pair:
                    key, value = pair.split(':')
                    if key in key_map:
                        data[key_map[key]] = float(value)
            return data
        except Exception as e:
            logging.error(f"Error parsing telemetry packet: {e}")
            return None

    def data_receiver_thread(self):
        while self.running:
            try:
                if self.mock_mode:
                    data = self.generate_mock_data()
                    time.sleep(0.1)  # ~10 Hz
                elif self.serial_connection and self.serial_connection.in_waiting:
                    raw_data = self.serial_connection.readline().decode('utf-8')
                    data = self.parse_telemetry_packet(raw_data)
                else:
                    time.sleep(0.01)
                    continue
                if data:
                    self.data_queue.put(data)
                    self.add_to_history(data)
            except Exception as e:
                logging.error(f"Error in data receiver: {e}")
                time.sleep(1)

    def add_to_history(self, data):
        timestamp = datetime.fromisoformat(data['timestamp'])
        for key in self.data_history:
            self.data_history[key].append(data.get(key, 0) if key != 'timestamp' else timestamp)
        if len(self.data_history['timestamp']) > self.max_points:
            for key in self.data_history:
                self.data_history[key] = self.data_history[key][-self.max_points:]

    def start(self):
        self.running = True
        self.connect_serial()
        self.thread = threading.Thread(target=self.data_receiver_thread, daemon=True)
        self.thread.start()
        logging.info("Telemetry receiver started")

    def stop(self):
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()
        logging.info("Telemetry receiver stopped")

# =========================
# Dash App
# =========================
telemetry = TelemetryReceiver()
telemetry.start()

app = dash.Dash(__name__)
app.title = "Zephyrus Live Telemetry"

# --- Figure Initializers for Streaming ---
def init_speed_figure():
    fig = go.Figure(go.Scatter(x=[], y=[], mode='lines', name='Speed', line=dict(color='blue', width=2)))
    fig.update_layout(title="Vehicle Speed Over Time", yaxis=dict(range=[0, 150], title="Speed (km/h)", dtick=25),
                      height=300, margin=dict(l=40, r=20, t=40, b=40), uirevision="speed_ts")
    return fig

def init_battery_figure():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='Voltage', yaxis='y', line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='SOC', yaxis='y2', line=dict(color='orange', width=2)))
    fig.update_layout(title="Battery Parameters Over Time", yaxis=dict(title="Voltage (V)", side="left", range=[300, 420]),
                      yaxis2=dict(title="SOC (%)", side="right", overlaying="y", range=[0, 100]),
                      legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top'),
                      height=300, margin=dict(l=40, r=40, t=40, b=40), uirevision="battery_ts")
    return fig

def init_temp_figure():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='Min Cell', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='Max Cell', line=dict(color='red', width=2)))
    fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='Inverter', line=dict(color='orange', width=2)))
    fig.update_layout(title="Temperature Monitoring Over Time", yaxis={'range': [10, 90], 'title': "Temperature (°C)"},
                      legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top'),
                      height=300, margin=dict(l=40, r=20, t=40, b=40), uirevision="temp_ts")
    return fig

# --- App Layout ---
app.layout = html.Div(className="main-container", children=[
    html.Div(className="header", children=[
        html.H1("Zephyrus Live Telemetry Dashboard", className="header-title"),
        html.Div(className="status-bar", children=[
            html.Div(id="mode-label", className="mode-indicator")
        ])
    ]),
    html.Div(className="dashboard-content", children=[
        html.Div(className="gauge-row", children=[
            html.Div(dcc.Graph(id="speed-gauge"), className="gauge-container"),
            html.Div(className="gauge-container", children=[
                dcc.Graph(id="voltage-gauge"),
                html.Div(id="voltage-status-indicator")
            ]),
        ]),
        html.Div(className="mixed-row", children=[
            html.Div(className="gauge-container", children=[
                dcc.Graph(id="soc-gauge"),
                html.Div(id="soc-status-indicator")
            ]),
            html.Div(dcc.Graph(id="temp-overview"), className="chart-container"),
        ]),
        html.Div(className="chart-row", children=[
            html.Div(dcc.Graph(id="speed-timeseries", figure=init_speed_figure()), className="chart-container"),
            html.Div(dcc.Graph(id="battery-timeseries", figure=init_battery_figure()), className="chart-container"),
        ]),
        html.Div(className="chart-row", children=[
            html.Div(dcc.Graph(id="temperature-timeseries", figure=init_temp_figure()), className="chart-container-full"),
        ]),
    ]),
    dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),
    dcc.Store(id='telemetry-store')
])

# --- Callbacks ---
@callback(Output('telemetry-store', 'data'), Input('interval-component', 'n_intervals'))
def update_telemetry_store(n):
    return {key: ([t.isoformat() for t in val] if key == 'timestamp' else val)
            for key, val in telemetry.data_history.items()}

@callback(Output('mode-label', 'children'), Input('telemetry-store', 'data'))
def update_mode_label(data):
    return f"Mode: {'Mock Data' if telemetry.mock_mode else 'Live Hardware'}"

@callback(
    Output('voltage-status-indicator', 'children'),
    Output('voltage-status-indicator', 'className'),
    Output('soc-status-indicator', 'children'),
    Output('soc-status-indicator', 'className'),
    Input('telemetry-store', 'data')
)
def update_status_indicators(data):
    if not data['timestamp']:
        return dash.no_update

    voltage = data['battery_voltage'][-1]
    if voltage >= 380: v_status, v_class = "Green", "status-good"
    elif voltage >= 340: v_status, v_class = "Yellow", "status-caution"
    else: v_status, v_class = "Red", "status-warning"
    v_text = f"Voltage: {v_status}"
    v_classname = f"status-indicator {v_class}"
    
    soc = data['battery_soc'][-1]
    if soc >= 50: s_status, s_class = "Green", "status-good"
    elif soc >= 20: s_status, s_class = "Yellow", "status-caution"
    else: s_status, s_class = "Red", "status-warning"
    s_text = f"SOC: {s_status}"
    s_classname = f"status-indicator {s_class}"
    
    return v_text, v_classname, s_text, s_classname

def create_gauge(data, key, title, range_val, color, steps, dtick=None):
    value = data[key][-1] if data[key] else 0
    reference = data[key][-2] if len(data[key]) > 1 else value
    axis = {'range': range_val, 'tickwidth': 2, 'tickcolor': '#333'}
    if dtick is not None:
        axis['dtick'] = dtick

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title},
        delta={'reference': reference, 'valueformat': '.1f'},
        gauge={
            'axis': axis,
            'bar': {'color': color},
            'steps': steps,
            # MODIFIED: The needle has been restored for precise readings
            'threshold': {
                'line': {'color': '#111', 'width': 4},
                'thickness': 0.9,
                'value': value
            },
            'borderwidth': 2,
            'bordercolor': '#ddd'
        }
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        transition={'duration': 280, 'easing': 'cubic-in-out'}
    )
    return fig

@callback(Output('speed-gauge', 'figure'), Input('telemetry-store', 'data'))
def update_speed_gauge(data):
    return create_gauge(
        data, 'vehicle_speed', "Vehicle Speed (km/h)",
        [0, 150], "darkblue",
        steps=[{'range': [0, 90], 'color': "lightgray"},
               {'range': [90, 120], 'color': "gray"}],
        dtick=10
    )

@callback(Output('voltage-gauge', 'figure'), Input('telemetry-store', 'data'))
def update_voltage_gauge(data):
    return create_gauge(
        data, 'battery_voltage', "Battery Voltage (V)",
        [300, 420], "green",
        steps=[{'range': [300, 340], 'color': "red"},
               {'range': [340, 380], 'color': "yellow"},
               {'range': [380, 420], 'color': "lightgreen"}],
        dtick=20
    )

@callback(Output('soc-gauge', 'figure'), Input('telemetry-store', 'data'))
def update_soc_gauge(data):
    return create_gauge(
        data, 'battery_soc', "Battery SOC (%)",
        [0, 100], "orange",
        steps=[{'range': [0, 20], 'color': "red"},
               {'range': [20, 50], 'color': "yellow"},
               {'range': [50, 100], 'color': "lightgreen"}],
        dtick=10
    )

@callback(Output('temp-overview', 'figure'), Input('telemetry-store', 'data'))
def update_temp_overview(data):
    if not data['timestamp']: return go.Figure()
    temps = {'Min Cell': data['min_cell_temp'][-1], 'Max Cell': data['max_cell_temp'][-1], 'Inverter': data['inverter_temp'][-1]}
    fig = go.Figure(go.Bar(x=list(temps.keys()), y=list(temps.values()),
                           marker_color=['blue', 'red', 'orange'], text=[f'{t:.1f}°C' for t in temps.values()], textposition='auto'))
    fig.update_layout(title="Current Temperatures", yaxis=dict(title="Temperature (°C)", range=[0, 100]),
                      height=300, margin=dict(l=20, r=20, t=40, b=20),
                      transition={'duration': 280, 'easing': 'cubic-in-out'})
    return fig

# --- Streaming Callbacks ---
@callback(Output('speed-timeseries', 'extendData'), Input('telemetry-store', 'data'))
def stream_speed_chart(data):
    if not data['timestamp']: return dash.no_update
    t = datetime.fromisoformat(data['timestamp'][-1])
    y = data['vehicle_speed'][-1]
    return (dict(x=[[t]], y=[[y]]), [0], ROLLING_POINTS)

@callback(Output('battery-timeseries', 'extendData'), Input('telemetry-store', 'data'))
def stream_battery_chart(data):
    if not data['timestamp']: return dash.no_update
    t = datetime.fromisoformat(data['timestamp'][-1])
    v = data['battery_voltage'][-1]
    s = data['battery_soc'][-1]
    return (dict(x=[[t], [t]], y=[[v], [s]]), [0, 1], ROLLING_POINTS)

@callback(Output('temperature-timeseries', 'extendData'), Input('telemetry-store', 'data'))
def stream_temp_chart(data):
    if not data['timestamp']: return dash.no_update
    t = datetime.fromisoformat(data['timestamp'][-1])
    min_t, max_t, inv_t = data['min_cell_temp'][-1], data['max_cell_temp'][-1], data['inverter_temp'][-1]
    return (dict(x=[[t], [t], [t]], y=[[min_t], [max_t], [inv_t]]), [0, 1, 2], ROLLING_POINTS)

# =========================
# Custom index / styles
# =========================
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; }
            .main-container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 20px; margin-bottom: 20px; text-align: center; }
            .header-title { margin: 0; font-size: 2.5em; }
            .mode-indicator { font-size: 1em; opacity: 0.9; }
            .gauge-row, .mixed-row, .chart-row { display: flex; gap: 20px; margin-bottom: 20px; justify-content: center; }
            .gauge-container {
                position: relative; 
                width: calc(50% - 10px); background: white; border-radius: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 10px;
            }
            .chart-container {
                width: calc(50% - 10px); background: white; border-radius: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 10px;
            }
            .chart-container-full {
                width: 100%; background: white; border-radius: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 10px;
            }
            .status-bar { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 15px; }
            .status-indicator { 
                position: absolute;
                top: 20px;
                right: 20px;
                z-index: 10;
                padding: 5px 15px; border-radius: 15px; color: white; 
                font-weight: bold; font-size: 0.9em; transition: all 0.3s ease; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .status-good { background-color: #28a745; }
            .status-caution { background-color: #ffc107; color: #1f2937; }
            .status-warning { background-color: #dc3545; }
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

# =========================
# Entrypoint
# =========================
if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=8050)
    except KeyboardInterrupt:
        pass
    finally:
        telemetry.stop()
        print("\nTelemetry dashboard stopped.")