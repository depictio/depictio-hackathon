"""Dash callbacks for interactive functionality."""

import json
from datetime import datetime
from dash import Input, Output, State, callback, html, MATCH, ALL, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import plotly.express as px
import dash_mantine_components as dmc
import pandas as pd
from pathlib import Path

from src.data_loader import get_image_dataframe, generate_random_features, load_phenobase_data
from src.umap_processor import compute_umap_embedding, create_umap_dataframe


def register_callbacks(app, df_original, cache):
    """
    Register all callbacks for the application.

    Args:
        app: Dash application instance
        df_original: Original dataframe with all data
        cache: Flask-Cache instance
    """

    # =========================================================================
    # WebSocket URL Setup
    # =========================================================================
    app.clientside_callback(
        """
        function(pathname) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = protocol + '//' + host + '/ws';
            console.log('[WebSocket] Connecting to:', wsUrl);
            return wsUrl;
        }
        """,
        Output("ws", "url"),
        Input("url-location", "pathname"),
    )

    # =========================================================================
    # WebSocket Message Handler
    # =========================================================================
    app.clientside_callback(
        """
        function(msg) {
            if (!msg) return window.dash_clientside.no_update;
            console.log('[WebSocket] Received message:', msg);
            try {
                const data = JSON.parse(msg.data);
                console.log('[WebSocket] Parsed data:', data);
                if (data.type === 'new_image') {
                    return {
                        count: data.count,
                        total: data.total,
                        timestamp: Date.now(),
                        images: data.images || []
                    };
                }
            } catch(e) {
                console.error('WebSocket parse error:', e);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("ws-message-store", "data"),
        Input("ws", "message"),
    )

    # =========================================================================
    # Freeze Toggle - Update Live Indicator
    # =========================================================================
    @app.callback(
        Output("live-indicator", "children"),
        Output("live-indicator", "color"),
        Input("freeze-toggle", "checked"),
    )
    def update_freeze_indicator(frozen):
        """Update the live indicator based on freeze state."""
        if frozen:
            return "⏸ Paused", "red"
        return "● Live", "green"

    # =========================================================================
    # Notifications for New Data
    # =========================================================================
    @app.callback(
        Output("notification-container", "sendNotifications"),
        Input("ws-message-store", "data"),
        State("freeze-toggle", "checked"),
        prevent_initial_call=True,
    )
    def send_new_data_notification(ws_data, frozen):
        """Send notification when new data arrives."""
        if not ws_data:
            return no_update

        count = ws_data.get('count', 0)
        total = ws_data.get('total', 0)

        notification = {
            "action": "show",
            "id": f"new-data-{total}",
            "title": "New Data Received",
            "message": f"+{count} image{'s' if count > 1 else ''} added (total: {total})",
            "color": "green" if not frozen else "orange",
            "autoClose": 3000,
        }

        if frozen:
            notification["title"] = "New Data (Paused)"
            notification["message"] = f"+{count} image{'s' if count > 1 else ''} - updates paused"

        return [notification]

    # =========================================================================
    # Event Log & Pending Update Indicator
    # =========================================================================
    @app.callback(
        [
            Output("event-log-container", "children"),
            Output("event-count-badge", "children"),
            Output("event-log-store", "data"),  # Persist events in store
            Output("pending-update-store", "data"),
            Output("pending-badge", "style"),
            Output("new-rows-store", "data"),
        ],
        Input("ws-message-store", "data"),
        [
            State("event-log-store", "data"),
            State("pending-update-store", "data"),
            State("new-rows-store", "data"),
            State("freeze-toggle", "checked"),
        ],
        prevent_initial_call=True,
    )
    def update_event_log(ws_data, existing_events, _pending, existing_new_rows, frozen):
        """Update event log and show pending update indicator."""
        if not ws_data:
            return no_update, no_update, no_update, no_update, no_update, no_update

        # If frozen, only update event log but don't trigger other updates
        count = ws_data.get('count', 0)
        total = ws_data.get('total', 0)
        images = ws_data.get('images', [])
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Track ONLY the current batch of new filenames (not cumulative)
        # This ensures only the most recently added rows are highlighted
        new_row_filenames = [img.get('filename', '') for img in images]

        # Create new event data (serializable for store)
        new_event_data = {
            "count": count,
            "total": total,
            "timestamp": timestamp,
            "images": images,
            "is_new": True,
        }

        # Get existing events or start fresh
        if existing_events and isinstance(existing_events, list):
            # Mark old events as not new
            for evt in existing_events:
                evt["is_new"] = False
            # Keep last 15 events
            all_events = [new_event_data] + existing_events[:14]
        else:
            all_events = [new_event_data]

        # Render events as components
        event_components = []
        for i, evt in enumerate(all_events):
            is_newest = (i == 0)
            evt_images = evt.get('images', [])

            # Build image details
            image_details = []
            for img in evt_images[:3]:  # Show max 3 images
                image_details.append(
                    dmc.Group(
                        gap=4,
                        children=[
                            dmc.Badge(
                                f"pos {img.get('pos', '?')}",
                                size="xs",
                                variant="dot",
                                color="blue",
                            ),
                            dmc.Text(
                                img.get('filename', 'unknown')[:25] + ('...' if len(img.get('filename', '')) > 25 else ''),
                                size="xs",
                                c="dimmed",
                                style={"fontFamily": "monospace"},
                            ),
                        ]
                    )
                )
            if len(evt_images) > 3:
                image_details.append(
                    dmc.Text(f"... and {len(evt_images) - 3} more", size="xs", c="dimmed", fs="italic")
                )

            event_components.append(
                dmc.Paper(
                    children=dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Group(
                                gap="xs",
                                justify="space-between",
                                children=[
                                    dmc.Group(
                                        gap="xs",
                                        children=[
                                            dmc.ThemeIcon(
                                                children="📷",
                                                color="green" if is_newest else "gray",
                                                variant="filled" if is_newest else "light",
                                                size="sm",
                                                radius="xl",
                                            ),
                                            dmc.Text(
                                                f"+{evt['count']} image{'s' if evt['count'] > 1 else ''}",
                                                size="sm",
                                                fw=600 if is_newest else 400,
                                                c="green" if is_newest else "dark",
                                            ),
                                        ]
                                    ),
                                    dmc.Text(
                                        evt['timestamp'],
                                        size="xs",
                                        c="dimmed",
                                    ),
                                ]
                            ),
                            # Image details
                            dmc.Stack(
                                gap=2,
                                children=image_details,
                            ) if image_details else None,
                            dmc.Text(
                                f"Total: {evt['total']} images",
                                size="xs",
                                c="dimmed",
                            ),
                        ]
                    ),
                    p="xs",
                    radius="sm",
                    withBorder=True,
                    style={
                        "backgroundColor": "var(--mantine-color-green-1)" if is_newest else "transparent",
                        "borderColor": "var(--mantine-color-green-5)" if is_newest else "var(--mantine-color-gray-3)",
                        "borderWidth": "2px" if is_newest else "1px",
                        "transition": "all 0.3s ease",
                    },
                    className="new-event" if is_newest else "",
                )
            )

        event_count = len(all_events)

        # Show the pending badge when new data arrives (even if frozen - user should know)
        # Only pass the CURRENT batch of new filenames for highlighting
        return event_components, str(event_count), all_events, not frozen, {"display": "inline-block"}, new_row_filenames

    # =========================================================================
    # Live Statistics Update
    # =========================================================================
    @app.callback(
        Output("stats-display", "children", allow_duplicate=True),
        Input("ws", "message"),
        [
            State("patch-dropdown", "value"),
            State("coord-dropdown", "value"),
            State("freeze-toggle", "checked"),
        ],
        prevent_initial_call=True,
    )
    def update_live_stats(ws_message, _patch_type, coordinate, frozen):
        """Update statistics when new data arrives via WebSocket."""
        if not ws_message or not coordinate or frozen:
            return no_update

        try:
            ws_data = json.loads(ws_message.get('data', '{}'))
            if ws_data.get('type') != 'new_image':
                return no_update
        except (json.JSONDecodeError, AttributeError):
            return no_update

        # Reload fresh data
        df_fresh = load_phenobase_data()
        coordinate_int = int(coordinate)
        filtered_df = df_fresh[df_fresh['pos'] == coordinate_int]

        if len(filtered_df) == 0:
            return no_update

        # Get unique dates and time periods
        dates = filtered_df['date'].unique() if 'date' in filtered_df.columns else []
        time_periods = filtered_df['time_period'].unique() if 'time_period' in filtered_df.columns else []

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
                        dmc.ThemeIcon(size="lg", radius="md", variant="light", color="orange", children="🔄"),
                        dmc.Stack(
                            gap=0,
                            children=[
                                dmc.Text("LIVE", fw=700, size="xl", c="orange"),
                                dmc.Text("Refresh UMAP for clusters", size="xs", c="dimmed"),
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

        print(f"[Stats] Updated live stats: {len(filtered_df)} images", flush=True)
        return stats_display

    # =========================================================================
    # UMAP Plot - Manual Update Only
    # =========================================================================
    @app.callback(
        [
            Output("umap-plot", "figure"),
            Output("data-store", "data"),
            Output("features-store", "data"),
            Output("stats-display", "children"),
            Output("pending-update-store", "data", allow_duplicate=True),
            Output("pending-badge", "style", allow_duplicate=True),
        ],
        [
            Input("patch-dropdown", "value"),
            Input("coord-dropdown", "value"),
            Input("update-umap-btn", "n_clicks"),
        ],
        prevent_initial_call='initial_duplicate',
    )
    def update_umap_and_data(patch_type, coordinate, update_clicks):
        """Update UMAP plot - triggered by filter change or Update button."""
        if not patch_type or coordinate is None:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="Select patch type and coordinate",
                xaxis_title="UMAP 1",
                yaxis_title="UMAP 2",
            )
            return empty_fig, None, None, "No data selected", False, {"display": "none"}

        coordinate = int(coordinate)

        # Always reload from CSV to get latest data
        df_current = load_phenobase_data()
        filtered_df = get_image_dataframe(df_current, patch_type, coordinate)

        if len(filtered_df) == 0:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="No data available",
                xaxis_title="UMAP 1",
                yaxis_title="UMAP 2",
            )
            return empty_fig, None, None, "No images found", False, {"display": "none"}

        # Include row count in cache key to bust cache when new data is added
        cache_key = f"umap_{patch_type}_{coordinate}_{len(filtered_df)}"

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

        # Clear pending update flag and hide badge
        return fig, umap_df.to_dict("records"), None, stats_display, False, {"display": "none"}

    # =========================================================================
    # Time Series Plot - Auto-updates with smooth transitions
    # =========================================================================
    @app.callback(
        [
            Output("timeseries-plot", "figure"),
            Output("timeseries-store", "data"),
        ],
        [
            Input("patch-dropdown", "value"),
            Input("coord-dropdown", "value"),
            Input("ws", "message"),  # Direct WebSocket input for live updates
            Input("update-umap-btn", "n_clicks"),  # Manual refresh trigger
        ],
        [
            State("freeze-toggle", "checked"),
            State("data-store", "data"),  # Changed to State to avoid circular updates
        ],
    )
    def update_time_series(patch_type, coordinate, ws_message, n_clicks, frozen, _stored_data):
        """Update time series - auto-refreshes when new data arrives."""
        triggered_id = ctx.triggered_id
        print(f"[TimeSeries] *** CALLBACK TRIGGERED *** by: {triggered_id}", flush=True)
        print(f"[TimeSeries] ws_message={ws_message is not None}, patch_type={patch_type}, coord={coordinate}, frozen={frozen}", flush=True)

        # Variable to store new filenames for highlighting
        ws_new_filenames = []

        # Handle WebSocket messages
        if triggered_id == "ws" and ws_message:
            # Check freeze state
            if frozen:
                print("[TimeSeries] Frozen - skipping WebSocket update", flush=True)
                return no_update, no_update
            # Parse WebSocket message directly
            try:
                ws_data = json.loads(ws_message.get('data', '{}'))
                if ws_data.get('type') != 'new_image':
                    print("[TimeSeries] Not a new_image message, skipping", flush=True)
                    return no_update, no_update
                # Extract unique patch paths from WebSocket message (czi_filename is NOT unique per row)
                ws_new_filenames = [img.get('patch_path', '') for img in ws_data.get('images', [])]
                print(f"[TimeSeries] New patch paths from WS: {ws_new_filenames}", flush=True)
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"[TimeSeries] Failed to parse WebSocket message: {e}", flush=True)
                return no_update, no_update

        # Always reload fresh data when coordinate is available
        if coordinate:
            print(f"[TimeSeries] Loading fresh data for coord={coordinate}", flush=True)
            df_fresh = load_phenobase_data()
            coordinate_int = int(coordinate)
            df = df_fresh[df_fresh['pos'] == coordinate_int].copy()
            print(f"[TimeSeries] Filtered: {len(df)} rows", flush=True)

            if len(df) == 0:
                print("[TimeSeries] No data after filtering", flush=True)
                return go.Figure(), None

            if 'timestamp' not in df.columns or 'object_count' not in df.columns:
                print("[TimeSeries] ERROR: Missing columns!", flush=True)
                return go.Figure(), None

            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            print("[TimeSeries] Missing coordinate", flush=True)
            return go.Figure(), None

        try:
            df = df.sort_values('timestamp')

            print(f"[TimeSeries] Building plot with {len(df)} points", flush=True)

            # Mark new points for highlighting - use patch paths from WebSocket message
            # Only highlight if we have new patch paths from the current WebSocket trigger
            new_rows_set = set(ws_new_filenames) if ws_new_filenames else set()
            # Use the first patch path column for matching (it's unique per row)
            patch_col = 'patches_2d_ch0_tl_exp_path'
            if patch_col in df.columns:
                df['is_new'] = df[patch_col].isin(new_rows_set)
            else:
                df['is_new'] = False
            print(f"[TimeSeries] Marking {df['is_new'].sum()} points as new out of {len(df)}", flush=True)

            # Split into old and new data for different styling
            df_old = df[~df['is_new']]
            df_new = df[df['is_new']]

            # Create scatter plot with two traces
            fig = go.Figure()

            # Old points (regular styling)
            if len(df_old) > 0:
                fig.add_trace(go.Scatter(
                    x=df_old['timestamp'],
                    y=df_old['object_count'],
                    mode='markers',
                    name='Images',
                    marker=dict(
                        size=8,
                        color=df_old['object_count'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="Objects"),
                        opacity=0.7,
                        line=dict(width=1, color='white')
                    ),
                    customdata=df_old[['czi_filename', 'id']] if 'id' in df_old.columns else df_old[['czi_filename']],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Time: %{x}<br>"
                        "Objects: %{y}<br>"
                        "<extra></extra>"
                    ),
                ))

            # New points (subtle highlight: slightly larger with white glow border)
            if len(df_new) > 0:
                fig.add_trace(go.Scatter(
                    x=df_new['timestamp'],
                    y=df_new['object_count'],
                    mode='markers',
                    name='New',
                    marker=dict(
                        size=11,  # Slightly larger
                        color=df_new['object_count'],
                        colorscale='Viridis',
                        showscale=False,
                        opacity=1.0,
                        line=dict(width=2, color='rgba(255,255,255,0.9)'),  # White glow border
                    ),
                    customdata=df_new[['czi_filename', 'id']] if 'id' in df_new.columns else df_new[['czi_filename']],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b> (new)<br>"
                        "Time: %{x}<br>"
                        "Objects: %{y}<br>"
                        "<extra></extra>"
                    ),
                ))

            # Set explicit axis ranges based on data to ensure new points are visible
            x_min = df['timestamp'].min()
            x_max = df['timestamp'].max()
            y_min = df['object_count'].min()
            y_max = df['object_count'].max()

            # Add small padding to ranges
            x_padding = pd.Timedelta(seconds=30)
            y_padding = (y_max - y_min) * 0.1 if y_max > y_min else 1

            fig.update_xaxes(
                rangeslider_visible=True,
                range=[x_min - x_padding, x_max + x_padding],  # Explicit range
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1m", step="minute", stepmode="backward"),
                        dict(count=5, label="5m", step="minute", stepmode="backward"),
                        dict(count=10, label="10m", step="minute", stepmode="backward"),
                        dict(count=30, label="30m", step="minute", stepmode="backward"),
                        dict(count=60, label="60m", step="minute", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]),
                    bgcolor="#f1f3f5",
                    activecolor="#1971c2",
                ),
                rangeslider=dict(bgcolor="#f8f9fa", thickness=0.05),
            )

            fig.update_yaxes(range=[max(0, y_min - y_padding), y_max + y_padding])  # Explicit Y range

            fig.update_layout(
                title=f"Time Series: {patch_type} (position {coordinate})" if patch_type else "Time Series",
                xaxis_title="Time",
                yaxis_title="Number of Segmented Objects",
                height=350,
                hovermode="closest",
                # Use coordinate-based uirevision to preserve zoom within same view
                # but reset when coordinate changes
                uirevision=f"{patch_type}_{coordinate}",
            )

            timeseries_data = {
                'min_time': df['timestamp'].min().isoformat(),
                'max_time': df['timestamp'].max().isoformat(),
                'total_points': len(df),
            }

            print(f"[TimeSeries] Plot built successfully with {len(df)} points", flush=True)
            return fig, timeseries_data

        except Exception as e:
            print(f"[TimeSeries] ERROR building plot: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return go.Figure(), None

    # =========================================================================
    # Data Table - Auto-updates
    # =========================================================================
    @app.callback(
        [
            Output("data-table", "rowData"),
            Output("data-table", "columnDefs"),
            Output("table-row-count", "children"),
        ],
        [
            Input("umap-plot", "selectedData"),
            Input("umap-plot", "clickData"),
            Input("reset-selection-btn", "n_clicks"),
            Input("data-store", "data"),
            Input("ws", "message"),  # Direct WebSocket input for live updates
        ],
        [
            State("patch-dropdown", "value"),
            State("coord-dropdown", "value"),
            State("freeze-toggle", "checked"),
        ],
    )
    def update_table(selected_data, click_data, _reset_clicks, stored_data, ws_message, _patch_type, coordinate, frozen):
        """Update data table - auto-refreshes when new data arrives."""
        triggered_id = ctx.triggered_id
        print(f"[Table] *** CALLBACK TRIGGERED *** by: {triggered_id}", flush=True)

        # Variable to store new filenames for highlighting
        ws_new_filenames = []

        try:
            # If triggered by WebSocket, reload fresh data (simple coord filter, no image check)
            if triggered_id == "ws" and ws_message and coordinate:
                # Check freeze state
                if frozen:
                    print("[Table] Frozen - skipping WebSocket update", flush=True)
                    return no_update, no_update, no_update
                # Parse WebSocket message directly
                try:
                    ws_data = json.loads(ws_message.get('data', '{}'))
                    if ws_data.get('type') != 'new_image':
                        print("[Table] Not a new_image message, skipping", flush=True)
                        return no_update, no_update, no_update
                    # Extract unique patch paths from WebSocket message (czi_filename is NOT unique)
                    ws_new_filenames = [img.get('patch_path', '') for img in ws_data.get('images', [])]
                    print(f"[Table] New patch paths from WS: {ws_new_filenames}", flush=True)
                except (json.JSONDecodeError, AttributeError) as e:
                    print(f"[Table] Failed to parse WebSocket message: {e}", flush=True)
                    return no_update, no_update, no_update
                print("[Table] WebSocket trigger - reloading fresh data", flush=True)
                df_fresh = load_phenobase_data()
                coordinate_int = int(coordinate)
                # Simple filter by coordinate only - don't check if images exist
                filtered_df = df_fresh[df_fresh['pos'] == coordinate_int].copy()
                print(f"[Table] Fresh data (coord={coordinate_int}): {len(filtered_df)} rows", flush=True)
                if len(filtered_df) > 0:
                    df = filtered_df
                else:
                    return [], [], "0 rows"
            elif stored_data:
                df = pd.DataFrame(stored_data)
            else:
                return [], [], "0 rows"
        except Exception as e:
            print(f"[Table] ERROR loading data: {e}", flush=True)
            return [], [], f"Error: {e}"

        selected_indices = []

        # WebSocket trigger takes priority - always show latest data
        if triggered_id == "ws":
            # WebSocket trigger: show ALL data sorted by timestamp (newest first)
            # AG Grid will paginate, so we can show all rows
            print(f"[Table] WebSocket trigger - showing ALL {len(df)} rows sorted by timestamp", flush=True)
            selected_df = df.sort_values('timestamp', ascending=False) if 'timestamp' in df.columns else df
        elif triggered_id == "reset-selection-btn":
            selected_df = df.sort_values('timestamp', ascending=False) if 'timestamp' in df.columns else df
        elif selected_data and "points" in selected_data:
            selected_indices = [p["pointIndex"] for p in selected_data["points"]]
            selected_df = df.iloc[selected_indices] if selected_indices else df.head(20)
        elif click_data and "points" in click_data:
            selected_indices = [click_data["points"][0]["pointIndex"]]
            selected_df = df.iloc[selected_indices]
        else:
            # Default: show all data sorted by timestamp (newest first)
            selected_df = df.sort_values('timestamp', ascending=False) if 'timestamp' in df.columns else df

        column_defs = [
            {"field": "czi_filename", "headerName": "Filename", "flex": 2},
            {"field": "pos", "headerName": "Position", "flex": 1},
            {"field": "date", "headerName": "Date", "flex": 1},
            {"field": "time_period", "headerName": "Time", "flex": 1},
            {"field": "timestamp", "headerName": "Timestamp", "flex": 1.5},
            {"field": "object_count", "headerName": "Objects", "flex": 1},
        ]

        # Add UMAP columns only if they exist
        if "cluster" in selected_df.columns:
            column_defs.append({"field": "cluster", "headerName": "Cluster", "flex": 1})
        if "umap_x" in selected_df.columns:
            column_defs.append({"field": "umap_x", "headerName": "UMAP X", "flex": 1, "valueFormatter": {"function": "d3.format('.2f')(params.value)"}})
        if "umap_y" in selected_df.columns:
            column_defs.append({"field": "umap_y", "headerName": "UMAP Y", "flex": 1, "valueFormatter": {"function": "d3.format('.2f')(params.value)"}})

        # Build list of columns to include
        table_columns = ["czi_filename", "pos", "date", "time_period"]
        if "timestamp" in selected_df.columns:
            table_columns.append("timestamp")
        if "object_count" in selected_df.columns:
            table_columns.append("object_count")
        if "cluster" in selected_df.columns:
            table_columns.append("cluster")
        if "umap_x" in selected_df.columns:
            table_columns.extend(["umap_x", "umap_y"])

        available_cols = [c for c in table_columns if c in selected_df.columns]
        table_data = selected_df[available_cols].to_dict("records")

        # Mark new rows for highlighting and add unique row IDs
        # Use patch path for matching (czi_filename is NOT unique per row)
        new_rows_set = set(ws_new_filenames) if ws_new_filenames else set()
        patch_col = 'patches_2d_ch0_tl_exp_path'

        # Get patch paths from selected_df to match against (table_data may not have this column)
        patch_paths = selected_df[patch_col].tolist() if patch_col in selected_df.columns else []

        for i, row in enumerate(table_data):
            row['_row_id'] = f"{row.get('czi_filename', '')}_{row.get('timestamp', i)}"
            # Check if the corresponding patch path is in the new rows set
            is_new = False
            if i < len(patch_paths):
                is_new = patch_paths[i] in new_rows_set
            row['_is_new'] = is_new

        row_count = f"{len(table_data)} of {len(df)} rows"
        new_count = sum(1 for r in table_data if r.get('_is_new'))
        print(f"[Table] Marking {new_count} rows as new out of {len(table_data)}", flush=True)
        if new_count > 0:
            row_count = f"{len(table_data)} of {len(df)} rows ({new_count} new)"
        print(f"[Table] Returning {len(table_data)} rows to AG Grid ({new_count} new)", flush=True)

        return table_data, column_defs, row_count

    # =========================================================================
    # Image Grid - Manual update with UMAP
    # =========================================================================
    @app.callback(
        Output("image-grid", "children"),
        [
            Input("umap-plot", "selectedData"),
            Input("umap-plot", "clickData"),
            Input("reset-selection-btn", "n_clicks"),
            Input("data-store", "data"),
        ]
    )
    def update_image_grid(selected_data, click_data, reset_clicks, stored_data):
        """Update image grid based on selection."""
        if not stored_data:
            return html.Div("No data available")

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

        return create_image_grid(selected_df)

    # =========================================================================
    # Image Modal
    # =========================================================================
    @app.callback(
        [
            Output("image-modal", "opened"),
            Output("modal-image", "src"),
        ],
        [Input({"type": "image-thumb", "index": ALL}, "n_clicks")],
        [
            State("image-modal", "opened"),
        ],
        prevent_initial_call=True,
    )
    def toggle_modal(n_clicks_list, is_open):
        """Toggle fullscreen image modal."""
        if not any(n_clicks_list):
            return False, ""

        # Use ctx.triggered_id to get the exact image that was clicked
        triggered_id = ctx.triggered_id
        if triggered_id and isinstance(triggered_id, dict) and triggered_id.get("type") == "image-thumb":
            image_path = triggered_id["index"]
            return True, f"/images/{image_path}"

        return False, ""

    # =========================================================================
    # Time Range Filter (existing functionality)
    # =========================================================================
    @app.callback(
        [
            Output("umap-plot", "figure", allow_duplicate=True),
            Output("data-store", "data", allow_duplicate=True),
            Output("time-filter-badge", "children"),
        ],
        [Input("timeseries-plot", "relayoutData")],
        [
            State("data-store", "data"),
            State("patch-dropdown", "value"),
            State("coord-dropdown", "value"),
        ],
        prevent_initial_call=True,
    )
    def filter_by_time_range(relayout_data, stored_data, patch_type, coordinate):
        """Time range selection triggers UMAP recalculation."""
        if not relayout_data or not stored_data:
            raise PreventUpdate

        df = pd.DataFrame(stored_data)

        if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
            start_time = pd.to_datetime(relayout_data['xaxis.range[0]'])
            end_time = pd.to_datetime(relayout_data['xaxis.range[1]'])

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            time_filtered_df = df[
                (df['timestamp'] >= start_time) &
                (df['timestamp'] <= end_time)
            ].copy()

            if len(time_filtered_df) == 0:
                empty_fig = go.Figure()
                empty_fig.update_layout(title="No data in selected time range")
                return empty_fig, stored_data, "No data in range"

            cache_key = f"umap_{patch_type}_{coordinate}_{start_time.isoformat()}_{end_time.isoformat()}"

            @cache.memoize(timeout=3600)
            def get_cached_umap(key, df_subset):
                features, clusters = generate_random_features(df_subset)
                embedding = compute_umap_embedding(features)
                return embedding, clusters

            embedding, clusters = get_cached_umap(cache_key, time_filtered_df)
            umap_df = create_umap_dataframe(time_filtered_df, embedding, clusters)

            fig = px.scatter(
                umap_df,
                x="umap_x",
                y="umap_y",
                color="cluster",
                hover_data=["czi_filename", "pos", "date", "time_period"],
                title=f"UMAP: {patch_type} (position {coordinate}) - Time Filtered",
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

            duration_minutes = (end_time - start_time).total_seconds() / 60
            if duration_minutes < 60:
                badge_text = f"{len(time_filtered_df)} images ({duration_minutes:.0f}m)"
            else:
                badge_text = f"{len(time_filtered_df)} images ({duration_minutes/60:.1f}h)"

            return fig, umap_df.to_dict("records"), badge_text

        elif 'xaxis.autorange' in relayout_data:
            # User clicked "All" or double-clicked to reset - reload full data
            print("[TimeFilter] Resetting to full data view", flush=True)

            # Reload fresh data from source
            df_full = load_phenobase_data()

            # Filter by coordinate like the main callback does
            coordinate_int = int(coordinate) if coordinate else None
            if coordinate_int is not None:
                filtered_df = df_full[df_full['pos'] == coordinate_int].copy()
            else:
                filtered_df = df_full.copy()

            # Keep only rows with valid images
            if 'image_path' in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df['image_path'].apply(lambda p: Path(p).exists() if pd.notna(p) else False)
                ].copy()

            if len(filtered_df) == 0:
                return no_update, stored_data, "No data"

            # Recompute UMAP with full data
            cache_key = f"umap_{patch_type}_{coordinate}_full_reset"

            @cache.memoize(timeout=3600)
            def get_cached_umap_reset(key, df_subset):
                features, clusters = generate_random_features(df_subset)
                embedding = compute_umap_embedding(features)
                return embedding, clusters

            embedding, clusters = get_cached_umap_reset(cache_key, filtered_df)
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
            )

            fig.update_layout(
                clickmode="event+select",
                dragmode="lasso",
                hovermode="closest",
                height=500,
                margin=dict(l=20, r=20, t=40, b=20),
            )

            return fig, umap_df.to_dict("records"), f"{len(filtered_df)} images (all data)"

        raise PreventUpdate


def create_image_grid(df: pd.DataFrame) -> html.Div:
    """Create a grid of image thumbnails."""
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
