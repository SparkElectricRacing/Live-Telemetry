"""
All dashboard callbacks
"""

import os
import shutil
import logging
import dash
from datetime import datetime
from dash import Output, Input, State, html, callback_context, exceptions

from config import MAX_DATA_POINTS, LOG_DIRECTORY

# sets up all interactive behavior in the dashboard 
def register_all_callbacks(app, telemetry_receiver):
    """Register all dashboard callbacks"""
    
    # Control callbacks
    @app.callback(
        Output('connection-status', 'children'),
        Input('start-btn', 'n_clicks'),
        Input('stop-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_start_stop_collection(start_clicks, stop_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'start-btn':
            logging.info("Start Collection clicked")
            if not telemetry_receiver.running:
                telemetry_receiver.start()
                logging.info("Telemetry collection started")
            return "Collecting Data"
            
        elif button_id == 'stop-btn':
            logging.info("Stop Collection clicked")
            telemetry_receiver.stop()
            logging.info("elemetry collection stopped")
            return "Stopped"
        
    # update the stored telemetry data
    @app.callback(
        Output('telemetry-store', 'data'),
        Input('interval-component', 'n_intervals'), # dash interval component fires every few seconds
        State('telemetry-store', 'data')
    )
    def update_telemetry_store(n, existing_data):
        logging.info(f" CALLBACK: Telemetry store update called (interval {n})")
        logging.info(f"  Queue size: {telemetry_receiver.data_queue.qsize()}")
        logging.info(f"  Telemetry running: {telemetry_receiver.running}")
        logging.info(f"  Mock mode: {telemetry_receiver.mock_mode}")
        logging.info(f"  Playback mode: {telemetry_receiver.playback_mode}")
        
        # Get new data points from the queue
        new_data_points = telemetry_receiver.get_data_from_queue()
        
        if not new_data_points:
            logging.info("   📋 Total data points retrieved from queue: 0")
            if existing_data is None:
                logging.info("   🆕 Using initial data structure")
                # Return initial empty data structure with all backend signals
                return {
                    'timestamp': [],
                    'speedMPH': [],
                    'rpm_speed': [],
                    'pack_voltage': [],
                    'pack_SOC': [],
                    'avg_temp': [],
                    'avg_cell_voltage': [],
                    'low_cell_voltage': [],
                    'high_cell_voltage': [],
                    'max_cell_temp': [],
                    'is_charging': [],
                    'DTC1': []
                }
            else:
                logging.info(" No new data points available - UI will not update")
                return dash.no_update
        
        logging.info(f"Total data points retrieved from queue: {len(new_data_points)}")
        
        # Initialize or update data
        if existing_data is None:
            data = {
                'timestamp': [],
                'speedMPH': [],
                'rpm_speed': [],
                'pack_voltage': [],
                'pack_SOC': [],
                'avg_temp': [],
                'avg_cell_voltage': [],
                'low_cell_voltage': [],
                'high_cell_voltage': [],
                'max_cell_temp': [],
                'is_charging': [],
                'DTC1': []
            }
        else:
            data = existing_data.copy()

        # Add new data points
        for point in new_data_points:
            data['timestamp'].append(point['timestamp'])
            data['speedMPH'].append(point.get('speedMPH', 0))
            data['rpm_speed'].append(point.get('rpm_speed', 0))
            data['pack_voltage'].append(point.get('pack_voltage', 0))
            data['pack_SOC'].append(point.get('pack_SOC', 0))
            data['avg_temp'].append(point.get('avg_temp', 0))
            data['avg_cell_voltage'].append(point.get('avg_cell_voltage', 0))
            data['low_cell_voltage'].append(point.get('low_cell_voltage', 0))
            data['high_cell_voltage'].append(point.get('high_cell_voltage', 0))
            data['max_cell_temp'].append(point.get('max_cell_temp', 0))
            data['is_charging'].append(point.get('is_charging', False))
            data['DTC1'].append(point.get('DTC1', 0))
        
        # Keep only the last MAX_DATA_POINTS to prevent memory issues
        for key in data:
            if len(data[key]) > MAX_DATA_POINTS:
                data[key] = data[key][-MAX_DATA_POINTS:]
        
        logging.info(f"  Updated telemetry store with {len(new_data_points)} new data points")
        logging.info(f"  Total data points in store: {len(data['timestamp'])}")
        
        return data

    # updates internal flags on data collection mode
    @app.callback(
        Output('data-mode-selector', 'value'),
        Input('data-mode-selector', 'value')
    )
    def handle_mode_selection(selected_mode):
        if selected_mode == "mock":
            telemetry_receiver.mock_mode = True
            telemetry_receiver.api_available = False
            logging.info("Switched to Mock Data mode")
        elif selected_mode == "live":
            telemetry_receiver.mock_mode = False
            telemetry_receiver.test_api_connection()  # Test API availability
            logging.info("Switched to Live API mode")

        return selected_mode

    @app.callback(
        Output('error-notification', 'children'),
        Output('error-notification', 'className'),
        Input('data-mode-selector', 'value')
    )
    def update_error_notification(selected_mode):
        if selected_mode == "live" and not telemetry_receiver.api_available:
            return "⚠️ API not available, using mock data", "error-notification warning"
        return "", "error-notification hidden"

    # playback callbacks 
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
                    logging.info(f"Play button clicked with file: {selected_file}")
                    if telemetry_receiver.playback_mode and telemetry_receiver.playback_paused:
                        telemetry_receiver.resume_playback()
                        logging.info("Resumed playback")
                    else:
                        logging.info(f"Starting playback of: {selected_file}")
                        success = telemetry_receiver.start_playback(selected_file)
                        if not success:
                            logging.error(f"Failed to start playback of: {selected_file}")
                            return "Error loading log file", False, True, True
                    
                elif button_id == 'pause-btn':
                    logging.info("Pause button clicked")
                    telemetry_receiver.pause_playback()
                    
                elif button_id == 'stop-playback-btn':
                    logging.info("Stop playback button clicked")
                    telemetry_receiver.stop_playback()
            
            # Update status and button states based on current playback state
            if telemetry_receiver.playback_mode:
                if telemetry_receiver.playback_paused:
                    status = f" Paused at {telemetry_receiver.playback_index}/{len(telemetry_receiver.playback_data)}"
                    return status, False, False, False  # play enabled, pause enabled, stop enabled
                elif telemetry_receiver.playback_index >= len(telemetry_receiver.playback_data):
                    status = " Playback Complete"
                    return status, False, True, False  # play enabled, pause disabled, stop enabled
                else:
                    status = f" Playing {telemetry_receiver.playback_index}/{len(telemetry_receiver.playback_data)}"
                    return status, True, False, False  # play disabled, pause enabled, stop enabled
            else:
                if selected_file:
                    status = " Ready to play"
                    return status, False, True, True  # play enabled, pause disabled, stop disabled
                else:
                    status = "Select a log file to begin playback"
                    return status, True, True, True  # all disabled
                    
        except Exception as e:
            logging.error(f"Error in playback controls: {e}")
            return f"Error: {str(e)}", False, True, True

    # File management callbacks
    @app.callback(
        Output('log-files-list', 'children'),
        Output('selected-log-file', 'options'),
        Output('selected-file-for-action', 'options'),
        Input('page-load-trigger', 'data'),
        Input('start-btn', 'n_clicks'),
        Input('stop-btn', 'n_clicks')
    )
    def update_log_files_list(page_load, start_clicks, stop_clicks):
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
            playback_dropdown_options = []
            file_action_dropdown_options = []
            
            for log_file in log_files:
                file_elements.append(
                    html.Div([
                        html.Span(log_file['filename'], className="log-filename"),
                        html.Span(f"{log_file['size_kb']:.1f} KB", className="log-size"),
                        html.Span(log_file['modified'].strftime("%Y-%m-%d %H:%M"), className="log-time")
                    ], className="log-file-item clickable-log-file", id={'type': 'log-file-item', 'index': log_file['filepath']})
                )
                
                # Options for playback dropdown (needs full filepath)
                playback_dropdown_options.append({
                    'label': f"{log_file['filename']} - {log_file['size_kb']:.1f}KB - {log_file['modified'].strftime('%m/%d %H:%M')}",
                    'value': log_file['filepath']
                })
                
                # Options for file action dropdown (just filename)
                file_action_dropdown_options.append({
                    'label': f"{log_file['filename']} ({log_file['size_kb']:.1f}KB)",
                    'value': log_file['filename']
                })
            
            return file_elements, playback_dropdown_options, file_action_dropdown_options
            
        except Exception as e:
            return [html.Div(f"Error loading log files: {e}")], [], []

    # log file operations 
    @app.callback(
        Output('log-files-list', 'children', allow_duplicate=True),
        Output('selected-log-file', 'options', allow_duplicate=True),
        Output('selected-file-for-action', 'options', allow_duplicate=True),
        Output('selected-file-for-action', 'value'),
        Output('new-name-input', 'value'),
        Output('file-operation-status', 'children'),
        Input('delete-file-btn', 'n_clicks'),
        Input('rename-file-btn', 'n_clicks'),
        Input('delete-all-btn', 'n_clicks'),
        State('selected-file-for-action', 'value'),
        State('new-name-input', 'value'),
        prevent_initial_call=True
    )
    def handle_file_operations(delete_clicks, rename_clicks, delete_all_clicks, selected_filename, new_name):
        ctx = callback_context
        if not ctx.triggered:
            raise exceptions.PreventUpdate
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        status_message = ""
        
        try:
            if button_id == 'delete-file-btn' and selected_filename:
                file_path = os.path.join(LOG_DIRECTORY, selected_filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    status_message = f"✅ Deleted: {selected_filename}"
                    logging.info(f"Deleted log file: {selected_filename}")
                else:
                    status_message = f"❌ File not found: {selected_filename}"
            elif button_id == 'delete-file-btn':
                status_message = "❌ Please select a file to delete"
                    
            elif button_id == 'rename-file-btn' and selected_filename and new_name:
                old_path = os.path.join(LOG_DIRECTORY, selected_filename)
                # Ensure new name has .log extension
                if not new_name.endswith('.log'):
                    new_name += '.log'
                new_path = os.path.join(LOG_DIRECTORY, new_name)
                
                if os.path.exists(old_path):
                    if not os.path.exists(new_path):
                        os.rename(old_path, new_path)
                        status_message = f"✅ Renamed: {selected_filename} → {new_name}"
                        logging.info(f"Renamed log file: {selected_filename} → {new_name}")
                    else:
                        status_message = f"❌ File already exists: {new_name}"
                else:
                    status_message = f"❌ File not found: {selected_filename}"
            elif button_id == 'rename-file-btn' and not selected_filename:
                status_message = "❌ Please select a file to rename"
            elif button_id == 'rename-file-btn' and not new_name:
                status_message = "❌ Please enter a new filename"
                    
            elif button_id == 'delete-all-btn':
                deleted_count = 0
                for filename in os.listdir(LOG_DIRECTORY):
                    if filename.endswith('.log'):
                        file_path = os.path.join(LOG_DIRECTORY, filename)
                        os.remove(file_path)
                        deleted_count += 1
                        logging.info(f"Deleted log file: {filename}")
                
                if deleted_count > 0:
                    status_message = f" Successfully deleted {deleted_count} log files"
                else:
                    status_message = " No log files found to delete"
                    
            else:
                status_message = "❌ Invalid operation or missing parameters"
                
        except Exception as e:
            logging.error(f"Error during file operation: {e}")
            status_message = f"❌ Error: {str(e)}"
        
        # Refresh the list and clear inputs
        files, playback_options, action_options = update_log_files_list(0, 0, 0)
        return files, playback_options, action_options, None, "", status_message