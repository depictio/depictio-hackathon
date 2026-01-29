# Dash UMAP Image Explorer

Interactive UMAP-based image exploration tool built with Dash and Dash Mantine Components (DMC).

## Overview

This application provides an interactive interface for exploring image datasets using UMAP (Uniform Manifold Approximation and Projection) dimensionality reduction. Users can filter images by patch type and coordinate position, visualize them in 2D UMAP space, and interactively select images to view details.

## Features

- **Interactive UMAP Visualization**: Explore images in 2D embedding space with click and lasso selection
- **Dynamic Filtering**: Filter by patch type (4 options) and coordinate position (2 options)
- **Image Grid**: View thumbnails of selected images with hover effects
- **Fullscreen Modal**: Click any thumbnail to view the full-size image
- **Data Table**: Inspect metadata for selected images
- **Responsive Layout**: 1/4 controls, 3/4 visualizations layout using DMC Grid
- **Performance Optimized**: UMAP embeddings cached for fast recomputation

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

1. Install dependencies:
```bash
uv sync
```

2. Run the application:
```bash
uv run python app.py
```

3. Open your browser to:
```
http://127.0.0.1:8050
```

## Usage Guide

### Filtering Images
1. Select a **Patch Type** from the dropdown (e.g., `ch0_tl_exp`, `ch1_hoechst_cfw_exp`)
2. Select a **Coordinate Position** (0 or 1)
3. The UMAP plot and statistics will update automatically

### Selecting Images
- **Single Click**: Select a single point on the UMAP plot
- **Lasso Selection**: Draw a freeform selection around points
- **Rectangle Selection**: Drag to select a rectangular region
- Selected images appear in the image grid and data table

### Viewing Images
- **Hover**: Hover over thumbnails for hover effects
- **Click**: Click any thumbnail to open it in fullscreen
- **Close**: Press ESC or click outside to close the fullscreen view

## Data Structure

### Input Data
- **CSV**: `data/phenobase.csv` (110 rows: 1 category header + 1 column header + 108 data)
- **Columns**:
  - `czi_filename`: Source filename
  - `pos`: Coordinate position (0 or 1)
  - `patches_2d_ch0_tl_exp_path`: Path to ch0 images
  - `patches_2d_ch1_hoechst_cfw_exp_path`: Path to ch1 images
  - `patches_2d_ch2_pe_exp_path`: Path to ch2 images
  - `patches_2d_ch3_chloA_exp_path`: Path to ch3 images

### Patch Types
1. `ch0_tl_exp` - Transmitted light experiment
2. `ch1_hoechst_cfw_exp` - Hoechst CFW experiment
3. `ch2_pe_exp` - PE experiment
4. `ch3_chloA_exp` - Chlorophyll A experiment

### Image Directories
- `data/patches_2d_ch0_tl_exp/`
- `data/patches_2d_ch1_hoechst_cfw_exp/`
- `data/patches_2d_ch2_pe_exp/` (if exists)
- `data/patches_2d_ch3_chloA_exp/` (if exists)

## Architecture

### Project Structure
```
depictio-hackathon/
├── app.py                  # Main application entry point
├── pyproject.toml          # Dependencies and project config
├── README.md               # This file
├── data/
│   ├── phenobase.csv      # Image metadata
│   └── patches_2d_*/      # Image directories
├── src/
│   ├── __init__.py
│   ├── data_loader.py     # CSV loading and feature generation
│   ├── umap_processor.py  # UMAP computation with caching
│   ├── layout.py          # DMC UI components
│   └── callbacks.py       # Dash callbacks
└── assets/
    └── custom.css         # Custom styling
```

### Components

#### `src/data_loader.py`
- `load_phenobase_data()`: Load CSV, skip category header
- `extract_metadata_columns()`: Extract patch types and coordinates
- `generate_random_features()`: Create 15 correlated synthetic features
- `verify_image_paths()`: Validate and convert to absolute paths
- `get_image_dataframe()`: Filter data by patch type and coordinate

#### `src/umap_processor.py`
- `compute_umap_embedding()`: Compute UMAP with StandardScaler preprocessing
- `create_umap_dataframe()`: Combine embeddings with metadata

#### `src/layout.py`
- `create_layout()`: Build DMC-based responsive layout
  - Left panel: Filters and statistics (1/4 width)
  - Right panel: UMAP plot, image grid, data table (3/4 width)

#### `src/callbacks.py`
- `update_umap_and_data()`: Filter data and compute UMAP
- `update_images_and_table()`: Update images based on selection
- `toggle_modal()`: Handle fullscreen image modal
- `create_image_grid()`: Generate thumbnail grid

#### `app.py`
- Initialize Dash app with DMC
- Configure Flask-Caching (1-hour timeout)
- Register callbacks
- Serve images via `/images/<path>` endpoint

### Callback Flow
```
User Interaction → Callback → Component Update

1. Dropdown changes → update_umap_and_data() → UMAP plot, data store, stats
2. UMAP click/select → update_images_and_table() → Image grid, data table
3. Thumbnail click → toggle_modal() → Fullscreen modal
```

## Performance Optimizations

1. **UMAP Caching**: Embeddings cached for 1 hour using Flask-Caching
2. **Lazy Loading**: Images loaded on-demand via Flask route
3. **Data Store**: Filtered data shared between callbacks to avoid recomputation
4. **Loading States**: Spinners shown during UMAP computation
5. **Fixed Seed**: Reproducible feature generation (seed=42)

## Troubleshooting

### Images not loading
- Verify image paths in `data/phenobase.csv`
- Check that image directories exist in `data/`
- Ensure images are PNG format

### UMAP computation slow
- First computation may take 3-5 seconds
- Subsequent loads with same filters are instant (cached)
- Try reducing dataset size for testing

### Layout issues
- Clear browser cache
- Check browser console for errors
- Ensure DMC version >= 0.14.0

### Port already in use
```bash
# Kill process on port 8050
lsof -ti:8050 | xargs kill -9

# Or use a different port
python app.py --port 8051
```

## Development

### Adding New Features
1. **New filters**: Add to `layout.py` and update callbacks
2. **New visualizations**: Add to `layout.py` and create callback in `callbacks.py`
3. **New data columns**: Update `data_loader.py` to extract metadata

### Testing
```bash
# Run application in debug mode
uv run python app.py

# Test with different data
# Replace data/phenobase.csv with your own CSV
# Update patch_types in data_loader.py if needed
```

## Dependencies

- **dash** (>=2.18.0): Web framework
- **dash-mantine-components** (>=0.14.0): UI components
- **plotly** (>=5.24.0): Interactive plots
- **pandas** (>=2.2.0): Data manipulation
- **numpy** (>=1.26.0): Numerical computing
- **scikit-learn** (>=1.5.0): Preprocessing
- **umap-learn** (>=0.5.6): Dimensionality reduction
- **pillow** (>=10.4.0): Image processing
- **flask-caching** (>=2.3.0): Caching layer

## License

This project is part of the Depictio Hackathon.

## Authors

Created with Claude Code following the implementation plan.
