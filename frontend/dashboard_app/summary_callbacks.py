"""
Summary and analysis callbacks for log files
"""

import os
import json
import logging
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import dash
from dash import Output, Input, html, callback_context, exceptions, State, ALL
from datetime import datetime

from config import LOG_DIRECTORY, CHART_COLORS, CHART_FONT, TITLE_FONT_SIZE, CHART_FONT_SIZE


def register_summary_callbacks(app):
    """Register callbacks for log file summary and analysis"""

    # Handle clicking on a log file
    @app.callback(
        Output('selected-log-for-summary', 'data'),
        Input({'type': 'log-file-item', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_log_file_click(n_clicks_list):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise exceptions.PreventUpdate

        # Find which file was clicked
        triggered_prop = ctx.triggered[0]['prop_id']

        try:
            # Extract the JSON part before the dot (the ID)
            if '.n_clicks' in triggered_prop:
                id_str = triggered_prop.replace('.n_clicks', '')
                # Parse the pattern-matching ID
                import ast
                file_info = ast.literal_eval(id_str)
                filepath = file_info['index']
                logging.info(f"Log file clicked for summary: {filepath}")
                return filepath
        except Exception as e:
            logging.error(f"Error parsing clicked file ID: {e}")
            logging.error(f"Triggered prop: {triggered_prop}")

        raise exceptions.PreventUpdate

    # Load and display summary statistics
    @app.callback(
        Output('summary-stats-container', 'children'),
        Input('selected-log-for-summary', 'data'),
        prevent_initial_call=True
    )
    def display_summary_statistics(selected_filepath):
        if not selected_filepath:
            return html.Div("No file selected", className="no-data-message")

        try:
            # Load the log file
            data_records = []
            with open(selected_filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('{') and line.endswith('}'):
                        try:
                            data_records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            if not data_records:
                return html.Div("No valid data in file", className="no-data-message")

            # Create DataFrame
            df = pd.DataFrame(data_records)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Calculate statistics
            stats = {
                'vehicle_speed': {
                    'label': 'Vehicle Speed (km/h)',
                    'avg': df['vehicle_speed'].mean(),
                    'max': df['vehicle_speed'].max(),
                    'min': df['vehicle_speed'].min(),
                    'color': CHART_COLORS['primary']
                },
                'battery_voltage': {
                    'label': 'Battery Voltage (V)',
                    'avg': df['battery_voltage'].mean(),
                    'max': df['battery_voltage'].max(),
                    'min': df['battery_voltage'].min(),
                    'color': CHART_COLORS['voltage_gauge']
                },
                'battery_soc': {
                    'label': 'Battery SOC (%)',
                    'avg': df['battery_soc'].mean(),
                    'max': df['battery_soc'].max(),
                    'min': df['battery_soc'].min(),
                    'color': CHART_COLORS['soc_gauge']
                },
                'inverter_temp': {
                    'label': 'Inverter Temp (°C)',
                    'avg': df['inverter_temp'].mean(),
                    'max': df['inverter_temp'].max(),
                    'min': df['inverter_temp'].min(),
                    'color': CHART_COLORS['inverter_temp']
                }
            }

            # Duration
            duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
            duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"

            # Create stat cards
            stat_cards = []

            # Duration card
            stat_cards.append(
                html.Div([
                    html.H4("Session Duration", className="stat-card-title"),
                    html.Div(duration_str, className="stat-card-value-large"),
                    html.Div(f"{len(df)} data points", className="stat-card-subtitle")
                ], className="stat-card stat-card-duration")
            )

            # Stat cards for each metric
            for key, data in stats.items():
                stat_cards.append(
                    html.Div([
                        html.H4(data['label'], className="stat-card-title"),
                        html.Div([
                            html.Div([
                                html.Span("Avg: ", className="stat-label"),
                                html.Span(f"{data['avg']:.1f}", className="stat-value", style={'color': data['color']})
                            ], className="stat-row"),
                            html.Div([
                                html.Span("Max: ", className="stat-label"),
                                html.Span(f"{data['max']:.1f}", className="stat-value")
                            ], className="stat-row"),
                            html.Div([
                                html.Span("Min: ", className="stat-label"),
                                html.Span(f"{data['min']:.1f}", className="stat-value")
                            ], className="stat-row")
                        ], className="stat-card-content")
                    ], className="stat-card")
                )

            filename = os.path.basename(selected_filepath)
            return html.Div([
                html.H4(f"Analysis: {filename}", className="summary-title"),
                html.Div(stat_cards, className="stat-cards-grid")
            ])

        except Exception as e:
            logging.error(f"Error loading summary statistics: {e}")
            return html.Div(f"Error loading file: {str(e)}", className="error-message")

    # Create summary time series plot
    @app.callback(
        Output('summary-timeseries-plot', 'figure'),
        Input('selected-log-for-summary', 'data'),
        prevent_initial_call=True
    )
    def display_summary_plots(selected_filepath):
        if not selected_filepath:
            return go.Figure()

        try:
            # Load the log file
            data_records = []
            with open(selected_filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('{') and line.endswith('}'):
                        try:
                            data_records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            if not data_records:
                return go.Figure()

            # Create DataFrame
            df = pd.DataFrame(data_records)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Create subplots with 3 rows
            fig = make_subplots(
                rows=3,
                cols=1,
                subplot_titles=("Vehicle Speed", "Battery SOC & Voltage", "Temperatures"),
                shared_xaxes=True,
                vertical_spacing=0.08,
                specs=[[{"secondary_y": False}],
                       [{"secondary_y": True}],
                       [{"secondary_y": False}]]
            )

            # Row 1: Vehicle Speed
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['vehicle_speed'],
                    mode='lines',
                    name='Speed (km/h)',
                    line=dict(color=CHART_COLORS['primary'], width=2)
                ),
                row=1, col=1
            )

            # Row 2: Battery SOC (left y-axis) and Voltage (right y-axis)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['battery_soc'],
                    mode='lines',
                    name='SOC (%)',
                    line=dict(color=CHART_COLORS['soc_gauge'], width=2)
                ),
                row=2, col=1, secondary_y=False
            )

            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['battery_voltage'],
                    mode='lines',
                    name='Voltage (V)',
                    line=dict(color=CHART_COLORS['voltage_gauge'], width=2)
                ),
                row=2, col=1, secondary_y=True
            )

            # Row 3: Temperatures
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['min_cell_temp'],
                    mode='lines',
                    name='Min Cell Temp',
                    line=dict(color=CHART_COLORS['min_cell_temp'], width=2)
                ),
                row=3, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['max_cell_temp'],
                    mode='lines',
                    name='Max Cell Temp',
                    line=dict(color=CHART_COLORS['max_cell_temp'], width=2)
                ),
                row=3, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['inverter_temp'],
                    mode='lines',
                    name='Inverter Temp',
                    line=dict(color=CHART_COLORS['inverter_temp'], width=2)
                ),
                row=3, col=1
            )

            # Update axes
            fig.update_xaxes(title_text="Time", row=3, col=1, color='#e8e8e8', gridcolor='#34495e')
            fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1, color='#e8e8e8', gridcolor='#34495e')
            fig.update_yaxes(title_text="SOC (%)", row=2, col=1, color='#e8e8e8', gridcolor='#34495e', secondary_y=False)
            fig.update_yaxes(title_text="Voltage (V)", row=2, col=1, color='#e8e8e8', secondary_y=True)
            fig.update_yaxes(title_text="Temperature (°C)", row=3, col=1, color='#e8e8e8', gridcolor='#34495e')

            # Update layout
            filename = os.path.basename(selected_filepath)
            fig.update_layout(
                title=dict(text=f"Telemetry Data: {filename}", font=dict(color='#e8e8e8', size=TITLE_FONT_SIZE, family=CHART_FONT)),
                height=900,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color='#e8e8e8', family=CHART_FONT)
                ),
                plot_bgcolor=CHART_COLORS['background'],
                paper_bgcolor=CHART_COLORS['background'],
                font=dict(color='#e8e8e8', family=CHART_FONT, size=CHART_FONT_SIZE),
                hovermode='x unified'
            )

            return fig

        except Exception as e:
            logging.error(f"Error creating summary plot: {e}")
            return go.Figure()
