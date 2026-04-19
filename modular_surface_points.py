import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
from plyfile import PlyData
from sklearn.cluster import DBSCAN
from plyfile import PlyElement, PlyData

def save_aligned_ply(vertices_aligned, original_ply_file, output_ply_file="aligned_output.ply"):
    """
    Save the aligned PLY vertices to a new PLY file.
    Preserves original faces if available.
    """
    ply = PlyData.read(original_ply_file)
    v = ply['vertex']
    # Build new vertex array with aligned coordinates
    vertex_array = np.array(
        [(float(x), float(y), float(z)) for x, y, z in vertices_aligned],
        dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4')]
    )
    vertex_element = PlyElement.describe(vertex_array, 'vertex')

    # Preserve faces if they exist
    if 'face' in ply:
        faces = ply['face'].data
        face_element = PlyElement.describe(faces, 'face')
        PlyData([vertex_element, face_element], text=True).write(output_ply_file)
    else:
        PlyData([vertex_element], text=True).write(output_ply_file)

    print(f"Aligned PLY saved to {output_ply_file}")


def keep_largest_xy_cluster(points, eps_ratio=0.08, min_samples=20):
    if len(points) == 0:
        return points
    xy = points[:, :2]
    span = np.linalg.norm(xy.max(axis=0) - xy.min(axis=0))
    eps = span * eps_ratio
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(xy)
    labels = clustering.labels_
    valid = labels >= 0
    if np.sum(valid) == 0:
        return points
    unique, counts = np.unique(labels[valid], return_counts=True)
    largest_cluster = unique[np.argmax(counts)]
    return points[labels == largest_cluster]


def rotation_matrix_from_vectors(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = np.dot(a, b)
    if np.isclose(c, 1.0):
        return np.eye(3)
    s = np.linalg.norm(v)
    kmat = np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
    ])
    return np.eye(3) + kmat + kmat @ kmat * ((1 - c) / (s ** 2))


def flatten_vertices_align_ground_top(vertices, faces, ransac_threshold=0.002, cluster_bins=200):
    import random

    def fit_plane(p1, p2, p3):
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm == 0:
            return None, None
        normal = normal / norm
        d = -np.dot(normal, p1)
        return normal, d

    def ransac_plane(vertices, iterations=2000, threshold=0.002):
        best_inliers = 0
        best_plane = None
        n = len(vertices)
        for _ in range(iterations):
            ids = random.sample(range(n), 3)
            p1, p2, p3 = vertices[ids]
            normal, d = fit_plane(p1, p2, p3)
            if normal is None:
                continue
            distances = np.abs(vertices @ normal + d)
            inliers = np.sum(distances < threshold)
            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = (normal, d)
        return best_plane

    # Step 1: detect dominant plane
    normal, d = ransac_plane(vertices, threshold=ransac_threshold)

    # Step 2: rotate plane normal to align with Z
    target = np.array([0, 0, 1])
    R = rotation_matrix_from_vectors(normal, target)
    rotated = vertices @ R.T

    # Step 3: make mesh upright
    if np.mean(rotated[:, 2]) < 0:
        rotated[:, 2] *= -1

    # Step 4: detect two main surfaces along Z
    z_vals = rotated[:, 2]
    hist, edges = np.histogram(z_vals, bins=cluster_bins)
    peak_indices = np.argsort(hist)[-2:]
    peak_z = (edges[peak_indices] + edges[peak_indices + 1]) / 2
    floor_z = np.max(peak_z)
    rotated[:, 2] -= floor_z
    rotated[:, 2] *= -1

    # Step 5: PCA on ground surface XY only for canonical orientation
    z_vals_post = rotated[:, 2]
    ground_mask = (z_vals_post >= 4.0) & (z_vals_post <= 6.0)  # ~5mm surface
    ground_pts = rotated[ground_mask, :2]
    if len(ground_pts) < 10:
        ground_pts = rotated[:, :2]  # fallback to full cloud

    centroid = ground_pts.mean(axis=0)
    xy_centered_ground = ground_pts - centroid

    cov = np.cov(xy_centered_ground.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # Sort: largest eigenvalue = principal axis → align to X
    order = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, order]

    # Force canonical sign: principal axis points toward positive X side
    # (whichever end has more points, call that +X)
    principal = eigenvectors[:, 0]
    projections = xy_centered_ground @ principal
    if np.mean(projections > 0) < 0.5:
        eigenvectors[:, 0] *= -1

    # Force canonical sign on secondary axis to maintain right-hand system
    secondary = eigenvectors[:, 1]
    projections2 = xy_centered_ground @ secondary
    if np.mean(projections2 > 0) < 0.5:
        eigenvectors[:, 1] *= -1

    R_pca = eigenvectors.T
    full_centered = rotated[:, :2] - centroid
    rotated[:, :2] = full_centered @ R_pca.T

    return rotated


def minimum_bounding_rectangle(points_2d):
    hull = ConvexHull(points_2d)
    hull_points = points_2d[hull.vertices]
    edges = np.diff(hull_points, axis=0, append=hull_points[:1])
    edge_angles = np.arctan2(edges[:, 1], edges[:, 0])
    unique_angles = np.unique(np.abs(edge_angles) % (np.pi / 2))
    min_area = np.inf
    best_angle = 0
    for angle in unique_angles:
        R = np.array([
            [np.cos(-angle), -np.sin(-angle)],
            [np.sin(-angle), np.cos(-angle)]
        ])
        rot_points = points_2d @ R.T
        min_xy = np.min(rot_points, axis=0)
        max_xy = np.max(rot_points, axis=0)
        area = (max_xy[0] - min_xy[0]) * (max_xy[1] - min_xy[1])
        if area < min_area:
            min_area = area
            best_angle = angle
    return best_angle


def process_ply(num_points,
                ply_file,
                target_height=5.0,
                tolerance=1.0,
                csv_file="output_coordinates.csv",
                plot=True,
                linear=False):

    import random
    random.seed(42)
    np.random.seed(42)

    ply = PlyData.read(ply_file)
    v = ply['vertex']
    vertices = np.vstack((v['x'], v['y'], v['z'])).T
    faces = ply['face'].data

    # STEP 1: Flatten scan
    points = flatten_vertices_align_ground_top(vertices, faces)
    print("Z range:", points[:, 2].min(), points[:, 2].max())
    print("Ground points found:", np.sum(
        (points[:, 2] >= target_height - tolerance) & 
        (points[:, 2] <= target_height + tolerance)
    ))
    print("Ground XY range after flatten:")
    ground_mask = (points[:, 2] >= target_height - tolerance) & (points[:, 2] <= target_height + tolerance)
    gp = points[ground_mask]
    print("  X:", gp[:, 0].min(), gp[:, 0].max())
    print("  Y:", gp[:, 1].min(), gp[:, 1].max())
    print("rotation_angle (deg):", np.degrees(minimum_bounding_rectangle(gp[:, :2])))

    # STEP 2: Detect 5mm surface with outlier removal
    ground_mask = (
        (points[:, 2] >= target_height - tolerance) &
        (points[:, 2] <= target_height + tolerance)
    )
    ground_surface_points = points[ground_mask]
    if ground_surface_points.size == 0:
        raise ValueError(f"No points found near {target_height} mm surface")
    ground_surface_points = keep_largest_xy_cluster(ground_surface_points)
    ground_xy = ground_surface_points[:, :2]

    # STEP 3: Align to consistent corner at (0,0)
    rotation_angle = minimum_bounding_rectangle(ground_xy)
    cos_a = np.cos(-rotation_angle)
    sin_a = np.sin(-rotation_angle)
    R = np.array([
        [cos_a, -sin_a],
        [sin_a,  cos_a]
    ])

    # Apply initial rotation
    rotated_ground_xy = ground_xy @ R.T

    # Canonicalize: ensure longest axis is along X
    dims = rotated_ground_xy.max(axis=0) - rotated_ground_xy.min(axis=0)
    if dims[1] > dims[0]:
        swap = np.array([[0, 1], [-1, 0]], dtype=float)
        R = swap @ R
        rotated_ground_xy = ground_xy @ R.T  # recompute from scratch

    # Detect notch quadrant and rotate until notch is at top-right
    def get_notch_quadrant(xy):
        cx = (xy[:, 0].min() + xy[:, 0].max()) / 2
        cy = (xy[:, 1].min() + xy[:, 1].max()) / 2
        counts = {
            'TR': np.sum((xy[:, 0] >= cx) & (xy[:, 1] >= cy)),
            'TL': np.sum((xy[:, 0] <  cx) & (xy[:, 1] >= cy)),
            'BR': np.sum((xy[:, 0] >= cx) & (xy[:, 1] <  cy)),
            'BL': np.sum((xy[:, 0] <  cx) & (xy[:, 1] <  cy)),
        }
        return min(counts, key=counts.get)

    notch_to_rotations = {'TR': 0, 'TL': 1, 'BR': 3, 'BL': 2}
    rot90_matrices = {
        0: np.eye(2, dtype=float),
        1: np.array([[0, -1], [1,  0]], dtype=float),  # 90° CCW
        2: np.array([[-1, 0], [0, -1]], dtype=float),  # 180°
        3: np.array([[0,  1], [-1, 0]], dtype=float),  # 270° CCW
    }

    notch = get_notch_quadrant(rotated_ground_xy)
    n_rots = notch_to_rotations[notch]
    if n_rots > 0:
        R = rot90_matrices[n_rots] @ R
        rotated_ground_xy = ground_xy @ R.T  # always recompute from original ground_xy

    # Now anchor: green surface min corner goes to (0,0)
    corner_min = rotated_ground_xy.min(axis=0)
    aligned_xy = rotated_ground_xy - corner_min
    aligned_ground_surface = np.hstack([aligned_xy, ground_surface_points[:, 2:3]])

    # STEP 4: Find largest surface above ground
    above_points = points[points[:, 2] > target_height + tolerance]
    bin_size = 1.5
    z_bins = np.round(above_points[:, 2] / bin_size) * bin_size
    unique_z, counts = np.unique(z_bins, return_counts=True)
    largest_z = unique_z[np.argmax(counts)]
    z_lower = largest_z - bin_size
    z_upper = largest_z + bin_size
    largest_surface_points = above_points[(above_points[:, 2] >= z_lower) & (above_points[:, 2] <= z_upper)]
    largest_surface_points = keep_largest_xy_cluster(largest_surface_points)

    # STEP 5: Sample / linear points with strict boundary margin
    margin = 20  # distance from edge to avoid

    # Transform surface points to aligned coordinates
    surface_xy = largest_surface_points[:, :2] @ R.T
    surface_xy_aligned = surface_xy - corner_min  # anchor to corner

    # Compute strict min/max including margin
    min_xy_margin = surface_xy_aligned.min(axis=0) + margin
    max_xy_margin = surface_xy_aligned.max(axis=0) - margin

    if linear:
        # Linear sampling along longest axis inside margin
        longest_axis = 0 if (max_xy_margin[0] - min_xy_margin[0]) > (max_xy_margin[1] - min_xy_margin[1]) else 1
        axis_vals = np.linspace(min_xy_margin[longest_axis], max_xy_margin[longest_axis], num_points)
        other_axis_val = (min_xy_margin[1 - longest_axis] + max_xy_margin[1 - longest_axis]) / 2

        aligned_sampled_points = np.zeros((num_points, 3))
        if longest_axis == 0:
            aligned_sampled_points[:, 0] = axis_vals
            aligned_sampled_points[:, 1] = other_axis_val
        else:
            aligned_sampled_points[:, 1] = axis_vals
            aligned_sampled_points[:, 0] = other_axis_val

        from scipy.spatial import cKDTree
        tree = cKDTree(surface_xy_aligned)
        for i in range(num_points):
            pt = aligned_sampled_points[i, :2]
            dist, idx = tree.query(pt)
            aligned_sampled_points[i, 2] = largest_surface_points[idx, 2]

    else:
        # Random sampling strictly inside margin
        inside_margin_mask = np.all(
            (surface_xy_aligned > min_xy_margin) & (surface_xy_aligned < max_xy_margin),
            axis=1
        )
        filtered_points = largest_surface_points[inside_margin_mask]

        # sample exactly num_points
        if len(filtered_points) <= num_points:
            sampled_points = filtered_points
        else:
            sampled_indices = np.random.choice(len(filtered_points), num_points, replace=False)
            sampled_points = filtered_points[sampled_indices]

        # align sampled points
        rotated_sampled_xy = sampled_points[:, :2] @ R.T
        aligned_xy_sampled = rotated_sampled_xy - corner_min
        aligned_sampled_points = np.hstack([aligned_xy_sampled, sampled_points[:, 2:3]])

    # STEP 6: Align entire PLY cloud using same R and corner_min
    rotated_points_xy = points[:, :2] @ R.T
    points_aligned = np.hstack([rotated_points_xy - corner_min, points[:, 2:3]])

    # Save CSV
    df = pd.DataFrame(
        aligned_sampled_points,
        columns=['X_aligned', 'Y_aligned', 'Z_aligned']
    )
    df.to_csv(csv_file, index=False)

    if plot:
        # 3D plot
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(
            aligned_ground_surface[:, 0],
            aligned_ground_surface[:, 1],
            aligned_ground_surface[:, 2],
            c='green', s=5, alpha=0.8,
            label='Ground Surface'
        )
        ax.scatter(
            aligned_sampled_points[:, 0],
            aligned_sampled_points[:, 1],
            aligned_sampled_points[:, 2],
            c='red', s=20,
            label=f'{len(aligned_sampled_points)} Sampled Points'
        )
        ax.set_xlabel('X (aligned)')
        ax.set_ylabel('Y (aligned)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('Aligned Surfaces')
        ax.legend()
        plt.show()

        # X-Z view
        fig3 = plt.figure(figsize=(10, 6))
        ax3 = fig3.add_subplot(111)
        ax3.scatter(points_aligned[:, 0], points_aligned[:, 2], c='lightgray', s=1, alpha=0.5, label='PLY Cloud')
        ax3.scatter(aligned_ground_surface[:, 0], aligned_ground_surface[:, 2], c='green', s=5, alpha=0.8, label='5mm Surface')
        ax3.scatter(aligned_sampled_points[:, 0], aligned_sampled_points[:, 2], c='red', s=20, label=f'{len(aligned_sampled_points)} Points Above')
        ax3.set_xlabel('X (aligned)')
        ax3.set_ylabel('Z (mm)')
        ax3.set_title('X-Z View of Aligned PLY Cloud and Surfaces')
        ax3.legend()
        ax3.grid(True)
        plt.show()

        # Y-Z view
        fig4 = plt.figure(figsize=(10, 6))
        ax4 = fig4.add_subplot(111)
        ax4.scatter(points_aligned[:, 1], points_aligned[:, 2], c='lightgray', s=1, alpha=0.5, label='PLY Cloud')
        ax4.scatter(aligned_ground_surface[:, 1], aligned_ground_surface[:, 2], c='green', s=5, alpha=0.8, label='5mm Surface')
        ax4.scatter(aligned_sampled_points[:, 1], aligned_sampled_points[:, 2], c='red', s=20, label=f'{len(aligned_sampled_points)} Points Above')
        ax4.set_xlabel('Y (aligned)')
        ax4.set_ylabel('Z (mm)')
        ax4.set_title('Y-Z View of Aligned PLY Cloud and Surfaces')
        ax4.legend()
        ax4.grid(True)
        plt.show()

        # XY top-down view
        fig5 = plt.figure(figsize=(8, 8))
        ax5 = fig5.add_subplot(111)
        ax5.scatter(points_aligned[:, 0], points_aligned[:, 1], c='lightgray', s=1, alpha=0.3, label='PLY Cloud')
        ax5.scatter(aligned_ground_surface[:, 0], aligned_ground_surface[:, 1], c='green', s=5, alpha=0.8, label='5mm Surface')
        ax5.scatter(aligned_sampled_points[:, 0], aligned_sampled_points[:, 1], c='red', s=20, label=f'{len(aligned_sampled_points)} Sampled Points')
        ax5.set_xlabel('X (aligned)')
        ax5.set_ylabel('Y (aligned)')
        ax5.set_title('Top-Down XY View of PLY Cloud, 5mm Surface, and Sampled Points')
        ax5.legend()
        ax5.grid(True)
        ax5.set_aspect('equal', 'box')
        plt.show()

    # Save aligned PLY
    save_aligned_ply(points_aligned, ply_file, output_ply_file="aligned_ply_output.ply")
    return {
        "aligned_sampled_points": aligned_sampled_points,
        "aligned_ground_surface": aligned_ground_surface,
        "rotation_angle_degrees": np.degrees(rotation_angle)
    }
    
    
    