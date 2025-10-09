"""
Telemetry data receiver and processing
"""

import threading
import queue
import time
import random
import requests
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import (
    API_URL, API_POLL_RATE, API_TIMEOUT, LOG_DIRECTORY, MAX_DATA_POINTS
)


class TelemetryReceiver:
    """Handles telemetry data collection from various sources"""
    
    def __init__(self):
        self.data_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.mock_mode = True
        self.api_available = False
        self.current_log_handler = None
        
        # Playback functionality
        self.playback_mode = False
        self.playback_data = []
        self.playback_index = 0
        self.playback_paused = False
        self.playback_file = None
        
        # Test API availability on startup
        self.test_api_connection()
        
    def test_api_connection(self):
        """Test if the API is available"""
        try:
            response = requests.get(API_URL, timeout=API_TIMEOUT)
            self.api_available = response.status_code == 200
            if self.api_available:
                logging.info("✅ API connection successful")
                self.mock_mode = False
            else:
                logging.warning(f"⚠️ API responded with status {response.status_code}, using mock data")
                self.mock_mode = True
        except requests.exceptions.RequestException as e:
            logging.warning(f"⚠️ API not available ({e}), using mock data")
            self.api_available = False
            self.mock_mode = True
    
    def start(self):
        """Start telemetry data collection"""
        if not self.running:
            self.running = True
            self.start_new_log_file()
            self.thread = threading.Thread(target=self.data_receiver_thread, daemon=True)
            self.thread.start()
            logging.info("🚀 Telemetry receiver started")
    
    def stop(self):
        """Stop telemetry data collection"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1)
            logging.info("🛑 Telemetry receiver stopped")
            
            # Remove current log handler when stopping
            if self.current_log_handler:
                logging.getLogger().removeHandler(self.current_log_handler)
                self.current_log_handler.close()
                self.current_log_handler = None
    
    def start_new_log_file(self):
        """Start logging to a new file with timestamp"""
        try:
            # Remove existing file handler if any
            if self.current_log_handler:
                logging.getLogger().removeHandler(self.current_log_handler)
                self.current_log_handler.close()
            
            # Create new log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = LOG_DIRECTORY / f'telemetry_{timestamp}.log'
            
            # Create file handler with proper formatting
            self.current_log_handler = logging.FileHandler(log_filename)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            self.current_log_handler.setFormatter(formatter)
            
            # Add handler to logger
            logging.getLogger().addHandler(self.current_log_handler)
            
            logging.info(f"📝 Started logging to: {log_filename}")
            
        except Exception as e:
            logging.error(f"❌ Failed to create log file: {e}")
    
    def data_receiver_thread(self):
        """Background thread for receiving data"""
        logging.info(f"🚀 Data receiver thread started - Mock: {self.mock_mode}, Playback: {self.playback_mode}")
        
        while self.running:
            try:
                data = None
                
                # Playback mode has highest priority and blocks all other data generation
                if self.playback_mode:
                    if not self.playback_paused and self.playback_index < len(self.playback_data):
                        data = self.playback_data[self.playback_index]
                        self.playback_index += 1
                        logging.info(f"▶️ Playback: {self.playback_index}/{len(self.playback_data)} - Speed: {data['vehicle_speed']:.1f} km/h")
                        time.sleep(API_POLL_RATE)
                    elif self.playback_index >= len(self.playback_data):
                        # Playback finished - restore normal mode
                        logging.info("🏁 Playback finished, restoring normal mode")
                        self.stop_playback()
                        time.sleep(1)
                        continue
                    else:
                        # Paused
                        time.sleep(0.1)
                        continue
                        
                # Only generate other data if NOT in playback mode
                elif self.mock_mode and not self.playback_mode:
                    data = self.generate_mock_data()
                    logging.info(f"🎲 Generated mock data: {data['vehicle_speed']:.1f} km/h, {data['battery_voltage']:.1f}V")
                    time.sleep(API_POLL_RATE)
                    
                elif not self.playback_mode:  # API mode, but only if not in playback
                    data = self.fetch_api_data()
                    if data:
                        logging.info(f"📡 Received API data: {data['vehicle_speed']:.1f} km/h")
                    time.sleep(API_POLL_RATE)
                
                # Put data on the queue and log for playback
                if data:
                    self.data_queue.put(data)
                    logging.debug(f"📦 Added data to queue. Queue size: {self.data_queue.qsize()}")
                    
                    # Log telemetry data in proper format for future playback
                    if not self.playback_mode:  # Don't log playback data
                        telemetry_json = json.dumps(data)
                        logging.info(f"Telemetry: {telemetry_json}")
                
            except Exception as e:
                logging.error(f"❌ Error in data receiver thread: {e}")
                time.sleep(1)
    
    def generate_mock_data(self) -> Dict[str, Any]:
        """Generate realistic mock telemetry data"""
        return {
            'timestamp': datetime.now().isoformat(),
            'vehicle_speed': random.uniform(0, 120),
            'battery_voltage': random.uniform(350, 400),
            'battery_soc': random.uniform(20, 95),
            'min_cell_temp': random.uniform(20, 30),
            'max_cell_temp': random.uniform(30, 40),
            'inverter_temp': random.uniform(45, 75)
        }
    
    def fetch_api_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data from the API"""
        try:
            response = requests.get(API_URL, timeout=API_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            else:
                logging.warning(f"⚠️ API error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ API request failed: {e}")
            self.api_available = False
            self.mock_mode = True
            return None
    
    def get_data_from_queue(self, max_points: int = MAX_DATA_POINTS) -> List[Dict[str, Any]]:
        """Get all available data from the queue"""
        data_points = []
        try:
            while not self.data_queue.empty() and len(data_points) < max_points:
                data_points.append(self.data_queue.get_nowait())
        except queue.Empty:
            pass
        return data_points
    
    def load_log_file(self, log_file_path: str) -> bool:
        """Load telemetry data from log file for playback"""
        try:
            self.playback_data = []
            logging.info(f"Attempting to load log file: {log_file_path}")
            
            with open(log_file_path, 'r') as f:
                line_count = 0
                for line in f:
                    line_count += 1
                    # Extract JSON data from log lines
                    if 'Telemetry:' in line:
                        # Find the JSON part after "Telemetry: "
                        json_start = line.find('Telemetry: ') + len('Telemetry: ')
                        json_str = line[json_start:].strip()
                        try:
                            # Clean up common JSON issues
                            json_str = json_str.replace("'", '"')  # Replace single quotes with double quotes
                            if json_str.startswith('{') and json_str.endswith('}'):
                                data = json.loads(json_str)
                                # Validate that we have the required fields
                                required_fields = ['timestamp', 'vehicle_speed', 'battery_voltage', 'battery_soc']
                                if all(field in data for field in required_fields):
                                    self.playback_data.append(data)
                                else:
                                    logging.warning(f"⚠️ Line {line_count}: Missing required fields in data")
                        except json.JSONDecodeError as e:
                            logging.warning(f"⚠️ Line {line_count}: Invalid JSON - {e}")
                        except Exception as e:
                            logging.warning(f"⚠️ Line {line_count}: Error parsing data - {e}")
            
            logging.info(f"✅ Successfully loaded {len(self.playback_data)} data points from {log_file_path}")
            return len(self.playback_data) > 0
            
        except Exception as e:
            logging.error(f"❌ Error loading log file {log_file_path}: {e}")
            return False
    
    def start_playback(self, log_file_path: str) -> bool:
        """Start playback from a log file"""
        logging.info(f"Attempting to start playback of: {log_file_path}")
        
        if self.load_log_file(log_file_path):
            # Force playback mode - this overrides everything else
            logging.info("Log file loaded successfully, starting playback mode")
            self.playback_mode = True
            self.playback_index = 0
            self.playback_paused = False
            self.playback_file = log_file_path
            
            # Make sure the receiver is running
            if not self.running:
                self.start()
            
            logging.info(f"✅ PLAYBACK STARTED: {log_file_path} with {len(self.playback_data)} data points")
            logging.info(f"Playback mode: {self.playback_mode}, Mock mode: {self.mock_mode}")
            return True
        else:
            logging.error(f"❌ Failed to load log file: {log_file_path}")
            return False
    
    def pause_playback(self):
        """Pause playback"""
        if self.playback_mode:
            self.playback_paused = True
            logging.info("⏸️ Playback paused")
    
    def resume_playback(self):
        """Resume playback"""
        if self.playback_mode:
            self.playback_paused = False
            logging.info("▶️ Playback resumed")
    
    def stop_playback(self):
        """Stop playback and return to normal mode"""
        if self.playback_mode:
            logging.info("⏹️ Stopping playback, returning to normal mode")
            self.playback_mode = False
            self.playback_paused = False
            self.playback_index = 0
            self.playback_data = []
            self.playback_file = None
            
            # Restore previous mode
            if not self.api_available:
                self.mock_mode = True
                logging.info("🎲 Returned to mock mode")
            else:
                self.mock_mode = False
                logging.info("📡 Returned to API mode")