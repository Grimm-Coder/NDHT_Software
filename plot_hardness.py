# file: hardness_plotter.py

import pandas as pd
import numpy as np
import pyvista as pv
from matplotlib import cm
from scipy.interpolate import RBFInterpolator

def plot_hardness_on_ply(
    ply_file: str,
    csv_file: str,
    reduction: float = 0.5,
    z_threshold: float = None,
    title: str = "Scan Results"
):
    """
    Plots a PLY mesh with a hardness heatmap only on the top surface, labels the hardest and softest points,
    adds a title, and opens the window in fullscreen.

    Parameters:
    - ply_file: Path to the PLY mesh.
    - csv_file: Path to CSV with columns ['X_aligned','Y_aligned','Z_aligned','Hardness',...]
    - reduction: Fraction of faces to keep for simplification (0 < reduction <= 1)
    - z_threshold: Minimum Z value to be considered "top surface". If None, automatically set near max Z.
    - title: Title text displayed on the plot
    """
    # Load and simplify mesh
    mesh = pv.read(ply_file).decimate(reduction)
    print(f"Mesh: {mesh.n_cells} faces, {mesh.n_points} points")

    # Load CSV
    df = pd.read_csv(csv_file)
    coords = df[['X_aligned','Y_aligned','Z_aligned']].to_numpy()
    hardness = df['Hardness'].to_numpy()

    # Determine Z threshold if not provided
    if z_threshold is None:
        z_max = mesh.points[:,2].max()
        z_threshold = z_max - 0.5  # default margin below max Z

    # Select top surface vertices
    top_surface_idx = mesh.points[:,2] >= z_threshold

    # Initialize all colors as gray
    colors = np.full(mesh.points.shape, 0.5)  # default gray

    # Interpolate hardness only on top surface
    rbf = RBFInterpolator(coords, hardness, kernel='linear')
    interpolated = rbf(mesh.points[top_surface_idx])

    # Map to RGB
    norm_interpolated = (interpolated - hardness.min()) / (hardness.max() - hardness.min())
    colors[top_surface_idx] = cm.viridis(norm_interpolated)[:, :3]

    # Assign colors
    mesh.point_data['HardnessColor'] = colors

    # Identify hardest and softest points
    hardest_idx = np.argmax(interpolated)
    softest_idx = np.argmin(interpolated)
    top_points = mesh.points[top_surface_idx]
    hardest_point = top_points[hardest_idx]
    softest_point = top_points[softest_idx]

    # Plot
    plotter = pv.Plotter()
    plotter.add_mesh(mesh, scalars='HardnessColor', rgb=True, show_edges=False)

    # Add scalar bar
    plotter.add_scalar_bar(
        title='Hardness', n_labels=5, vertical=True,
        title_font_size=20, label_font_size=16
    )

    # Add labels for hardest and softest points (black)
    plotter.add_point_labels(
        np.array([hardest_point, softest_point]),
        [f'Hardest: {interpolated[hardest_idx]:.1f}', f'Softest: {interpolated[softest_idx]:.1f}'],
        point_size=15,
        font_size=18,
        text_color='black'
    )

    # Add title at top-center (black)
    plotter.add_text(title, position=(0.5, 0.95), font_size=24, color='black', shadow=True, viewport=True)

    # Show in fullscreen
    plotter.show(full_screen=True)