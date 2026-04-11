"""Dash application entry point for the Olist Customer Segmentation dashboard.

Exposes ``server = app.server`` for Gunicorn.  All pages are auto-discovered
from the ``pages/`` directory via ``use_pages=True``.

Usage (development):
    python dashboard/app.py

Usage (production via Gunicorn):
    gunicorn "dashboard.app:server" --bind 0.0.0.0:8080
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import html

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.BOOTSTRAP,
    ],
    title="Olist — Segmentation Client",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# ── Gunicorn hook ─────────────────────────────────────────────────────────────
server = app.server

# ── Navigation bar ────────────────────────────────────────────────────────────
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(
            dbc.NavLink(page["name"], href=page["relative_path"], active="exact")
        )
        for page in dash.page_registry.values()
    ],
    brand=html.Span(
        [html.I(className="bi bi-diagram-3 me-2"), "Olist Segmentation"]
    ),
    brand_href="/",
    color="dark",
    dark=True,
    fluid=True,
    className="mb-4 shadow-sm",
)

# ── Root layout ───────────────────────────────────────────────────────────────
app.layout = dbc.Container(
    [
        navbar,
        dash.page_container,
    ],
    fluid=True,
    className="px-4",
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
