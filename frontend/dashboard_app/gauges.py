"""
Gauge creation functions
"""

import plotly.graph_objects as go
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CHART_HEIGHT, CHART_MARGIN, CHART_FONT_SIZE, CHART_FONT, TITLE_FONT_SIZE,
    SPEED_GAUGE_CONFIG, VOLTAGE_GAUGE_CONFIG, SOC_GAUGE_CONFIG, RPM_GAUGE_CONFIG
)


def create_rpm_gauge(data: Dict[str, Any]) -> go.Figure:
    """Create RPM gauge chart"""
    current_rpm = abs(data['rpm_speed'][-1]) if data['rpm_speed'] else 0
    previous_rpm = abs(data['rpm_speed'][-2]) if len(data['rpm_speed']) > 1 else current_rpm
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_rpm,
        domain={'x': [0, 1], 'y': [0, 1]},
        # title={'text': "Motor RPM"},
        delta={'reference': previous_rpm},
        gauge={
            'axis': {'range': RPM_GAUGE_CONFIG['range']},
            'bar': {'color': RPM_GAUGE_CONFIG['bar_color']},
            'steps': RPM_GAUGE_CONFIG['steps'],
            'threshold': RPM_GAUGE_CONFIG['threshold']
        }
    ))
    
    fig.update_layout(
        title=dict(
            text="Motor RPM",
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(color='#e8e8e8', size=20, family=CHART_FONT)
        ),
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=60, b=20), # Reduced top margin slightly for layout title
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    
    return fig


def create_speed_gauge(data: Dict[str, Any]) -> go.Figure:
    """Create speed gauge chart"""
    current_speed = data['speedMPH'][-1] if data['speedMPH'] else 0
    previous_speed = data['speedMPH'][-2] if len(data['speedMPH']) > 1 else current_speed
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_speed,
        domain={'x': [0, 1], 'y': [0, 1]},
        # title={'text': "Vehicle Speed (mph)"}, # Moved to layout
        delta={'reference': previous_speed},
        gauge={
            'axis': {'range': SPEED_GAUGE_CONFIG['range']},
            'bar': {'color': SPEED_GAUGE_CONFIG['bar_color']},
            'steps': SPEED_GAUGE_CONFIG['steps'],
            #'threshold': SPEED_GAUGE_CONFIG['threshold']
        }
    ))
    
    fig.update_layout(
        title=dict(
            text="Vehicle Speed (mph)",
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(color='#e8e8e8', size=20, family=CHART_FONT)
        ),
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    
    return fig


def create_voltage_gauge(data: Dict[str, Any]) -> go.Figure:
    """Create voltage gauge chart"""
    current_voltage = data['pack_voltage'][-1] if data['pack_voltage'] else 0
    previous_voltage = data['pack_voltage'][-2] if len(data['pack_voltage']) > 1 else current_voltage
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_voltage,
        domain={'x': [0, 1], 'y': [0, 1]},
        # title={'text': "Battery Voltage (V)"},
        delta={'reference': previous_voltage},
        gauge={
            'axis': {'range': VOLTAGE_GAUGE_CONFIG['range']},
            'bar': {'color': VOLTAGE_GAUGE_CONFIG['bar_color']},
            'steps': VOLTAGE_GAUGE_CONFIG['steps'],
            'threshold': VOLTAGE_GAUGE_CONFIG['threshold']
        }
    ))
    
    fig.update_layout(
        title=dict(
            text="Battery Voltage (V)",
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(color='#e8e8e8', size=20, family=CHART_FONT)
        ),
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    
    return fig


def create_soc_gauge(data: Dict[str, Any]) -> go.Figure:
    """Create SOC gauge chart"""
    current_soc = data['pack_SOC'][-1] if data['pack_SOC'] else 0
    previous_soc = data['pack_SOC'][-2] if len(data['pack_SOC']) > 1 else current_soc
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_soc,
        domain={'x': [0, 1], 'y': [0, 1]},
        # title={'text': "Battery SOC (%)"},
        delta={'reference': previous_soc},
        gauge={
            'axis': {'range': SOC_GAUGE_CONFIG['range']},
            'bar': {'color': SOC_GAUGE_CONFIG['bar_color']},
            'steps': SOC_GAUGE_CONFIG['steps'],
            'threshold': SOC_GAUGE_CONFIG['threshold']
        }
    ))
    
    fig.update_layout(
        title=dict(
            text="Battery SOC (%)",
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)
        ),
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8e8e8', size=CHART_FONT_SIZE, family=CHART_FONT)
    )
    
    return fig