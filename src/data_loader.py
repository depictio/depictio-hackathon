"""Data loading and feature generation for the UMAP image explorer."""

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime


def extract_time_info(filename: str) -> dict:
    """
    Extract time information from CZI filename.

    Expected format: PK2_BAR_5to20_YYYYMMDD_AM/PM_XX

    Args:
        filename: CZI filename string

    Returns:
        Dictionary with date, time_period, and formatted_datetime
    """
    try:
        parts = filename.split('_')
        date_str = None
        time_period = None

        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit():
                date_str = part
                if i + 1 < len(parts) and parts[i + 1] in ['AM', 'PM']:
                    time_period = parts[i + 1]
                break

        if date_str:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            formatted_datetime = f"{formatted_date} {time_period}" if time_period else formatted_date

            return {
                'date': formatted_date,
                'time_period': time_period or 'N/A',
                'datetime': formatted_datetime
            }
    except:
        pass

    return {
        'date': 'N/A',
        'time_period': 'N/A',
        'datetime': 'N/A'
    }


def load_phenobase_data(csv_path: str = "data/phenobase.csv") -> pd.DataFrame:
    """
    Load phenobase CSV data, skipping the first category header row.

    Args:
        csv_path: Path to the phenobase CSV file

    Returns:
        DataFrame with image metadata
    """
    df = pd.read_csv(csv_path, skiprows=[0])
    df['id'] = range(len(df))

    time_info = df['czi_filename'].apply(extract_time_info)
    df['date'] = time_info.apply(lambda x: x['date'])
    df['time_period'] = time_info.apply(lambda x: x['time_period'])
    df['datetime'] = time_info.apply(lambda x: x['datetime'])

    return df


def extract_metadata_columns(df: pd.DataFrame, base_path: str = "data") -> dict:
    """
    Extract metadata for dropdowns from the dataframe.
    Only includes patch types that have actual image directories.

    Args:
        df: DataFrame with image metadata
        base_path: Base directory for images

    Returns:
        Dictionary with patch types, coordinates, and patch column names
    """
    patch_columns = [col for col in df.columns if col.startswith('patches_2d_')]

    available_patch_types = []
    available_patch_columns = []

    for col in patch_columns:
        patch_type = col.replace('patches_2d_', '').replace('_path', '')
        patch_dir = Path(base_path) / f'patches_2d_{patch_type}'

        if patch_dir.exists():
            available_patch_types.append(patch_type)
            available_patch_columns.append(col)

    coordinates = sorted(df['pos'].unique())

    return {
        'patch_types': available_patch_types,
        'coordinates': coordinates,
        'patch_columns': available_patch_columns
    }


def generate_random_features(df: pd.DataFrame, n_features: int = 50, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate random numerical features with distinct clustering patterns for UMAP.
    Creates realistic high-dimensional structure with multiple visible clusters.

    Args:
        df: DataFrame with image metadata
        n_features: Number of features to generate
        seed: Random seed for reproducibility

    Returns:
        Tuple of (features array of shape (n_samples, n_features), cluster labels)
    """
    np.random.seed(seed)
    n_samples = len(df)

    n_clusters = max(3, n_samples // 10)
    cluster_assignments = np.array([i % n_clusters for i in range(n_samples)])
    np.random.shuffle(cluster_assignments)

    features = np.zeros((n_samples, n_features))

    angle_step = 2 * np.pi / n_clusters
    for cluster_id in range(n_clusters):
        mask = cluster_assignments == cluster_id
        n_in_cluster = mask.sum()

        if n_in_cluster == 0:
            continue

        angle = cluster_id * angle_step
        radius = 8.0 + np.random.randn() * 2.0

        cluster_center = np.zeros(n_features)
        cluster_center[0] = radius * np.cos(angle)
        cluster_center[1] = radius * np.sin(angle)

        for i in range(2, n_features):
            cluster_center[i] = np.random.randn() * 3.0

        features[mask] = cluster_center + np.random.randn(n_in_cluster, n_features) * 1.2

    if 'pos' in df.columns:
        pos_values = df['pos'].values
        pos_shift = np.where(pos_values == 0, -2.0, 2.0).reshape(-1, 1)
        features += pos_shift * np.random.randn(1, n_features) * 0.5

    return features, cluster_assignments


def verify_image_paths(df: pd.DataFrame, patch_column: str, base_path: str = "data") -> pd.Series:
    """
    Verify that image paths exist and convert to absolute paths.

    Args:
        df: DataFrame with image metadata
        patch_column: Column name containing image paths
        base_path: Base directory for images

    Returns:
        Series with absolute paths
    """
    base_path = Path(base_path).absolute()

    def make_absolute(rel_path):
        if pd.isna(rel_path):
            return None
        abs_path = base_path / rel_path
        return str(abs_path) if abs_path.exists() else None

    return df[patch_column].apply(make_absolute)


def get_image_dataframe(df: pd.DataFrame, patch_type: str = None, coordinate: int = None) -> pd.DataFrame:
    """
    Get filtered dataframe with absolute image paths.

    Args:
        df: Original dataframe
        patch_type: Patch type to filter by (e.g., 'ch0_tl_exp')
        coordinate: Coordinate position to filter by (0 or 1)

    Returns:
        Filtered dataframe with absolute image paths
    """
    filtered_df = df.copy()

    if coordinate is not None:
        filtered_df = filtered_df[filtered_df['pos'] == coordinate]

    if patch_type:
        patch_column = f'patches_2d_{patch_type}_path'
        filtered_df['image_path'] = verify_image_paths(filtered_df, patch_column)
        filtered_df = filtered_df[filtered_df['image_path'].notna()]

    return filtered_df
