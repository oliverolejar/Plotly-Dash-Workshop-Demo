"""SPIMquant explorer: the lightsheet region table, handed to a viewer.

No code required to use this app - pick the animals and brain regions you
care about, then sort and filter the table. Everything below is what makes
that possible.
"""

from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

BACKGROUND_REGION = "Unknown_Label_0"
STAINS = ["Abeta", "Iba1"]
SPLIT_COLUMNS = ["sex", "genotype", "batch_id"]
TREATMENT_ORDER = ["PBS", "Lecanemab", "N control", "P control", MISSING_LABEL]
METRIC_ORDER = [
    "Total count",
    "Total burden (nvoxels)",
    "Density (count/mm3)",
    "Field fraction (%)",
]


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


def _filtered_df(selected_sexes, selected_genotypes, selected_treatments, selected_regions):
    mask = (
        _mask_for("sex", selected_sexes)
        & _mask_for("genotype", selected_genotypes)
        & _mask_for("treatment", selected_treatments)
        & _mask_for("name", selected_regions)
    )
    return lightsheet_df[mask]


def _subject_summary(filtered, stain):
    regions = filtered[filtered["name"] != BACKGROUND_REGION]
    if regions.empty:
        return regions, 0

    count = regions[f"{stain}+count"]
    volume = regions[f"{stain}+volume"]
    weighted = regions[f"{stain}+fieldfrac"] * volume
    working = regions.assign(_count=count, _volume=volume, _weighted=weighted)

    grouped = working.groupby("participant_id", as_index=False).agg(
        participant_label=("participant_label", "first"),
        treatment=("treatment", "first"),
        sex=("sex", "first"),
        genotype=("genotype", "first"),
        batch_id=("batch_id", "first"),
        total_count=("_count", "sum"),
        total_nvoxels=(f"{stain}+nvoxels", "sum"),
        total_volume=("_volume", "sum"),
        weighted_fieldfrac=("_weighted", "sum"),
    )
    summary = grouped.assign(
        **{
            "Total count": grouped["total_count"],
            "Total burden (nvoxels)": grouped["total_nvoxels"],
            # density is exactly count/volume per region, so it recomputes cleanly at
            # whole-brain scale; fieldfrac is independent, so it needs volume weighting.
            "Density (count/mm3)": grouped["total_count"] / grouped["total_volume"],
            "Field fraction (%)": grouped["weighted_fieldfrac"] / grouped["total_volume"],
        }
    )
    summary["treatment"] = summary["treatment"].fillna(MISSING_LABEL)
    return summary, regions["name"].nunique()


def _facet_labels_to_yaxis_titles(figure):
    suffixes = {trace.yaxis[1:] for trace in figure.data}
    kept = []
    for annotation in figure.layout.annotations:
        if not annotation.text.startswith("metric="):
            kept.append(annotation)
            continue
        # px anchors facet labels to "paper" rather than to the panel's axes, so find the
        # owning panel by position: the label sits centered on its x domain, at its y top.
        for suffix in suffixes:
            x_domain = figure.layout[f"xaxis{suffix}"].domain
            y_domain = figure.layout[f"yaxis{suffix}"].domain
            if x_domain[0] <= annotation.x <= x_domain[1] and abs(y_domain[1] - annotation.y) < 1e-6:
                figure.layout[f"yaxis{suffix}"].title.text = annotation.text.split("=", 1)[1]
                break
    figure.layout.annotations = kept


def _placeholder_figure(text):
    figure = go.Figure()
    figure.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{"text": text, "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 16}}],
    )
    return figure


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
        html.H4("Treatment effect per mouse", className="mt-5"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Stain"),
                        dcc.Dropdown(
                            id="stain-dropdown",
                            options=[{"label": s, "value": s} for s in STAINS],
                            value="Abeta",
                            clearable=False,
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Label("Compare by"),
                        dcc.Dropdown(
                            id="split-dropdown",
                            options=[{"label": s, "value": s} for s in SPLIT_COLUMNS],
                            value="genotype",
                            clearable=False,
                        ),
                    ],
                    md=6,
                ),
            ],
            className="mb-2",
        ),
        html.Small(
            "Each point is one mouse, summarised across the brain regions you have "
            "selected above - the whole-image background record is always left out. "
            "Note that \"N control\" and \"P control\" are a single animal each, so "
            "their box is just that one point.",
            className="text-muted d-block mb-2",
        ),
        dcc.Graph(id="group-box-plot"),
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
    filtered = _filtered_df(selected_sexes, selected_genotypes, selected_treatments, selected_regions)
    count = f"Showing {len(filtered)} of {len(lightsheet_df)} rows"
    return filtered.to_dict("records"), count


@app.callback(
    Output("group-box-plot", "figure"),
    Input("sex-dropdown", "value"),
    Input("genotype-dropdown", "value"),
    Input("treatment-dropdown", "value"),
    Input("region-dropdown", "value"),
    Input("stain-dropdown", "value"),
    Input("split-dropdown", "value"),
)
def update_box_plot(
    selected_sexes, selected_genotypes, selected_treatments, selected_regions, stain, split
):
    filtered = _filtered_df(selected_sexes, selected_genotypes, selected_treatments, selected_regions)
    summary, region_count = _subject_summary(filtered, stain)
    if summary.empty:
        return _placeholder_figure("No brain regions match the current filters.")

    # batch_id is an int, which Plotly would render as a continuous colorbar instead of
    # discrete groups; the cast also keeps mice with a blank split value in the legend.
    summary[split] = summary[split].fillna(MISSING_LABEL).astype(str)
    long_df = summary.melt(
        id_vars=["participant_label", "treatment", split],
        value_vars=METRIC_ORDER,
        var_name="metric",
        value_name="value",
    )

    figure = px.box(
        long_df,
        x="treatment",
        y="value",
        color=split,
        points="all",
        facet_col="metric",
        facet_col_wrap=2,
        # room for each panel's own y-axis title and tick labels between the columns
        facet_col_spacing=0.1,
        hover_data=["participant_label"],
        category_orders={
            "treatment": [t for t in TREATMENT_ORDER if t in set(summary["treatment"])],
            "metric": METRIC_ORDER,
        },
        title=f"{stain} burden per mouse - {region_count} regions, {len(summary)} mice",
    )
    # px facets share one y axis by default, which would flatten counts (~1e3) against
    # nvoxels (~1e7); each metric needs its own scale.
    figure.update_yaxes(matches=None, showticklabels=True)
    # these are y-axis quantities with units, so label the axis rather than the panel
    _facet_labels_to_yaxis_titles(figure)
    figure.update_xaxes(title_text="")
    figure.update_layout(height=700, boxmode="group")
    return figure


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
