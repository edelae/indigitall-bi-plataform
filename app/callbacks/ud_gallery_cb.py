"""Unified Dashboard — Gallery ⟷ Dashboard toggle callback."""

from dash import Input, Output, callback, ctx


@callback(
    Output("ud-gallery", "style"),
    Output("ud-dashboard", "style"),
    Input("ud-gallery-card-visionamos", "n_clicks"),
    Input("ud-back-to-gallery", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_gallery_dashboard(card_clicks, back_clicks):
    if ctx.triggered_id == "ud-gallery-card-visionamos":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}
