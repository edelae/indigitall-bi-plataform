"""Unified Dashboard — Date selector callback."""

from datetime import date, timedelta

from dash import Input, Output, callback, ctx


@callback(
    Output("ud-date-store", "data"),
    Output("ud-date-picker", "style"),
    Output("ud-btn-7d", "active"),
    Output("ud-btn-30d", "active"),
    Output("ud-btn-90d", "active"),
    Output("ud-btn-custom", "active"),
    Input("ud-btn-7d", "n_clicks"),
    Input("ud-btn-30d", "n_clicks"),
    Input("ud-btn-90d", "n_clicks"),
    Input("ud-btn-custom", "n_clicks"),
    Input("ud-date-picker", "start_date"),
    Input("ud-date-picker", "end_date"),
)
def update_ud_date_range(_n7, _n30, _n90, _ncustom, picker_start, picker_end):
    triggered = ctx.triggered_id
    today = date.today()
    hide = {"display": "none"}
    show = {"display": "inline-block", "marginLeft": "12px"}

    if triggered == "ud-btn-7d":
        s = today - timedelta(days=6)
        return {"start": str(s), "end": str(today)}, hide, True, False, False, False
    if triggered == "ud-btn-90d":
        s = today - timedelta(days=89)
        return {"start": str(s), "end": str(today)}, hide, False, False, True, False
    if triggered == "ud-btn-custom":
        s = today - timedelta(days=29)
        return {"start": str(s), "end": str(today)}, show, False, False, False, True
    if triggered == "ud-date-picker" and picker_start and picker_end:
        return (
            {"start": str(picker_start)[:10], "end": str(picker_end)[:10]},
            show, False, False, False, True,
        )
    s = today - timedelta(days=29)
    return {"start": str(s), "end": str(today)}, hide, False, True, False, False
