"""
Configuration constants for the telemetry dashboard
"""

import os
import pathlib

# API Configuration
API_URL = "http://localhost:3000/api/telemetry"
API_POLL_RATE = 0.05  # 50ms between polls
API_TIMEOUT = 2  # 2 second timeout

# Update intervals
UPDATE_INTERVAL = 50  # Dash callback interval in milliseconds

# Styling Constants
PRIMARY_FONT = 'Arial, sans-serif'
CHART_FONT = 'Arial'
CHART_FONT_SIZE = 12
TITLE_FONT_SIZE = 16
BORDER_RADIUS = '20px'

# Chart Configuration
CHART_HEIGHT = 300
CHART_MARGIN = dict(l=20, r=20, t=80, b=20)
TEMP_CHART_HEIGHT = 260
TEMP_CHART_MARGIN = dict(l=20, r=20, t=80, b=20)

# Chart Colors
CHART_COLORS = {
    'primary': '#ffd700',
    'background': '#0f1419',
    'container': '#1e2329',
    'text': '#e8e8e8',
    'min_cell_temp': '#3498db',
    'max_cell_temp': '#e74c3c',
    'inverter_temp': '#ffd700',
    'speed_line': '#3498db',
    'voltage_gauge': '#27ae60',
    'soc_gauge': '#ffd700'
}

# Gauge Configurations
SPEED_GAUGE_CONFIG = {
    'range': [None, 150],
    'bar_color': "darkblue",
    'steps': [
        {'range': [0, 50], 'color': "lightgray"},
        {'range': [50, 100], 'color': "gray"},
        {'range': [100, 150], 'color': "red"}
    ],
    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 120}
}

VOLTAGE_GAUGE_CONFIG = {
    'range': [300, 420],
    'bar_color': "#27ae60",
    'steps': [
        {'range': [300, 340], 'color': "#e74c3c"},
        {'range': [340, 380], 'color': "#f39c12"},
        {'range': [380, 420], 'color': "#2c3e50"}
    ],
    'threshold': {'line': {'color': "#e74c3c", 'width': 4}, 'thickness': 0.75, 'value': 320}
}

SOC_GAUGE_CONFIG = {
    'range': [0, 100],
    'bar_color': "#ffd700",
    'steps': [
        {'range': [0, 20], 'color': "#e74c3c"},
        {'range': [20, 50], 'color': "#f39c12"},
        {'range': [50, 100], 'color': "#2c3e50"}
    ],
    'threshold': {'line': {'color': "#e74c3c", 'width': 4}, 'thickness': 0.75, 'value': 15}
}

# File paths
BASE_DIR = pathlib.Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"
LOG_DIRECTORY = BASE_DIR.parent / "telemetry_logs"

# Ensure log directory exists
LOG_DIRECTORY.mkdir(exist_ok=True)

# Status indicator thresholds
VOLTAGE_THRESHOLDS = {
    'good': 380,
    'caution': 340
}

SOC_THRESHOLDS = {
    'good': 50,
    'caution': 20
}

# Data limits
MAX_DATA_POINTS = 100  # Maximum number of data points to keep in memory