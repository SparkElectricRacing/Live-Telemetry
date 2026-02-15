"""
All dashboard callbacks
"""

import os
import shutil
import logging
import dash
from datetime import datetime
from dash import Output, Input, State, html, callback_context, exceptions, MATCH, ALL
import uuid

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
            
    # --- Sidebar Toggle Callback (Clientside for Map Resize) ---
    app.clientside_callback(
        """
        function(n_clicks, current_style) {
            // Calculate new style
            let newStyle = {'display': 'flex'};
            if (n_clicks > 0) {
                if (!current_style || current_style.display !== 'none') {
                    newStyle = {'display': 'none'};
                }
            }
            
            // Trigger resize event after a short delay
            setTimeout(function() {
                window.dispatchEvent(new Event('resize'));
            }, 300);
            
            // If opening (flex), update last read timestamp
            let newReadTs = window.dash_clientside.no_update;
            if (newStyle.display === 'flex') {
                newReadTs = Date.now();
            }
            
            return [newStyle, newReadTs];
        }
        """,
        Output('notification-sidebar', 'style'),
        Output('last-read-ts', 'data'),
        Input('sidebar-toggle-btn', 'n_clicks'),
        State('notification-sidebar', 'style'),
        prevent_initial_call=True
    )

    # --- Clientside Callback: Badge Visibility ---
    app.clientside_callback(
        """
        function(latest_ts, last_read_ts) {
            if (!latest_ts) return {'display': 'none'};
            if (!last_read_ts) last_read_ts = 0;
            
            if (latest_ts > last_read_ts) {
                return {'display': 'block'};
            }
            return {'display': 'none'};
        }
        """,
        Output('notification-badge', 'style'),
        Input('latest-notification-ts', 'data'),
        Input('last-read-ts', 'data')
    )

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

    # --- NEW: Notification Callback ---
    @app.callback(
        Output('notification-container', 'children'),
        Output('notification-state', 'data'),
        Output('latest-notification-ts', 'data'),
        Input('telemetry-store', 'data'),
        Input('interval-component', 'n_intervals'),
        State('notification-state', 'data'),
        State('notification-container', 'children')
    )
    def update_notifications(data, n, notification_state, current_children):
        # Import inside function to avoid circular imports
        from config import DANGER_THRESHOLDS, NOTIFICATION_COOLDOWN
        import time
        
        if not data:
            return dash.no_update, dash.no_update, dash.no_update

        # Initialize state if needed
        if notification_state is None:
            notification_state = {}
            
        current_time = time.time()
        new_notifications_added = False
        
        # Check through all thresholds
        for var_name, rules in DANGER_THRESHOLDS.items():
            if var_name in data and len(data[var_name]) > 0:
                current_value = data[var_name][-1]
                
                # Ensure rules is a list
                if isinstance(rules, dict):
                    rules = [rules]
                
                # Find all triggered rules
                active_min_rules = []
                active_max_rules = []
                
                for rule in rules:
                    if 'min' in rule and rule['min'] is not None and current_value < rule['min']:
                        active_min_rules.append(rule)
                    if 'max' in rule and rule['max'] is not None and current_value > rule['max']:
                        active_max_rules.append(rule)
                        
                # Select the most severe rule (lowest min, highest max)
                target_rules = []
                
                if active_min_rules:
                    # For min violations, the one with the lowest threshold is the most severe/specific
                    # e.g. Value 9. Triggered <50, <20, <10. We want <10.
                    most_severe_min = min(active_min_rules, key=lambda r: r['min'])
                    target_rules.append(most_severe_min)
                    
                if active_max_rules:
                    # For max violations, the one with the highest threshold is the most severe
                    # e.g. Value 130. Triggered >100, >120. We want >120.
                    most_severe_max = max(active_max_rules, key=lambda r: r['max'])
                    target_rules.append(most_severe_max)
                    
                # Process the selected target rules
                for rule in target_rules:
                    is_min = 'min' in rule and rule['min'] is not None and current_value < rule['min']
                    is_max = 'max' in rule and rule['max'] is not None and current_value > rule['max']
                    
                    if is_min:
                        rule_suffix = rule.get('id_suffix', 'low')
                        rule_id = f"{var_name}_{rule_suffix}"
                        threshold_val = rule['min']
                        default_title = f"Low {rule.get('label', var_name)}"
                        default_msg = f"Value {current_value:.1f} is below minimum {threshold_val}"
                    elif is_max:
                        rule_suffix = rule.get('id_suffix', 'high')
                        rule_id = f"{var_name}_{rule_suffix}"
                        threshold_val = rule['max']
                        default_title = f"High {rule.get('label', var_name)}"
                        default_msg = f"Value {current_value:.1f} is above maximum {threshold_val}"
                    else:
                        continue

                    # Check cooldown
                    last_time = notification_state.get(rule_id, 0)
                    if current_time - last_time > NOTIFICATION_COOLDOWN:
                        # TRIGGER NOTIFICATION
                        notification_state[rule_id] = current_time
                        
                        # Create new notification element
                        notif_id = str(uuid.uuid4())
                        
                        # Use custom message if available or construct one
                        message_text = rule.get('message', default_msg).format(value=current_value)
                        
                        new_item = html.Div([
                            html.Div([
                                html.Strong(rule.get('label', default_title), className="notification-title"),
                                html.Span("✕", id={'type': 'close-notification', 'index': notif_id}, className="notification-close")
                            ], style={'display': 'flex', 'justifyContent': 'space-between', 'width': '100%', 'marginBottom': '5px'}),
                            html.Div(message_text, className="notification-message"),
                        ], id={'type': 'notification-item', 'index': notif_id}, className=f"notification-toast {rule.get('type', 'warning')}")
                        
                        # Add to list (children)
                        if current_children is None:
                            current_children = []
                        
                        # Insert at top
                        current_children.insert(0, new_item)
                        new_notifications_added = True
                        
                        # Limit to last 50 notifications
                        if len(current_children) > 50:
                            current_children = current_children[:50]
        
        # Return updated children and state
        # Update timestamp if new notifications were added
        latest_ts = dash.no_update
        if new_notifications_added:
            latest_ts = int(time.time() * 1000) # JS timestamp
            
        return current_children, notification_state, latest_ts

    # --- NEW: Close Notification Callback ---
    @app.callback(
        Output('notification-container', 'children', allow_duplicate=True),
        Input({'type': 'close-notification', 'index': ALL}, 'n_clicks'),
        Input('clear-notifications-btn', 'n_clicks'),
        State('notification-container', 'children'),
        prevent_initial_call=True
    )
    def remove_notification(close_clicks, clear_clicks, current_children):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
            
        try:
             # Get the ID of the triggered component
             if not ctx.triggered_id:
                  return dash.no_update

             triggered_id = ctx.triggered_id
             
             # Check if Clear All was clicked
             if triggered_id == 'clear-notifications-btn':
                 logging.info("Clear All Notifications clicked")
                 return []
             
             # If for some reason it's not a dict (should be with pattern matching)
             if not isinstance(triggered_id, dict):
                 return dash.no_update
             
             # Check of n_clicks valid
             # With pattern matching callbacks, ctx.triggered is a list
             # We need to ensure the click count is valid (>0)
             
             # Find which input triggered it
             # ctx.triggered[0] is usually safe for single triggers
             prop_id = ctx.triggered[0]['prop_id']
             value = ctx.triggered[0]['value']
             
             if not value or value == 0:
                 return dash.no_update

             note_id = triggered_id['index']
             target_id = {'type': 'notification-item', 'index': note_id}
             
             if not current_children:
                 return dash.no_update
             
             # Filter out the toast with the matching ID
             # Use direct dictionary comparison now that we construct target_id correctly
             new_children = [
                 child for child in current_children 
                 if not (
                     isinstance(child, dict) and 
                     'props' in child and 
                     child['props'].get('id') == target_id
                 )
             ]
             
             return new_children
             
        except Exception as e:
            logging.error(f"Error removing notification: {e}")
            return dash.no_update