"""
layout editor callbacks
"""
import dash
from dash import dcc, html, Input, Output, callback, State, ALL, MATCH, ctx
import plotly.graph_objs as go
import json
import uuid
from datetime import datetime

# Import config from your layout.py
from layout import AVAILABLE_VARIABLES, AVAILABLE_CHARTS

# Import constants from your config.py
from config import (
    CHART_FONT, CHART_FONT_SIZE, TITLE_FONT_SIZE, 
    SPEED_GAUGE_CONFIG, VOLTAGE_GAUGE_CONFIG, SOC_GAUGE_CONFIG
)

# This helper function creates the dynamic graphs
# I've updated it to use your multi-file app's variable names and gauge configs
def create_dynamic_figure(variable, chart_type, data):
    fig = go.Figure()
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                      font=dict(color='#e8e8e8', family=CHART_FONT),
                      xaxis=dict(color='#e8e8e8', gridcolor='#34495e'),
                      yaxis=dict(color='#e8e8e8', gridcolor='#34495e'))

    if not data or not data.get(variable) or not data.get('timestamp'):
        return fig

    # Ensure timestamps are valid before converting
    valid_timestamps = []
    valid_y_data = []
    for t_str, y_val in zip(data['timestamp'], data[variable]):
        try:
            valid_timestamps.append(datetime.fromisoformat(t_str))
            valid_y_data.append(y_val)
        except (ValueError, TypeError):
            continue # Skip invalid data points
    
    if not valid_y_data:
        return fig

    timestamps = valid_timestamps
    y_data = valid_y_data
    current_value = y_data[-1] if y_data else 0
    title = AVAILABLE_VARIABLES.get(variable, 'Unknown Variable')

    if chart_type == 'gauge':
        # Use ranges from your existing config.py
        ranges = {
            'speedMPH': SPEED_GAUGE_CONFIG['range'], 
            'pack_voltage': VOLTAGE_GAUGE_CONFIG['range'], 
            'pack_SOC': SOC_GAUGE_CONFIG['range']
        }
        # Provide a default range if variable is not a standard gauge
        range_val = ranges.get(variable, [min(y_data), max(y_data) if max(y_data) > 0 else 100])
        
        fig = go.Figure(go.Indicator(mode="gauge+number", value=current_value,
                                     domain={'x': [0, 1], 'y': [0, 1]},
                                     title={'text': title},
                                     gauge={'axis': {'range': range_val}, 'bar': {'color': "#27ae60"}}))
    elif chart_type == 'timeseries':
        fig.add_trace(go.Scatter(x=timestamps, y=y_data, mode='lines', name=title, line=dict(color='#ffd700')))
        fig.update_layout(title=title, xaxis_title="Time")
    elif chart_type == 'bar':
        fig.add_trace(go.Bar(x=[title], y=[current_value], text=[f'{current_value:.1f}'],
                             textposition='auto', marker_color='#3498db'))
        fig.update_layout(title=f"Current {title}")

    fig.update_layout(height=300, margin=dict(l=40, r=20, t=60, b=40),
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                      font=dict(color='#e8e8e8', family=CHART_FONT),
                      transition={'duration': 50, 'easing': 'cubic-in-out'})
    return fig


# Main function to register all editor callbacks
def register_layout_editor_callbacks(app):

    @app.callback(
        Output('custom-dashboard-view-container', 'children'),
        Input('layout-config-store', 'data')
    )
    def render_custom_dashboard_view(layout_config):
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
                        dcc.Graph(id={'type': 'dynamic-graph', 'index': col_data['id']},
                                  config={'displayModeBar': False})
                    ], className="chart-container", style={'width': col_width})
                )
            rows.append(html.Div(columns, className="chart-row"))
        return rows

    @app.callback(
        Output('layout-editor-container', 'children'), 
        Input('layout-config-store', 'data')
    )
    def render_layout_editor(layout_config):
        if not layout_config or 'rows' not in layout_config:
            return []
        
        # Header Section
        editor_header = html.Div([
            html.H2("Layout Editor", className="editor-title"),
            html.Button("💾 Export to settings.json", id="export-layout-btn", className="control-btn export-btn")
        ], className="editor-header")

        editor_rows = []
        for i, row_data in enumerate(layout_config['rows']):
            row_id = row_data['id']
            column_editors = []
            
            for col_data in row_data['columns']:
                col_id = col_data['id']
                column_editors.append(html.Div([
                    html.Label("Column Settings", className="editor-col-label"),
                    dcc.Dropdown(
                        id={'type': 'variable-select', 'index': col_id},
                        options=[{'label': v, 'value': k} for k, v in AVAILABLE_VARIABLES.items()],
                        value=col_data['variable'], 
                        clearable=False,
                        className="editor-dropdown"
                    ),
                    dcc.Dropdown(
                        id={'type': 'chart-select', 'index': col_id},
                        options=[{'label': v, 'value': k} for k, v in AVAILABLE_CHARTS.items()],
                        value=col_data['chart'], 
                        clearable=False,
                        className="editor-dropdown"
                    ),
                    html.Button("Remove Column", id={'type': 'remove-col-btn', 'index': col_id}, n_clicks=0, className="btn-remove-col")
                ], className="editor-col-card"))

            # Row Card
            editor_rows.append(html.Div([
                html.Div([
                    html.H4(f"Row {i + 1}", className="row-title"),
                    html.Div([
                        html.Button("＋ Add Column", id={'type': 'add-col-btn', 'index': row_id}, n_clicks=0, className="btn-add-col"),
                        html.Button("× Remove Row", id={'type': 'remove-row-btn', 'index': row_id}, n_clicks=0, className="btn-remove-row")
                    ], className="row-controls-top")
                ], className="row-header"),
                
                html.Div(column_editors, className="editor-columns-grid"),
                
            ], className="editor-row-card"))
        
        add_row_button = html.Div([
            html.Button("＋ Add New Row", id={'type': 'add-row-btn', 'index': 'main'}, n_clicks=0, className="btn-add-row")
        ], className="add-row-container")
        
        return html.Div([editor_header] + editor_rows + [add_row_button], className="editor-container")

    @app.callback(
        Output("download-layout-json", "data"),
        Input("export-layout-btn", "n_clicks"),
        State("layout-config-store", "data"),
        prevent_initial_call=True,
    )
    def export_layout(n_clicks, layout_config):
        if n_clicks is None or ctx.triggered_id != 'export-layout-btn':
            return dash.no_update
        
        # Format for export (as in your original file)
        output_list = []
        for row in layout_config.get('rows', []):
            row_list = []
            for col in row.get('columns', []):
                row_list.append([col.get('chart'), col.get('variable')])
            output_list.append(row_list)
        json_string = json.dumps(output_list, indent=4)
        
        return dict(content=json_string, filename="settings.json")

    @app.callback(
        Output('layout-config-store', 'data', allow_duplicate=True),
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
        if not isinstance(triggered_id, dict):
            return dash.no_update

        trigger_type = triggered_id.get('type')
        trigger_index = triggered_id.get('index')

        if trigger_type == 'add-row-btn':
            new_config['rows'].append({'id': str(uuid.uuid4()), 'columns': [{'id': str(uuid.uuid4()), 'variable': 'speedMPH', 'chart': 'gauge'}]})
        elif trigger_type == 'remove-row-btn':
            new_config['rows'] = [row for row in new_config['rows'] if row['id'] != trigger_index]
        elif trigger_type == 'add-col-btn':
            for row in new_config['rows']:
                if row['id'] == trigger_index:
                    row['columns'].append({'id': str(uuid.uuid4()), 'variable': 'pack_SOC', 'chart': 'timeseries'})
                    break
        elif trigger_type == 'remove-col-btn':
            for row in new_config['rows']:
                original_cols = len(row['columns'])
                row['columns'] = [col for col in row['columns'] if col['id'] != trigger_index]
                if len(row['columns']) < original_cols and not row['columns']:
                    new_config['rows'] = [r for r in new_config['rows'] if r['id'] != row['id']]
                    break
        elif trigger_type in ['variable-select', 'chart-select']:
            prop = 'variable' if trigger_type == 'variable-select' else 'chart'
            # Correctly get the value from the triggered input
            value = ctx.inputs[f'{{"index":"{trigger_index}","type":"{trigger_type}"}}.value']
            for row in new_config['rows']:
                for col in row['columns']:
                    if col['id'] == trigger_index:
                        col[prop] = value
                        return new_config
        return new_config

    @app.callback(
        Output({'type': 'dynamic-graph', 'index': ALL}, 'figure'),
        Input('interval-component', 'n_intervals'),
        Input('dashboard-tabs', 'value'),
        State('telemetry-store', 'data'), # This store is populated by your existing callbacks.py
        State('layout-config-store', 'data'),
        State({'type': 'dynamic-graph', 'index': ALL}, 'id')
    )
    def update_all_dynamic_graphs(n_intervals, active_tab, telemetry_data, layout_config, graph_ids):
        if active_tab != 'tab-custom-view':
            raise dash.exceptions.PreventUpdate
        if not graph_ids:
            raise dash.exceptions.PreventUpdate
        if not layout_config or not telemetry_data:
            return [go.Figure()] * len(graph_ids)

        col_config_map = {}
        for row in layout_config['rows']:
            for col in row['columns']:
                col_config_map[col['id']] = (col['variable'], col['chart'])

        figures = []
        for graph_id in graph_ids:
            col_id = graph_id['index']
            if col_id in col_config_map:
                variable, chart_type = col_config_map[col_id]
                figures.append(create_dynamic_figure(variable, chart_type, telemetry_data))
            else:
                figures.append(go.Figure())
        return figures