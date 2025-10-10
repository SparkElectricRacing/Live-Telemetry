"""
Main entry point for the telemetry dashboard application
"""

import dash
import logging
import pathlib

from telemetry import TelemetryReceiver
from layout import create_dashboard_layout
from charts import register_chart_callbacks
from callbacks import register_all_callbacks
from summary_callbacks import register_summary_callbacks
from config import TEMPLATES_DIR


def create_app():
    """Create and configure the Dash application"""
    
    # Initialize telemetry receiver
    telemetry = TelemetryReceiver()
    
    # Initialize Dash app
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Live Telemetry"
    
    # Load custom HTML template
    template_path = TEMPLATES_DIR / "index.html"
    with open(template_path, 'r') as f:
        app.index_string = f.read()
    
    # Set layout
    app.layout = create_dashboard_layout()
    
    # Register all callbacks
    register_chart_callbacks(app, telemetry)
    register_all_callbacks(app, telemetry)
    register_summary_callbacks(app)

    return app, telemetry


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create app
    app, telemetry = create_app()
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8051)
    except KeyboardInterrupt:
        telemetry.stop()
        print("\nTelemetry dashboard stopped.")


if __name__ == '__main__':
    main()