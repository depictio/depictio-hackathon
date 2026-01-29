"""Dash layout with DMC components."""

import dash_mantine_components as dmc
from dash import dcc, html
import dash_ag_grid as dag


def create_layout(patch_types: list, coordinates: list):
    """
    Create the main application layout.

    Args:
        patch_types: List of patch type options
        coordinates: List of coordinate options

    Returns:
        Dash layout component
    """
    return dmc.MantineProvider(
        children=dmc.Container(
            fluid=True,
            p="md",
            children=[
                dmc.Paper(
                    children=[
                        dmc.Group(
                            justify="space-between",
                            align="center",
                            children=[
                                dmc.Stack(
                                    gap="xs",
                                    children=[
                                        dmc.Title("UMAP Image Explorer", order=1, c="blue"),
                                        dmc.Text(
                                            "Interactive exploration of high-dimensional image data",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                    p="lg",
                    mb="md",
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                ),

                dmc.Grid(
                    children=[
                        dmc.GridCol(
                            span=3,
                            children=[
                                dmc.Stack(
                                    gap="md",
                                    children=[
                                        dmc.Card(
                                            children=[
                                                dmc.Title("Filters", order=3, mb="sm"),

                                                dmc.Select(
                                                    id="patch-dropdown",
                                                    label="Patch Type",
                                                    placeholder="Select patch type",
                                                    data=[{"label": pt, "value": pt} for pt in patch_types],
                                                    value=patch_types[0] if patch_types else None,
                                                    mb="sm",
                                                ),

                                                dmc.Select(
                                                    id="coord-dropdown",
                                                    label="Coordinate Position",
                                                    placeholder="Select coordinate",
                                                    data=[{"label": str(c), "value": str(c)} for c in coordinates],
                                                    value=str(coordinates[0]) if coordinates else None,
                                                ),
                                            ],
                                            withBorder=True,
                                            shadow="sm",
                                            radius="md",
                                            p="md",
                                        ),

                                        dmc.Card(
                                            id="stats-card",
                                            children=[
                                                dmc.Title("Statistics", order=3, mb="md"),
                                                html.Div(id="stats-display", children="Loading..."),
                                            ],
                                            withBorder=True,
                                            shadow="sm",
                                            radius="md",
                                            p="md",
                                        ),
                                    ]
                                )
                            ]
                        ),

                        dmc.GridCol(
                            span=9,
                            children=[
                                dmc.Stack(
                                    gap="md",
                                    children=[
                                        dmc.Grid(
                                            children=[
                                                dmc.GridCol(
                                                    span=6,
                                                    children=[
                                                        dmc.Card(
                                                            children=[
                                                                dmc.Group(
                                                                    justify="space-between",
                                                                    mb="sm",
                                                                    children=[
                                                                        dmc.Title("UMAP Projection", order=4),
                                                                        dmc.Button(
                                                                            "Reset Selection",
                                                                            id="reset-selection-btn",
                                                                            variant="light",
                                                                            color="red",
                                                                            size="xs",
                                                                        ),
                                                                    ]
                                                                ),
                                                                dcc.Loading(
                                                                    id="loading-umap",
                                                                    type="default",
                                                                    children=dcc.Graph(
                                                                        id="umap-plot",
                                                                        style={"height": "500px"},
                                                                        config={"displayModeBar": True}
                                                                    ),
                                                                ),
                                                            ],
                                                            withBorder=True,
                                                            shadow="sm",
                                                            radius="md",
                                                            p="md",
                                                        )
                                                    ]
                                                ),

                                                dmc.GridCol(
                                                    span=6,
                                                    children=[
                                                        dmc.Card(
                                                            children=[
                                                                dmc.Title("Selected Images", order=4, mb="sm"),
                                                                dcc.Loading(
                                                                    id="loading-images",
                                                                    type="default",
                                                                    children=html.Div(
                                                                        id="image-grid-container",
                                                                        children=html.Div(
                                                                            id="image-grid",
                                                                            style={
                                                                                "height": "500px",
                                                                                "overflowY": "auto",
                                                                            }
                                                                        )
                                                                    ),
                                                                ),
                                                            ],
                                                            withBorder=True,
                                                            shadow="sm",
                                                            radius="md",
                                                            p="md",
                                                        )
                                                    ]
                                                ),
                                            ]
                                        ),

                                        dmc.Card(
                                            children=[
                                                dmc.Title("Data Table", order=4, mb="sm"),
                                                dag.AgGrid(
                                                    id="data-table",
                                                    columnSize="sizeToFit",
                                                    defaultColDef={
                                                        "resizable": True,
                                                        "sortable": True,
                                                        "filter": True,
                                                    },
                                                    dashGridOptions={
                                                        "pagination": True,
                                                        "paginationPageSize": 10,
                                                        "animateRows": True,
                                                    },
                                                    style={"height": "400px"},
                                                ),
                                            ],
                                            withBorder=True,
                                            shadow="sm",
                                            radius="md",
                                            p="md",
                                        ),
                                    ]
                                )
                            ]
                        ),
                    ]
                ),

                dcc.Store(id="data-store"),
                dcc.Store(id="features-store"),

                dmc.Modal(
                    id="image-modal",
                    size="xl",
                    children=[
                        html.Img(
                            id="modal-image",
                            style={"width": "100%", "height": "auto"}
                        )
                    ],
                ),
            ]
        )
    )
