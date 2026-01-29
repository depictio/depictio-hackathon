"""UMAP embedding computation with caching."""

import numpy as np
import pandas as pd
from umap import UMAP
from sklearn.preprocessing import StandardScaler


def compute_umap_embedding(features: np.ndarray, n_neighbors: int = 10, min_dist: float = 0.3,
                           random_state: int = 42) -> np.ndarray:
    """
    Compute UMAP embedding from features.

    Args:
        features: Feature matrix of shape (n_samples, n_features)
        n_neighbors: Number of neighbors for UMAP (lower = more local structure)
        min_dist: Minimum distance for UMAP (higher = more spread out)
        random_state: Random seed for reproducibility

    Returns:
        UMAP embedding of shape (n_samples, 2)
    """
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    n_samples = features.shape[0]
    n_neighbors_adj = min(n_neighbors, n_samples - 1)

    umap_model = UMAP(
        n_neighbors=n_neighbors_adj,
        min_dist=min_dist,
        n_components=2,
        random_state=random_state,
        metric='euclidean',
        spread=1.0,
    )

    embedding = umap_model.fit_transform(features_scaled)

    return embedding


def create_umap_dataframe(df: pd.DataFrame, embedding: np.ndarray, clusters: np.ndarray = None) -> pd.DataFrame:
    """
    Combine UMAP embedding with metadata.

    Args:
        df: Original dataframe with metadata
        embedding: UMAP embedding array
        clusters: Optional cluster labels for coloring

    Returns:
        DataFrame with UMAP coordinates and metadata
    """
    umap_df = df.copy()
    umap_df['umap_x'] = embedding[:, 0]
    umap_df['umap_y'] = embedding[:, 1]

    if clusters is not None:
        umap_df['cluster'] = clusters.astype(str)

    return umap_df
