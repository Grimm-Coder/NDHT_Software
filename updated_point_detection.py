import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

# --- Parameters ---
PLY_FILE = "flattened_brick_withLmarker.ply"  
TARGET_HEIGHT = 5.0    
TOLERANCE = 1.0        
NUM_POINTS = 100
CSV_FILE = "output_coordinates.csv"

# --- Step 1: Read binary little-endian double PLY ---
def read_ply_binary_double(filename):
    with open(filename, 'rb') as f:
        # Read header
        header = []
        while True:
            line = f.readline().decode('ascii').strip()
            header.append(line)
            if line == "end_header":
                break
        
       
        num_vertices = 0
        for line in header:
            if line.startswith("element vertex"):
                num_vertices = int(line.split()[-1])
        
        
        dtype = np.dtype([('x','<f8'), ('y','<f8'), ('z','<f8'),
                          ('nx','<f8'), ('ny','<f8'), ('nz','<f8')])
        vertices = np.fromfile(f, dtype=dtype, count=num_vertices)
        points = np.vstack([vertices['x'], vertices['y'], vertices['z']]).T
    return points

points = read_ply_binary_double(PLY_FILE)

# --- Step 2: Detect 5mm surface ---
ground_mask = (points[:,2] >= TARGET_HEIGHT - TOLERANCE) & (points[:,2] <= TARGET_HEIGHT + TOLERANCE)
ground_surface_points = points[ground_mask]
if ground_surface_points.size == 0:
    raise ValueError(f"No points found near {TARGET_HEIGHT} mm surface")

dims_ground_surface = ground_surface_points.max(axis=0) - ground_surface_points.min(axis=0)
print(f"5mm surface dimensions (X, Y, Z): {dims_ground_surface}")

# --- Step 3: Minimum Bounding Rectangle for alignment ---
def minimum_bounding_rectangle(points_2d):
    hull = ConvexHull(points_2d)
    hull_points = points_2d[hull.vertices]
    
    edges = np.diff(hull_points, axis=0, append=hull_points[:1])
    edge_angles = np.arctan2(edges[:,1], edges[:,0])
    unique_angles = np.unique(np.abs(edge_angles) % (np.pi / 2))
    
    min_area = np.inf
    best_angle = 0
    
    for angle in unique_angles:
        R = np.array([[np.cos(-angle), -np.sin(-angle)],
                      [np.sin(-angle),  np.cos(-angle)]])
        rot_points = points_2d @ R.T
        min_xy = np.min(rot_points, axis=0)
        max_xy = np.max(rot_points, axis=0)
        area = (max_xy[0] - min_xy[0]) * (max_xy[1] - min_xy[1])
        if area < min_area:
            min_area = area
            best_angle = angle
    return best_angle

ground_xy = ground_surface_points[:, :2]
rotation_angle = minimum_bounding_rectangle(ground_xy)
print(f"Rotation angle (degrees): {np.degrees(rotation_angle):.2f}")

cos_a = np.cos(-rotation_angle)
sin_a = np.sin(-rotation_angle)
R = np.array([[cos_a, -sin_a],
              [sin_a,  cos_a]])

ground_xy_centered = ground_xy - ground_xy.min(axis=0)  
aligned_xy = ground_xy_centered @ R.T
aligned_ground_surface = np.hstack([aligned_xy, ground_surface_points[:, 2:3]])

# --- Step 4: Find largest surface above ---
above_points = points[points[:,2] > TARGET_HEIGHT + TOLERANCE]
z_bins = np.round(above_points[:,2], 1)
unique_z, counts = np.unique(z_bins, return_counts=True)
largest_z = unique_z[np.argmax(counts)]
largest_surface_points = above_points[z_bins == largest_z]
dims_largest_surface = largest_surface_points.max(axis=0) - largest_surface_points.min(axis=0)
print(f"Largest surface above dimensions (X, Y, Z): {dims_largest_surface}")

if len(largest_surface_points) < NUM_POINTS:
    sampled_points = largest_surface_points
else:
    sampled_indices = np.random.choice(len(largest_surface_points), NUM_POINTS, replace=False)
    sampled_points = largest_surface_points[sampled_indices]

sampled_xy_centered = sampled_points[:, :2] - ground_xy.min(axis=0)
aligned_sampled_xy = sampled_xy_centered @ R.T
aligned_sampled_points = np.hstack([aligned_sampled_xy, sampled_points[:, 2:3]])

# --- Step 5: Translate so surface min X/Y = 0 ---
xmin = aligned_ground_surface[:,0].min()
ymin = aligned_ground_surface[:,1].min()
translation = np.array([-xmin, -ymin])

aligned_ground_surface[:, :2] += translation
aligned_sampled_points[:, :2] += translation

points_centered = points.copy()
points_centered[:, :2] -= ground_xy.min(axis=0)
points_aligned_xy = points_centered[:, :2] @ R.T
points_aligned = np.hstack([points_aligned_xy, points_centered[:, 2:3]])
points_aligned[:, :2] += translation

# --- Step 6: Save CSV with only sampled points and 5mm surface points ---
original_data = sampled_points  
aligned_data = aligned_sampled_points  



df = pd.DataFrame(np.hstack([aligned_data]), 
                  columns=['X_aligned','Y_aligned','Z_aligned'])
df.to_csv(CSV_FILE, index=False)
print(f"CSV saved as '{CSV_FILE}'")

# --- Step 7: Plot fully aligned PLY cloud ---
fig = plt.figure(figsize=(10,8))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(points_aligned[:,0], points_aligned[:,1], points_aligned[:,2],
           c='lightgray', s=1, alpha=0.5, label='Aligned & Translated PLY Cloud')
ax.scatter(aligned_ground_surface[:,0], aligned_ground_surface[:,1], aligned_ground_surface[:,2],
           c='green', s=5, alpha=0.8, label='Aligned 5mm Surface')
ax.scatter(aligned_sampled_points[:,0], aligned_sampled_points[:,1], aligned_sampled_points[:,2],
           c='red', s=20, label=f'{NUM_POINTS} Sampled Points Above')
ax.set_xlabel('X (aligned)')
ax.set_ylabel('Y (aligned)')
ax.set_zlabel('Z (mm)')
ax.set_title('Fully Aligned and Translated PLY Cloud with Surfaces')
ax.legend()
plt.show()

# --- Step 8: Plot aligned 5mm surface with bounding rectangle ---
fig2 = plt.figure(figsize=(8,6))
ax2 = fig2.add_subplot(111, projection='3d')
ax2.scatter(aligned_ground_surface[:,0], aligned_ground_surface[:,1], aligned_ground_surface[:,2],
            c='green', s=5, alpha=0.8, label='Aligned 5mm Surface')
x_min, x_max = aligned_ground_surface[:,0].min(), aligned_ground_surface[:,0].max()
y_min, y_max = aligned_ground_surface[:,1].min(), aligned_ground_surface[:,1].max()
z_mean = aligned_ground_surface[:,2].mean()
rect_3d = np.array([
    [x_min, y_min, z_mean],
    [x_max, y_min, z_mean],
    [x_max, y_max, z_mean],
    [x_min, y_max, z_mean],
    [x_min, y_min, z_mean],
])
ax2.plot(rect_3d[:,0], rect_3d[:,1], rect_3d[:,2], c='black', lw=2, label='Bounding Rectangle')
ax2.set_xlabel('X (aligned)')
ax2.set_ylabel('Y (aligned)')
ax2.set_zlabel('Z (mm)')
ax2.set_title('Aligned 5mm Surface Only with Bounding Rectangle')
ax2.legend()
plt.show()

# --- Step 9: X-Z view ---
fig3 = plt.figure(figsize=(10,6))
ax3 = fig3.add_subplot(111)
ax3.scatter(points_aligned[:,0], points_aligned[:,2], c='lightgray', s=1, alpha=0.5, label='PLY Cloud')
ax3.scatter(aligned_ground_surface[:,0], aligned_ground_surface[:,2], c='green', s=5, alpha=0.8, label='5mm Surface')
ax3.scatter(aligned_sampled_points[:,0], aligned_sampled_points[:,2], c='red', s=20, label=f'{NUM_POINTS} Points Above')
ax3.set_xlabel('X (aligned)')
ax3.set_ylabel('Z (mm)')
ax3.set_title('X-Z View of Aligned PLY Cloud and Surfaces')
ax3.legend()
ax3.grid(True)
plt.show()

# --- Step 10: Y-Z view ---
fig4 = plt.figure(figsize=(10,6))
ax4 = fig4.add_subplot(111)
ax4.scatter(points_aligned[:,1], points_aligned[:,2], c='lightgray', s=1, alpha=0.5, label='PLY Cloud')
ax4.scatter(aligned_ground_surface[:,1], aligned_ground_surface[:,2], c='green', s=5, alpha=0.8, label='5mm Surface')
ax4.scatter(aligned_sampled_points[:,1], aligned_sampled_points[:,2], c='red', s=20, label=f'{NUM_POINTS} Points Above')
ax4.set_xlabel('Y (aligned)')
ax4.set_ylabel('Z (mm)')
ax4.set_title('Y-Z View of Aligned PLY Cloud and Surfaces')
ax4.legend()
ax4.grid(True)
plt.show()