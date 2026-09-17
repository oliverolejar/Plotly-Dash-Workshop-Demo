"""Gapminder explorer: the notebook's animated bubble chart, handed to a viewer.

No code required to use this app - pick continents, drag the year slider,
sort/filter the table. Everything below is what makes that possible.
"""

import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate

df = px.data.gapminder()
continents = sorted(df["continent"].unique())
years = sorted(df["year"].unique())

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Gapminder Explorer"

app.layout = dbc.Container(
    [
        html.H1("Gapminder Explorer", className="mt-4"),
        html.P(
            "Pick continents and a year below - the chart and table update "
            "live. No code, no formulas, just clicking.",
            className="text-muted",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Continents"),
                        dcc.Dropdown(
                            id="continent-dropdown",
                            options=[{"label": c, "value": c} for c in continents],
                            value=continents,
                            multi=True,
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Label("Year"),
                        dcc.Slider(
                            id="year-slider",
                            min=years[0],
                            max=years[-1],
                            value=years[-1],
                            step=None,
                            marks={str(y): str(y) for y in years},
                        ),
                        dbc.Button(
                            "▶ Play",
                            id="play-button",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="mt-2",
                        ),
                        dcc.Interval(id="year-interval", interval=800, disabled=True),
                    ],
                    md=6,
                ),
            ],
            className="mb-4",
        ),
        dcc.Graph(id="gapminder-graph"),
        html.H4("Underlying data", className="mt-4"),
        dash_table.DataTable(
            id="gapminder-table",
            columns=[
                {"name": col, "id": col}
                for col in ["country", "continent", "year", "lifeExp", "gdpPercap", "pop"]
            ],
            sort_action="native",
            filter_action="native",
            page_size=10,
            style_table={"overflowX": "auto"},
        ),
    ],
    className="pb-5",
)


@app.callback(
    Output("year-interval", "disabled"),
    Output("play-button", "children"),
    Input("play-button", "n_clicks"),
    State("year-interval", "disabled"),
)
def toggle_play(n_clicks, is_disabled):
    if not n_clicks:
        raise PreventUpdate
    if is_disabled:
        return False, "⏸ Pause"
    return True, "▶ Play"


@app.callback(
    Output("year-slider", "value"),
    Input("year-interval", "n_intervals"),
    State("year-slider", "value"),
)
def advance_year(n_intervals, current_year):
    if not n_intervals:
        raise PreventUpdate
    next_index = (years.index(current_year) + 1) % len(years)
    return years[next_index]


@app.callback(
    Output("gapminder-graph", "figure"),
    Output("gapminder-table", "data"),
    Input("continent-dropdown", "value"),
    Input("year-slider", "value"),
)
def update_view(selected_continents, selected_year):
    filtered = df[df["continent"].isin(selected_continents) & (df["year"] == selected_year)]

    figure = px.scatter(
        filtered,
        x="gdpPercap",
        y="lifeExp",
        size="pop",
        color="continent",
        hover_name="country",
        log_x=True,
        size_max=60,
        range_x=[df["gdpPercap"].min(), df["gdpPercap"].max()],
        range_y=[df["lifeExp"].min(), df["lifeExp"].max()],
        title=f"Life expectancy vs. GDP per capita - {selected_year}",
    )

    columns = ["country", "continent", "year", "lifeExp", "gdpPercap", "pop"]
    return figure, filtered[columns].to_dict("records")


if __name__ == "__main__":
    app.run(debug=True)
