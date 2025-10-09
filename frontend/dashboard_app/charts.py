"""
Charts: component creation and callbacks
"""

import dash
import plotly.graph_objects as go
from dash import Output, Input
from datetime import datetime
from typing import Dict, Any

from config import (
    CHART_HEIGHT, CHART_MARGIN, CHART_FONT_SIZE, CHART_FONT, TITLE_FONT_SIZE,
    TEMP_CHART_HEIGHT, TEMP_CHART_MARGIN, CHART_COLORS,
    VOLTAGE_THRESHOLDS, SOC_THRESHOLDS
)
from gauges import create_speed_gauge, create_voltage_gauge, create_soc_gauge


# Chart Creation Functions
def create_speed_timeseries(data: Dict[str, Any]) -> go.Figure:
    """Create speed time series chart"""
    if not data['timestamp']:
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text="Vehicle Speed Over Time (No Data)",
                font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
            ),
            yaxis_title="Speed (km/h)",
            xaxis_title="Time",
            yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
            xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
            height=CHART_HEIGHT,
            margin=CHART_MARGIN,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e8e8e8', family=CHART_FONT)
        )
        return fig
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['vehicle_speed'],
        mode='lines',
        name='Vehicle Speed',
        line=dict(color=CHART_COLORS['speed_line'])
    ))
    
    fig.update_layout(
        title=dict(
            text="Vehicle Speed Over Time",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="Speed (km/h)",
        xaxis_title="Time",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT),
        legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT))
    )
    
    return fig


def create_voltage_timeseries(data: Dict[str, Any]) -> go.Figure:
    """Create voltage time series chart"""
    if not data['timestamp']:
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text="Battery Voltage Over Time (No Data)",
                font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
            ),
            yaxis_title="Voltage (V)",
            xaxis_title="Time",
            yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
            xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
            height=CHART_HEIGHT,
            margin=CHART_MARGIN,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e8e8e8', family=CHART_FONT)
        )
        return fig
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['battery_voltage'],
        mode='lines',
        name='Battery Voltage',
        line=dict(color=CHART_COLORS['voltage_gauge'])
    ))
    
    fig.update_layout(
        title=dict(
            text="Battery Voltage Over Time",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="Voltage (V)",
        xaxis_title="Time",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT),
        legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT))
    )
    
    return fig


def create_soc_timeseries(data: Dict[str, Any]) -> go.Figure:
    """Create SOC time series chart"""
    if not data['timestamp']:
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text="Battery SOC Over Time (No Data)",
                font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
            ),
            yaxis_title="SOC (%)",
            xaxis_title="Time",
            yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
            xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
            height=CHART_HEIGHT,
            margin=CHART_MARGIN,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e8e8e8', family=CHART_FONT)
        )
        return fig
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['battery_soc'],
        mode='lines',
        name='Battery SOC',
        line=dict(color=CHART_COLORS['soc_gauge'])
    ))
    
    fig.update_layout(
        title=dict(
            text="Battery SOC Over Time",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="SOC (%)",
        xaxis_title="Time",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT),
        legend=dict(font=dict(color='#e8e8e8', family=CHART_FONT))
    )
    
    return fig


def create_temperature_timeseries(data: Dict[str, Any]) -> go.Figure:
    """Create temperature time series chart"""
    if not data['timestamp']:
        return go.Figure()
    
    timestamps = [datetime.fromisoformat(t) for t in data['timestamp']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['min_cell_temp'],
        mode='lines',
        name='Min Cell',
        line=dict(color=CHART_COLORS['min_cell_temp'])
    ))
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['max_cell_temp'],
        mode='lines',
        name='Max Cell',
        line=dict(color=CHART_COLORS['max_cell_temp'])
    ))
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=data['inverter_temp'],
        mode='lines',
        name='Inverter',
        line=dict(color=CHART_COLORS['inverter_temp'])
    ))
    
    fig.update_layout(
        title=dict(
            text="Temperatures Over Time",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="Temperature (°C)",
        xaxis_title="Time",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
        height=TEMP_CHART_HEIGHT,
        margin=TEMP_CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT)
    )
    
    return fig


def create_temperature_bar_chart(data: Dict[str, Any]) -> go.Figure:
    """Create temperature bar chart"""
    if not data['timestamp']:
        min_temp, max_temp, inv_temp = 0, 0, 0
    else:
        min_temp = data['min_cell_temp'][-1]
        max_temp = data['max_cell_temp'][-1]
        inv_temp = data['inverter_temp'][-1]
    
    fig = go.Figure(go.Bar(
        x=['Min Cell', 'Max Cell', 'Inverter'],
        y=[min_temp, max_temp, inv_temp],
        marker_color=[
            CHART_COLORS['min_cell_temp'],
            CHART_COLORS['max_cell_temp'],
            CHART_COLORS['inverter_temp']
        ],
        text=[f'{min_temp:.1f}°C', f'{max_temp:.1f}°C', f'{inv_temp:.1f}°C'],
        textposition='auto',
        textfont=dict(color='#1e2329', size=CHART_FONT_SIZE, family=CHART_FONT)
    ))
    
    fig.update_layout(
        autosize=False,
        title=dict(
            text="Current Temperatures",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="Temperature (°C)",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e', range=[0, 80], fixedrange=True),
        xaxis=dict(color='#e8e8e8', fixedrange=True),
        height=TEMP_CHART_HEIGHT,
        margin=TEMP_CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT)
    )
    
    return fig


def create_empty_temperature_timeseries() -> go.Figure:
    """Create empty temperature time series for no data state"""
    fig = go.Figure()
    fig.update_layout(
        title=dict(
            text="Temperatures Over Time (No Data)",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="Temperature (°C)",
        xaxis_title="Time",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
        xaxis=dict(color='#e8e8e8', gridcolor='#34495e', fixedrange=True),
        height=TEMP_CHART_HEIGHT,
        margin=TEMP_CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT)
    )
    return fig


def create_empty_temperature_bar_chart() -> go.Figure:
    """Create empty temperature bar chart for no data state"""
    fig = go.Figure(go.Bar(
        x=['Min Cell', 'Max Cell', 'Inverter'],
        y=[0, 0, 0],
        marker_color=[
            CHART_COLORS['min_cell_temp'],
            CHART_COLORS['max_cell_temp'],
            CHART_COLORS['inverter_temp']
        ],
        text=['0.0°C', '0.0°C', '0.0°C'],
        textposition='auto',
        textfont=dict(color='#1e2329', size=CHART_FONT_SIZE, family=CHART_FONT)
    ))
    
    fig.update_layout(
        autosize=False,
        title=dict(
            text="Current Temperatures (No Data)",
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        yaxis_title="Temperature (°C)",
        yaxis=dict(color='#e8e8e8', gridcolor='#34495e', range=[0, 80], fixedrange=True),
        xaxis=dict(color='#e8e8e8', fixedrange=True),
        height=TEMP_CHART_HEIGHT,
        margin=TEMP_CHART_MARGIN,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', family=CHART_FONT)
    )
    
    return fig


# Chart Callbacks
def register_chart_callbacks(app, telemetry_receiver):
    """Register all chart-related callbacks"""
    
    @app.callback(
        Output('speed-gauge', 'figure'),
        Input('telemetry-store', 'data')
    )
    def update_speed_gauge(data):
        return create_speed_gauge(data)

    @app.callback(
        Output('voltage-gauge', 'figure'),
        Input('telemetry-store', 'data')
    )
    def update_voltage_gauge(data):
        return create_voltage_gauge(data)

    @app.callback(
        Output('soc-gauge', 'figure'),
        Input('telemetry-store', 'data')
    )
    def update_soc_gauge(data):
        return create_soc_gauge(data)

    @app.callback(
        Output('speed-timeseries', 'figure'),
        Input('telemetry-store', 'data')
    )
    def update_speed_timeseries(data):
        return create_speed_timeseries(data)

    @app.callback(
        Output('voltage-timeseries', 'figure'),
        Input('telemetry-store', 'data')
    )
    def update_voltage_timeseries(data):
        return create_voltage_timeseries(data)

    @app.callback(
        Output('soc-timeseries', 'figure'),
        Input('telemetry-store', 'data')
    )
    def update_soc_timeseries(data):
        return create_soc_timeseries(data)

    @app.callback(
        Output('temp-overview', 'figure'),
        Output('toggle-temp-chart-btn', 'children'),
        Input('telemetry-store', 'data'),
        Input('toggle-temp-chart-btn', 'n_clicks')
    )
    def update_temp_overview(data, n_clicks):
        if n_clicks is None:
            n_clicks = 0

        # Check if we have data - if not, show empty/zero values  
        if not data or not data.get('timestamp') or len(data['timestamp']) == 0:
            button_text = "Switch to Time Series" if n_clicks % 2 == 0 else "Switch to Current Values"
            
            if n_clicks % 2 == 1:
                # Time series mode when no data
                return create_empty_temperature_timeseries(), button_text
            else:
                # Current values mode when no data - show zeros
                return create_empty_temperature_bar_chart(), button_text

        # Normal operation when we have data
        if n_clicks % 2 == 1:
            button_text = "Switch to Current Values"
            return create_temperature_timeseries(data), button_text
        else:
            button_text = "Switch to Time Series"
            return create_temperature_bar_chart(data), button_text

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
        
        # Voltage status
        voltage = data['battery_voltage'][-1]
        if voltage >= VOLTAGE_THRESHOLDS['good']:
            v_status, v_class = "OK", "status-good"
        elif voltage >= VOLTAGE_THRESHOLDS['caution']:
            v_status, v_class = "Caution", "status-caution"
        else:
            v_status, v_class = "Warning", "status-warning"
        
        v_text = f"Voltage: {v_status}"
        v_classname = f"status-indicator {v_class}"
        
        # SOC status
        soc = data['battery_soc'][-1]
        if soc >= SOC_THRESHOLDS['good']:
            s_status, s_class = "OK", "status-good"
        elif soc >= SOC_THRESHOLDS['caution']:
            s_status, s_class = "Caution", "status-caution"
        else:
            s_status, s_class = "Warning", "status-warning"
        
        s_text = f"SOC: {s_status}"
        s_classname = f"status-indicator {s_class}"
        
        return v_text, v_classname, s_text, s_classname