"""SPIMquant explorer: the lightsheet region table, handed to a viewer.

No code required to use this app - pick the animals and brain regions you
care about, then sort and filter the table. Everything below is what makes
that possible.
"""

from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.dash_table.Format import Format, Scheme
from dash.exceptions import PreventUpdate

LOCAL_LIGHTSHEET_PATH = Path(__file__).parent / "seg-coarse_from-ABAv3_desc-gmm+n3k1_allsubjects.tsv"
FALLBACK_LIGHTSHEET_PATH = Path(
    "~/lightsheet/mouse_app_lecanemab_ki3_aggregated/derivatives/spimquant-v0.9.0/group/"
    "treatmenteffect_sexstratified_betterN4maskdropfailed/"
    "seg-coarse_from-ABAv3_desc-gmm+n3k1_allsubjects.tsv"
).expanduser()

MISSING_LABEL = "(not recorded)"


def load_lightsheet_data():
    if LOCAL_LIGHTSHEET_PATH.exists():
        print(f"Loading lightsheet data from local repo file: {LOCAL_LIGHTSHEET_PATH}")
        return pd.read_csv(LOCAL_LIGHTSHEET_PATH, sep="\t")
    if FALLBACK_LIGHTSHEET_PATH.exists():
        print(f"Local file not found. Loading lightsheet data from fallback path: {FALLBACK_LIGHTSHEET_PATH}")
        return pd.read_csv(FALLBACK_LIGHTSHEET_PATH, sep="\t")
    raise FileNotFoundError(
        "Could not find lightsheet data at either "
        f"{LOCAL_LIGHTSHEET_PATH} or {FALLBACK_LIGHTSHEET_PATH}"
    )


lightsheet_df = load_lightsheet_data()


def _options_for(column):
    values = sorted(lightsheet_df[column].dropna().unique())
    if lightsheet_df[column].isna().any():
        values.append(MISSING_LABEL)
    return values


def _mask_for(column, selected):
    if not selected:
        return pd.Series(False, index=lightsheet_df.index)
    mask = lightsheet_df[column].isin(selected)
    if MISSING_LABEL in selected:
        mask = mask | lightsheet_df[column].isna()
    return mask


def _table_columns():
    columns = []
    for column in lightsheet_df.columns:
        if pd.api.types.is_numeric_dtype(lightsheet_df[column]):
            columns.append(
                {
                    "name": column,
                    "id": column,
                    "type": "numeric",
                    "format": Format(precision=4, scheme=Scheme.decimal_or_exponent),
                }
            )
        else:
            columns.append({"name": column, "id": column, "type": "text"})
    return columns


sexes = _options_for("sex")
genotypes = _options_for("genotype")
treatments = _options_for("treatment")
regions = _options_for("name")

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "SPIMquant Dataset Explorer (Plotly/Dash Demo)"

app.layout = dbc.Container(
    [
        html.H1("SPIMquant Dataset Explorer (Plotly/Dash Demo)", className="mt-4"),
        html.P(
            "Every row is one brain region in one mouse, with the Abeta and "
            "Iba1 measurements for that region. Use the dropdowns to narrow "
            "down which animals and regions you are looking at, then sort "
            "and filter the table itself to go further.",
            className="text-muted",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Sex"),
                        dcc.Dropdown(
                            id="sex-dropdown",
                            options=[{"label": s, "value": s} for s in sexes],
                            value=sexes,
                            multi=True,
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label("Genotype"),
                        dcc.Dropdown(
                            id="genotype-dropdown",
                            options=[{"label": g, "value": g} for g in genotypes],
                            value=genotypes,
                            multi=True,
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label("Treatment"),
                        dcc.Dropdown(
                            id="treatment-dropdown",
                            options=[{"label": t, "value": t} for t in treatments],
                            value=treatments,
                            multi=True,
                        ),
                    ],
                    md=4,
                ),
            ],
            className="mb-2",
        ),
        html.Small(
            "These three describe the animal. The wild-type controls have no "
            "treatment recorded - keep \"(not recorded)\" selected to see them.",
            className="text-muted d-block mb-3",
        ),
        dbc.Row(
            dbc.Col(
                [
                    html.Label("Brain region"),
                    dcc.Dropdown(
                        id="region-dropdown",
                        options=[{"label": r, "value": r} for r in regions],
                        value=regions,
                        multi=True,
                    ),
                    html.Small(
                        "Regions are split into left (L_) and right (R_) sides. "
                        "\"Unknown_Label_0\" is the whole-image background record "
                        "rather than a real region.",
                        className="text-muted",
                    ),
                ]
            ),
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(html.H4("Region measurements", className="mt-2"), width="auto"),
                dbc.Col(
                    dbc.Button(
                        "⬇ Download CSV",
                        id="download-button",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="mt-2",
                    ),
                    width="auto",
                    className="ms-auto",
                ),
            ],
            className="align-items-center",
        ),
        html.P(id="row-count", className="text-muted small mb-1"),
        html.P(
            "Click a column header to sort, or type into the row beneath the "
            "headers to filter - for example, a region name under \"name\", or "
            "\">10\" under \"Abeta+density\". Scroll sideways to reach every "
            "column. Use the button above to save the rows you're currently "
            "viewing as a CSV file.",
            className="text-muted small",
        ),
        dcc.Download(id="download-dataframe-csv"),
        dash_table.DataTable(
            id="spimquant-table",
            columns=_table_columns(),
            sort_action="native",
            filter_action="native",
            page_size=15,
            style_table={"overflowX": "auto"},
            style_cell={
                "minWidth": "90px",
                "maxWidth": "220px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "textAlign": "left",
            },
        ),
    ],
    className="pb-5",
)


@app.callback(
    Output("spimquant-table", "data"),
    Output("row-count", "children"),
    Input("sex-dropdown", "value"),
    Input("genotype-dropdown", "value"),
    Input("treatment-dropdown", "value"),
    Input("region-dropdown", "value"),
)
def update_table(selected_sexes, selected_genotypes, selected_treatments, selected_regions):
    mask = (
        _mask_for("sex", selected_sexes)
        & _mask_for("genotype", selected_genotypes)
        & _mask_for("treatment", selected_treatments)
        & _mask_for("name", selected_regions)
    )
    filtered = lightsheet_df[mask]
    count = f"Showing {len(filtered)} of {len(lightsheet_df)} rows"
    return filtered.to_dict("records"), count


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("download-button", "n_clicks"),
    State("spimquant-table", "derived_virtual_data"),
)
def download_csv(n_clicks, table_data):
    if not n_clicks:
        raise PreventUpdate
    export_df = pd.DataFrame(table_data)
    return dcc.send_data_frame(export_df.to_csv, "spimquant_filtered.csv", index=False)


if __name__ == "__main__":
    app.run(debug=True)
