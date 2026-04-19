import numpy as np
from plyfile import PlyData


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


def dominant_plane_normal(vertices, faces, top_k=5000):

    areas = []
    normals = []

    for f in faces:

        idx = f[0]

        if len(idx) < 3:
            continue

        v0, v1, v2 = vertices[idx[:3]]

        e1 = v1 - v0
        e2 = v2 - v0

        cross = np.cross(e1, e2)

        area = np.linalg.norm(cross) / 2
        if area == 0:
            continue

        normal = cross / np.linalg.norm(cross)

        areas.append(area)
        normals.append(normal)

    areas = np.array(areas)
    normals = np.array(normals)

    idx = np.argsort(areas)[-top_k:]

    weighted = normals[idx] * areas[idx][:, None]

    avg_normal = weighted.sum(axis=0)
    avg_normal /= np.linalg.norm(avg_normal)

    return avg_normal


def flatten_ply_align_ground_top(input_ply, output_ply):

    ply = PlyData.read(input_ply)

    v = ply['vertex']
    vertices = np.vstack((v['x'], v['y'], v['z'])).T

    faces = ply['face'].data

    # Find dominant plane
    normal = dominant_plane_normal(vertices, faces)

    target = np.array([0, 0, 1])
    R = rotation_matrix_from_vectors(normal, target)

    rotated = vertices @ R.T

    # Flip vertically
    rotated[:, 2] = -rotated[:, 2]

    # -----------------------------
    # Align using TOP of ground slab
    # -----------------------------

    z_vals = rotated[:, 2]

    # Bottom portion assumed to be ground slab
    ground_threshold = np.percentile(z_vals, 15)

    ground_points = z_vals[z_vals <= ground_threshold]

    # Top surface of ground slab
    ground_top = np.percentile(ground_points, 95)

    # Shift so ground top becomes z = 0
    rotated[:, 2] -= ground_top

    # Write updated vertices
    v['x'] = rotated[:, 0]
    v['y'] = rotated[:, 1]
    v['z'] = rotated[:, 2]

    ply.write(output_ply)


flatten_ply_align_ground_top(
    "brick_withLmarker.ply",
    "flattened_brick_withLmarker.ply"
)