"""Dash layout with DMC components."""

import dash_mantine_components as dmc
from dash import dcc, html
import dash_ag_grid as dag
from dash_extensions import WebSocket


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
        children=[
            # Notification container for live updates (DMC 2.0+)
            dmc.NotificationContainer(
                id="notification-container",
                position="top-right",
                zIndex=2000,
            ),
            dmc.Container(
            fluid=True,
            p="md",
            children=[
                dmc.Paper(
                    children=[
                        dmc.Group(
                            justify="space-between",
                            align="center",
                            children=[
                                dmc.Group(
                                    gap="md",
                                    children=[
                                        dmc.ThemeIcon(
                                            children="🔬",
                                            size=50,
                                            radius="md",
                                            variant="gradient",
                                            gradient={"from": "blue", "to": "cyan", "deg": 45},
                                        ),
                                        dmc.Stack(
                                            gap=0,
                                            children=[
                                                dmc.Title("UMAP Image Explorer", order=2, c="blue"),
                                                dmc.Text(
                                                    "Real-time exploration of high-dimensional image data",
                                                    size="sm",
                                                    c="dimmed",
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                                # Live status indicator and freeze toggle
                                dmc.Group(
                                    gap="md",
                                    children=[
                                        html.Div(
                                            id="live-indicator-wrapper",
                                            className="live-indicator-pulse",
                                            children=dmc.Badge(
                                                id="live-indicator",
                                                children="● Live",
                                                color="green",
                                                variant="filled",
                                                size="lg",
                                                radius="xl",
                                            ),
                                        ),
                                        dmc.Switch(
                                            id="freeze-toggle",
                                            label="Pause Updates",
                                            size="md",
                                            color="red",
                                            checked=False,
                                            thumbIcon=html.Span("⏸", style={"fontSize": "10px"}),
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                    p="lg",
                    mb="md",
                    withBorder=True,
                    shadow="md",
                    radius="lg",
                    style={"background": "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)"},
                ),

                dmc.Grid(
                    children=[
                        # Left Panel
                        dmc.GridCol(
                            span=3,
                            children=[
                                dmc.Stack(
                                    gap="md",
                                    children=[
                                        # Filters Card
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

                                        # Statistics Card
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

                                        # Event Log Card - NEW
                                        dmc.Card(
                                            children=[
                                                dmc.Group(
                                                    justify="space-between",
                                                    mb="sm",
                                                    children=[
                                                        dmc.Title("Event Log", order=3),
                                                        dmc.Badge(
                                                            id="event-count-badge",
                                                            children="0",
                                                            color="blue",
                                                            variant="filled",
                                                            size="sm",
                                                        ),
                                                    ]
                                                ),
                                                dmc.ScrollArea(
                                                    h=400,
                                                    children=dmc.Stack(
                                                        id="event-log-container",
                                                        gap="xs",
                                                        children=[
                                                            dmc.Text(
                                                                "Waiting for events...",
                                                                size="sm",
                                                                c="dimmed",
                                                                fs="italic",
                                                            )
                                                        ],
                                                    ),
                                                ),
                                            ],
                                            withBorder=True,
                                            shadow="sm",
                                            radius="md",
                                            p="md",
                                            h="500px",
                                        ),
                                    ]
                                )
                            ]
                        ),

                        # Right Panel
                        dmc.GridCol(
                            span=9,
                            children=[
                                dmc.Stack(
                                    gap="md",
                                    children=[
                                        # UMAP and Images Row
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
                                                                        dmc.Group(
                                                                            gap="xs",
                                                                            children=[
                                                                                # Pending update badge (hidden when no updates)
                                                                                dmc.Badge(
                                                                                    id="pending-badge",
                                                                                    children="New data!",
                                                                                    color="red",
                                                                                    variant="filled",
                                                                                    size="sm",
                                                                                    style={"display": "none"},
                                                                                ),
                                                                                # Update button
                                                                                dmc.Button(
                                                                                    "Update UMAP",
                                                                                    id="update-umap-btn",
                                                                                    variant="filled",
                                                                                    color="green",
                                                                                    size="xs",
                                                                                    leftSection=dmc.Text("↻", size="sm"),
                                                                                ),
                                                                                dmc.Button(
                                                                                    "Reset",
                                                                                    id="reset-selection-btn",
                                                                                    variant="light",
                                                                                    color="red",
                                                                                    size="xs",
                                                                                ),
                                                                            ]
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

                                        # Time Series Visualization Card (Auto-updates)
                                        dmc.Card(
                                            children=[
                                                dmc.Group(
                                                    justify="space-between",
                                                    mb="sm",
                                                    children=[
                                                        dmc.Group(
                                                            gap="xs",
                                                            children=[
                                                                dmc.Title("Object Count Over Time", order=4),
                                                                dmc.Badge(
                                                                    "LIVE",
                                                                    color="green",
                                                                    variant="dot",
                                                                    size="sm",
                                                                ),
                                                            ]
                                                        ),
                                                        dmc.Badge(
                                                            id="time-filter-badge",
                                                            children="All data",
                                                            color="blue",
                                                            variant="light",
                                                        ),
                                                    ]
                                                ),
                                                dcc.Graph(
                                                    id="timeseries-plot",
                                                    style={"height": "350px"},
                                                    config={
                                                        "displayModeBar": True,
                                                        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                                                    },
                                                    # Enable smooth transitions
                                                    animate=True,
                                                ),
                                            ],
                                            withBorder=True,
                                            shadow="sm",
                                            radius="md",
                                            p="md",
                                        ),

                                        # Data Table Card (Auto-updates)
                                        dmc.Card(
                                            children=[
                                                dmc.Group(
                                                    justify="space-between",
                                                    mb="sm",
                                                    children=[
                                                        dmc.Group(
                                                            gap="xs",
                                                            children=[
                                                                dmc.Title("Data Table", order=4),
                                                                dmc.Badge(
                                                                    "LIVE",
                                                                    color="green",
                                                                    variant="dot",
                                                                    size="sm",
                                                                ),
                                                            ]
                                                        ),
                                                        dmc.Text(
                                                            id="table-row-count",
                                                            size="sm",
                                                            c="dimmed",
                                                        ),
                                                    ]
                                                ),
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
                                                        "rowClassRules": {
                                                            "new-row-highlight": "params.data._is_new",
                                                        },
                                                    },
                                                    getRowId="params.data._row_id",
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

                # Stores
                dcc.Store(id="data-store"),
                dcc.Store(id="features-store"),
                dcc.Store(id="timeseries-store"),
                dcc.Store(id="ws-message-store"),
                dcc.Store(id="event-log-store", data=[]),
                dcc.Store(id="pending-update-store", data=False),
                dcc.Store(id="new-rows-store", data=[]),  # Track newly added row IDs
                dcc.Store(id="known-rows-store", data=[]),  # Track all known row IDs

                # Location for WebSocket URL
                dcc.Location(id="url-location", refresh=False),

                # WebSocket
                WebSocket(id="ws", url=""),

                # Image Modal
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
        ),
        ]
    )
