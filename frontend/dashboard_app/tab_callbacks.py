from dash import Input, Output, html
from tabs import tab_dashboard, tab_analysis

# sets up the tab functionality in the app
def register_tab_callbacks(app):
    @app.callback(
        Output("tabs-content", "children"),
        Input("tabs", "value")
    )
    def render_tab(tab_name):
        if tab_name == "dashboard":
            return tab_dashboard.layout()
        elif tab_name == "analysis":
            return tab_analysis.layout()
        return html.Div("404: Tab not found")