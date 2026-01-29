"""Dash callbacks for interactive functionality."""

from dash import Input, Output, State, callback, html, MATCH, ALL, ctx
import plotly.graph_objects as go
import plotly.express as px
import dash_mantine_components as dmc
import pandas as pd
from pathlib import Path

from src.data_loader import get_image_dataframe, generate_random_features
from src.umap_processor import compute_umap_embedding, create_umap_dataframe


def register_callbacks(app, df_original, cache):
    """
    Register all callbacks for the application.

    Args:
        app: Dash application instance
        df_original: Original dataframe with all data
        cache: Flask-Cache instance
    """

    @app.callback(
        [
            Output("umap-plot", "figure"),
            Output("data-store", "data"),
            Output("features-store", "data"),
            Output("stats-display", "children"),
        ],
        [
            Input("patch-dropdown", "value"),
            Input("coord-dropdown", "value"),
        ],
        background=True,
    )
    def update_umap_and_data(patch_type, coordinate):
        """Update UMAP plot and store filtered data."""
        if not patch_type or coordinate is None:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="Select patch type and coordinate",
                xaxis_title="UMAP 1",
                yaxis_title="UMAP 2",
            )
            return empty_fig, None, None, "No data selected"

        coordinate = int(coordinate)
        filtered_df = get_image_dataframe(df_original, patch_type, coordinate)

        if len(filtered_df) == 0:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="No data available",
                xaxis_title="UMAP 1",
                yaxis_title="UMAP 2",
            )
            return empty_fig, None, None, "No images found"

        cache_key = f"umap_{patch_type}_{coordinate}"

        @cache.memoize(timeout=3600)
        def get_cached_umap(key, df_subset):
            features, clusters = generate_random_features(df_subset)
            embedding = compute_umap_embedding(features)
            return embedding, clusters

        embedding, clusters = get_cached_umap(cache_key, filtered_df)
        umap_df = create_umap_dataframe(filtered_df, embedding, clusters)

        fig = px.scatter(
            umap_df,
            x="umap_x",
            y="umap_y",
            color="cluster",
            hover_data=["czi_filename", "pos", "date", "time_period"],
            title=f"UMAP: {patch_type} (position {coordinate})",
            color_discrete_sequence=px.colors.qualitative.Plotly,
            custom_data=["czi_filename", "cluster", "date", "time_period"],
        )

        fig.update_traces(
            marker=dict(size=10, opacity=0.7, line=dict(width=1, color='white')),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Cluster: %{customdata[1]}<br>"
                "Date: %{customdata[2]}<br>"
                "Time: %{customdata[3]}<br>"
                "UMAP X: %{x:.2f}<br>"
                "UMAP Y: %{y:.2f}<br>"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            clickmode="event+select",
            dragmode="lasso",
            hovermode="closest",
            height=500,
            margin=dict(l=20, r=20, t=40, b=20),
        )

        n_clusters = len(umap_df['cluster'].unique())
        dates = umap_df['date'].unique()
        time_periods = umap_df['time_period'].unique()

        stats_display = dmc.Stack(
            gap="sm",
            children=[
                dmc.Group(
                    gap="xs",
                    children=[
                        dmc.ThemeIcon(size="lg", radius="md", variant="light", color="blue", children="📊"),
                        dmc.Stack(
                            gap=0,
                            children=[
                                dmc.Text(str(len(filtered_df)), fw=700, size="xl", c="blue"),
                                dmc.Text("Total Images", size="xs", c="dimmed"),
                            ]
                        ),
                    ]
                ),
                dmc.Divider(),
                dmc.Group(
                    gap="xs",
                    children=[
                        dmc.ThemeIcon(size="lg", radius="md", variant="light", color="grape", children="🎨"),
                        dmc.Stack(
                            gap=0,
                            children=[
                                dmc.Text(str(n_clusters), fw=700, size="xl", c="grape"),
                                dmc.Text("Clusters", size="xs", c="dimmed"),
                            ]
                        ),
                    ]
                ),
                dmc.Divider(),
                dmc.Group(
                    gap="xs",
                    children=[
                        dmc.ThemeIcon(size="lg", radius="md", variant="light", color="teal", children="📅"),
                        dmc.Stack(
                            gap=0,
                            children=[
                                dmc.Text(str(len(dates)), fw=700, size="xl", c="teal"),
                                dmc.Text("Unique Dates", size="xs", c="dimmed"),
                            ]
                        ),
                    ]
                ),
                dmc.Divider(),
                dmc.Stack(
                    gap="xs",
                    children=[
                        dmc.Text("Time Periods:", fw=500, size="sm"),
                        dmc.Group(
                            gap="xs",
                            children=[
                                dmc.Badge(tp, size="sm", variant="light") for tp in time_periods if tp != 'N/A'
                            ]
                        ),
                    ]
                ) if len([tp for tp in time_periods if tp != 'N/A']) > 0 else None,
            ]
        )

        return fig, umap_df.to_dict("records"), None, stats_display

    @app.callback(
        [
            Output("image-grid", "children"),
            Output("data-table", "rowData"),
            Output("data-table", "columnDefs"),
        ],
        [
            Input("umap-plot", "selectedData"),
            Input("umap-plot", "clickData"),
            Input("reset-selection-btn", "n_clicks"),
            Input("data-store", "data"),
        ]
    )
    def update_images_and_table(selected_data, click_data, reset_clicks, stored_data):
        """Update image grid and data table based on selection."""
        if not stored_data:
            return html.Div("No data available"), [], []

        df = pd.DataFrame(stored_data)
        selected_indices = []

        triggered_id = ctx.triggered_id

        if triggered_id == "reset-selection-btn":
            selected_df = df.head(20)
        else:
            if selected_data and "points" in selected_data:
                selected_indices = [p["pointIndex"] for p in selected_data["points"]]
            elif click_data and "points" in click_data:
                selected_indices = [click_data["points"][0]["pointIndex"]]

            if selected_indices:
                selected_df = df.iloc[selected_indices]
            else:
                selected_df = df.head(20)

        image_grid = create_image_grid(selected_df)

        column_defs = [
            {"field": "czi_filename", "headerName": "Filename", "flex": 2},
            {"field": "pos", "headerName": "Position", "flex": 1},
            {"field": "date", "headerName": "Date", "flex": 1},
            {"field": "time_period", "headerName": "Time", "flex": 1},
            {"field": "cluster", "headerName": "Cluster", "flex": 1},
            {"field": "umap_x", "headerName": "UMAP X", "flex": 1, "valueFormatter": {"function": "d3.format('.2f')(params.value)"}},
            {"field": "umap_y", "headerName": "UMAP Y", "flex": 1, "valueFormatter": {"function": "d3.format('.2f')(params.value)"}},
        ]

        table_data = selected_df[["czi_filename", "pos", "date", "time_period", "cluster", "umap_x", "umap_y"]].to_dict("records")

        return image_grid, table_data, column_defs

    @app.callback(
        [
            Output("image-modal", "opened"),
            Output("modal-image", "src"),
        ],
        [Input({"type": "image-thumb", "index": ALL}, "n_clicks")],
        [
            State({"type": "image-thumb", "index": ALL}, "id"),
            State("image-modal", "opened"),
        ],
        prevent_initial_call=True,
    )
    def toggle_modal(n_clicks_list, id_list, is_open):
        """Toggle fullscreen image modal."""
        if not any(n_clicks_list):
            return False, ""

        clicked_idx = next((i for i, clicks in enumerate(n_clicks_list) if clicks), None)

        if clicked_idx is not None:
            image_path = id_list[clicked_idx]["index"]
            return True, f"/images/{image_path}"

        return False, ""


def create_image_grid(df: pd.DataFrame) -> html.Div:
    """
    Create a grid of image thumbnails.

    Args:
        df: DataFrame with image_path column

    Returns:
        Div containing image grid
    """
    if len(df) == 0:
        return html.Div("No images selected. Click or select points on the UMAP plot.")

    images = []
    for idx, row in df.iterrows():
        if "image_path" in row and pd.notna(row["image_path"]):
            rel_path = Path(row["image_path"]).relative_to(Path("data").absolute())

            image_card = dmc.Card(
                children=[
                    html.Img(
                        id={"type": "image-thumb", "index": str(rel_path)},
                        src=f"/images/{rel_path}",
                        style={
                            "width": "150px",
                            "height": "150px",
                            "objectFit": "cover",
                            "cursor": "pointer",
                            "borderRadius": "4px",
                        },
                    ),
                ],
                p="xs",
                withBorder=True,
                radius="md",
            )

            images.append(image_card)

    return dmc.SimpleGrid(
        cols=4,
        spacing="sm",
        verticalSpacing="sm",
        children=images,
    )
