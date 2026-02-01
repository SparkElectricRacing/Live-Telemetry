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
            # If we are in playback mode, stop it first
            if telemetry_receiver.playback_mode:
                telemetry_receiver.stop_playback()
                telemetry_receiver.playback_mode = False
                
            if not telemetry_receiver.running:
                telemetry_receiver.start()
                logging.info("Telemetry collection started")
            return "Collecting Data"
            
        elif button_id == 'stop-btn':
            logging.info("Stop Collection clicked")
            telemetry_receiver.stop()
            logging.info("Telemetry collection stopped")
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
                    'DTC1': [],
                    'gps_lat': [],
                    'gps_lon': []
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
                'DTC1': [],
                'gps_lat': [],
                'gps_lon': []
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
            
            data.setdefault('gps_lat', []).append(point.get('gps_lat', 33.53250))
            data.setdefault('gps_lon', []).append(point.get('gps_lon', -86.61889))
        
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
            telemetry_receiver.playback_mode = False
            telemetry_receiver.api_available = False
            logging.info("Switched to Mock Data mode")
        elif selected_mode == "live":
            telemetry_receiver.mock_mode = False
            telemetry_receiver.playback_mode = False
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
        Output('prev-step-btn', 'disabled'),
        Output('next-step-btn', 'disabled'),
        Output('playback-slider', 'max'),
        Output('playback-slider', 'value'),
        Output('playback-slider', 'disabled'),
        Output('playback-frame-input', 'value'), # Update input value
        Output('playback-total-frames', 'children'), # Update total count label
        Input('play-btn', 'n_clicks'),
        Input('pause-btn', 'n_clicks'),
        Input('stop-playback-btn', 'n_clicks'),
        Input('prev-step-btn', 'n_clicks'),
        Input('next-step-btn', 'n_clicks'),
        Input('playback-slider', 'value'), # Slider input
        Input('playback-speed-selector', 'value'), # Speed input
        Input('playback-frame-input', 'value'), # Text input
        Input('selected-log-file', 'value'), # MOVED TO INPUT to trigger update on selection
        Input('interval-component', 'n_intervals'),
        prevent_initial_call=True
    )
    def handle_playback_controls(play_clicks, pause_clicks, stop_clicks, prev_clicks, next_clicks, slider_value, speed_value, frame_input_value, selected_file, n_intervals):
        try:
            ctx = dash.callback_context
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            
            # Update speed if it changed or on any interaction (safe to set repeatedly)
            if speed_value:
                 telemetry_receiver.playback_speed = speed_value

            # Default Return States
            # Status, PlayDis, PauseDis, StopDis, PrevDis, NextDis, Max, Value, SliderDis
            
            if triggered_id == 'play-btn' and selected_file:
                 logging.info(f"Play button clicked with file: {selected_file}")
                 telemetry_receiver.mock_mode = False
                 
                 if telemetry_receiver.playback_mode and telemetry_receiver.playback_paused and telemetry_receiver.playback_file == selected_file:
                      telemetry_receiver.resume_playback()
                 else:
                      telemetry_receiver.start_playback(selected_file)
            
            elif triggered_id == 'pause-btn':
                 telemetry_receiver.pause_playback()
            
            elif triggered_id == 'stop-playback-btn':
                 telemetry_receiver.stop_playback()
                 
            elif triggered_id == 'prev-step-btn':
                 telemetry_receiver.step_playback(-1)
                 if not telemetry_receiver.playback_paused:
                      telemetry_receiver.pause_playback()
            
            elif triggered_id == 'next-step-btn':
                 telemetry_receiver.step_playback(1)
                 if not telemetry_receiver.playback_paused:
                      telemetry_receiver.pause_playback()
                      
            elif triggered_id == 'playback-slider':
                 # Seek if slider changed
                 # If not in playback mode but file selected, start playback in paused state
                 if not telemetry_receiver.playback_mode and selected_file:
                      logging.info(f"Slider moved, starting paused playback for: {selected_file}")
                      telemetry_receiver.mock_mode = False
                      if telemetry_receiver.start_playback(selected_file):
                           telemetry_receiver.pause_playback()
                           telemetry_receiver.seek_playback(slider_value)

                 if telemetry_receiver.playback_mode:
                      if abs(slider_value - telemetry_receiver.playback_index) > 1:
                           telemetry_receiver.seek_playback(slider_value)
                           if not telemetry_receiver.playback_paused:
                                telemetry_receiver.pause_playback()
            
            elif triggered_id == 'selected-log-file':
                 if selected_file:
                      logging.info(f"File selected: {selected_file}. Pre-loading for playback.")
                      telemetry_receiver.mock_mode = False
                      if telemetry_receiver.start_playback(selected_file):
                           telemetry_receiver.pause_playback()
                           # Reset to 0
                           telemetry_receiver.seek_playback(0)

            elif triggered_id == 'playback-frame-input':
                 # Seek if text input changed
                 # Similar logic to slider, but using frame_input_value
                 # Ensure value is valid integer
                 if frame_input_value is not None:
                     target_index = int(frame_input_value)
                     
                     if not telemetry_receiver.playback_mode and selected_file:
                          logging.info(f"Frame input changed, starting paused playback for: {selected_file}")
                          telemetry_receiver.mock_mode = False
                          if telemetry_receiver.start_playback(selected_file):
                               telemetry_receiver.pause_playback()
                               telemetry_receiver.seek_playback(target_index)

                     if telemetry_receiver.playback_mode:
                          if abs(target_index - telemetry_receiver.playback_index) > 0: # strict equality check might be annoying if typing?
                               telemetry_receiver.seek_playback(target_index)
                               if not telemetry_receiver.playback_paused:
                                    telemetry_receiver.pause_playback()

            elif triggered_id == 'playback-speed-selector':
                 # Already handled by the check at top of function
                 logging.info(f"Playback speed changed to: {speed_value}")

            # --- Update UI State ---
            if telemetry_receiver.playback_mode:
                max_val = len(telemetry_receiver.playback_data) - 1
                curr_val = telemetry_receiver.playback_index
                
                # status text (playing/paused)
                status_text = "Paused" if telemetry_receiver.playback_paused else "Running"
                total_label = f"/ {max_val + 1}"
                
                if telemetry_receiver.playback_paused:
                     status_text = "Paused"
                     # Play: En, Pause: Dis, Stop: En, Prev: En, Next: En, Slider: En
                     # Returns: Status, PlayDis, PauseDis, StopDis, PrevDis, NextDis, Max, SliderVal, SliderDis, InputVal, TotalLabel
                     return status_text, False, True, False, False, False, max_val, curr_val, False, curr_val, total_label
                else:
                    status_text = "Playing" 
                    # Play: Dis, Pause: En, Stop: En, Prev: En, Next: En, Slider: En (acts as display)
                    return status_text, True, False, False, False, False, max_val, curr_val, False, curr_val, total_label
            else:
                # Not in playback mode
                status_text = "Ready" if selected_file else "Select File"
                # All playback specific controls disabled except Play (if file selected)
                play_enabled = not bool(selected_file)
                slider_disabled = not bool(selected_file)
                max_val = 100 # Default
                
                return status_text, play_enabled, True, True, True, True, max_val, 0, slider_disabled, 0, "/ 0"

        except Exception as e:
            logging.error(f"Error in playback controls: {e}")
            return f"Error: {str(e)}", False, True, True, True, True, 100, 0, True, 0, "/ 0"



    @app.callback(
        Output('selected-log-file', 'options'),
        Input('page-load-trigger', 'data'),
        Input('start-btn', 'n_clicks'),
        Input('stop-btn', 'n_clicks'),
        Input('delete-file-btn', 'n_clicks'),
        Input('rename-file-btn', 'n_clicks'),
        Input('delete-all-btn', 'n_clicks')
    )
    def update_log_files_list(page_load, start_clicks, stop_clicks, del_clicks, ren_clicks, del_all_clicks):
        try:
            log_files = []
            if os.path.exists(LOG_DIRECTORY):
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
            dropdown_options = []
            
            for log_file in log_files:
                # Format: "Jan 01 2024 14:30:00 - telemetry.log (120KB)"
                date_str = log_file['modified'].strftime('%b %d %Y %H:%M:%S')
                dropdown_options.append({
                    'label': f"{date_str} - {log_file['filename']} ({log_file['size_kb']:.1f}KB)",
                    'value': log_file['filepath']
                })
            
            return dropdown_options
            
        except Exception as e:
            logging.error(f"Error loading log files: {e}")
            return []

    # Toggle Log Management Dropdown
    @app.callback(
        Output('log-management-dropdown', 'style'),
        Input('manage-logs-btn', 'n_clicks'),
        State('log-management-dropdown', 'style')
    )
    def toggle_log_dropdown(n_clicks, current_style):
        if n_clicks and n_clicks > 0:
            if current_style.get('display') == 'none':
                new_style = current_style.copy()
                new_style['display'] = 'block'
                return new_style
            else:
                new_style = current_style.copy()
                new_style['display'] = 'none'
                return new_style
        return current_style

    # log file operations 
    @app.callback(
        Output('selected-log-file', 'value'),
        Output('new-name-input', 'value'),
        Output('file-operation-status', 'children'),
        Input('delete-file-btn', 'n_clicks'),
        Input('rename-file-btn', 'n_clicks'),
        Input('delete-all-btn', 'n_clicks'),
        State('selected-log-file', 'value'),
        State('new-name-input', 'value'),
        prevent_initial_call=True
    )
    def handle_file_operations(delete_clicks, rename_clicks, delete_all_clicks, selected_filepath, new_name):
        ctx = callback_context
        if not ctx.triggered:
            raise exceptions.PreventUpdate
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        status_message = ""
        
        try:
            if button_id == 'delete-file-btn' and selected_filepath:
                if os.path.exists(selected_filepath):
                    os.remove(selected_filepath)
                    filename = os.path.basename(selected_filepath)
                    status_message = f"✅ Deleted: {filename}"
                    logging.info(f"Deleted log file: {filename}")
                else:
                    status_message = f"❌ File not found: {selected_filepath}"
            elif button_id == 'delete-file-btn':
                status_message = "❌ Please select a file to delete"
                    
            elif button_id == 'rename-file-btn' and selected_filepath and new_name:
                # Ensure new name has .log extension
                if not new_name.endswith('.log'):
                    new_name += '.log'
                
                new_path = os.path.join(LOG_DIRECTORY, new_name)
                filename = os.path.basename(selected_filepath)
                
                if os.path.exists(selected_filepath):
                    if not os.path.exists(new_path):
                        os.rename(selected_filepath, new_path)
                        status_message = f"✅ Renamed: {filename} → {new_name}"
                        logging.info(f"Renamed log file: {filename} → {new_name}")
                    else:
                        status_message = f"❌ File already exists: {new_name}"
                else:
                    status_message = f"❌ File not found: {filename}"
            elif button_id == 'rename-file-btn' and not selected_filepath:
                status_message = "❌ Please select a file to rename"
            elif button_id == 'rename-file-btn' and not new_name:
                status_message = "❌ Please enter a new filename"
                    
            elif button_id == 'delete-all-btn':
                deleted_count = 0
                if os.path.exists(LOG_DIRECTORY):
                    for filename in os.listdir(LOG_DIRECTORY):
                        if filename.endswith('.log'):
                            # Avoid deleting active log if running? 
                            # Simple approach: try copy/delete
                            file_path = os.path.join(LOG_DIRECTORY, filename)
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                            except Exception as e:
                                logging.warning(f"Failed to delete {filename}: {e}")
                
                if deleted_count > 0:
                    status_message = f" Successfully deleted {deleted_count} log files"
                else:
                    status_message = " No log files found to delete"
                    
            else:
                status_message = "❌ Invalid operation or missing parameters"
                
        except Exception as e:
            logging.error(f"Error during file operation: {e}")
            status_message = f"❌ Error: {str(e)}"
        
        # Return: Clear selected file (None), Clear new name (""), Status message
        return None, "", status_message

    # --- NEW: Toggle View Visibility ---
    @app.callback(
        Output('static-dashboard-container', 'style'),
        Output('custom-dashboard-view-container', 'style'),
        Output('layout-editor-container', 'style'),
        Input('dashboard-tabs', 'value')
    )
    def render_content(tab):
        show = {'display': 'block'}
        hide = {'display': 'none'}
        if tab == 'tab-static':
            return show, hide, hide
        elif tab == 'tab-custom-view':
            return hide, show, hide
        elif tab == 'tab-editor':
            return hide, hide, show
        return show, hide, hide

    # --- NEW: GPS Map Callback ---
    @app.callback(
        Output("gps-marker", "position"),
        Input("telemetry-store", "data")
    )
    def update_gps_marker(data):
        if data and 'gps_lat' in data and 'gps_lon' in data and len(data['gps_lat']) > 0:
            # Get the latest GPS coordinates
            lat = data['gps_lat'][-1]
            lon = data['gps_lon'][-1]
            return [lat, lon]
        # Default dummy position if no data
        return [33.53250, -86.61889]