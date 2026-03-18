"""
PCA-based alignment and axis computation.
"""

import numpy as np
import trimesh


def compute_mesh_long_axis(mesh):
    """
    Use PCA on mesh vertices to find the femur's long axis.
    
    The axis is oriented toward the WIDER end (femoral head/trochanteric region)
    so that downstream functions know which end is proximal.

    Args:
        mesh: trimesh.Trimesh object

    Returns:
        tuple: (long_axis, top_point)
            - long_axis: unit vector pointing toward head
            - top_point: point on the proximal tip
    """
    verts = mesh.vertices
    centroid = verts.mean(axis=0)
    _, _, Vt = np.linalg.svd(verts - centroid, full_matrices=False)
    axis = Vt[0]  # First principal component

    # Project all vertices onto the axis
    proj = verts @ axis
    end_a = verts[proj.argmax()]
    end_b = verts[proj.argmin()]

    def perp_spread(tip_point):
        """Calculate perpendicular spread near a tip."""
        tip_proj = float(tip_point @ axis)
        bone_len = float(proj.max() - proj.min())
        mask = np.abs(verts @ axis - tip_proj) < 0.15 * bone_len
        pts = verts[mask]
        if len(pts) < 3:
            return 0.0
        perp = pts - np.outer(pts @ axis, axis)
        return float(np.sqrt(np.mean(np.sum((perp - perp.mean(0)) ** 2, axis=1))))

    # Flip axis to point toward wider (proximal) end
    if perp_spread(end_b) > perp_spread(end_a):
        axis = -axis

    top_point = verts[(verts @ axis).argmax()]
    return axis, top_point


def align_mesh_to_canonical_axes(mesh, long_axis=None):
    """
    Rigidly align mesh to canonical coordinate frame.

    Canonical frame:
      +Z = anatomical long axis (femoral head at top)
      +X = second principal component (widest transverse direction)
      +Y = X × Z (right-handed completion)
      origin = mesh centroid

    Args:
        mesh: trimesh.Trimesh object
        long_axis: Pre-computed long axis (optional). If provided, uses this
                   instead of recomputing from the mesh.

    Returns:
        trimesh.Trimesh aligned mesh
    """
    verts = np.array(mesh.vertices, dtype=np.float64)
    centroid = verts.mean(axis=0)
    verts_c = verts - centroid

    # Determine pc1 (long axis, oriented toward head)
    if long_axis is not None:
        pc1 = np.asarray(long_axis, dtype=np.float64).copy()
        pc1 /= np.linalg.norm(pc1)
    else:
        _, _, Vt = np.linalg.svd(verts_c, full_matrices=False)
        pc1 = Vt[0].copy()

        # Orient toward wider end
        proj = verts_c @ pc1
        end_a = verts_c[proj.argmax()]
        end_b = verts_c[proj.argmin()]

        def _perp_spread(tip_pt):
            tip_p = float(tip_pt @ pc1)
            blen = float(proj.max() - proj.min())
            mask = np.abs(verts_c @ pc1 - tip_p) < 0.15 * blen
            pts = verts_c[mask]
            if len(pts) < 3:
                return 0.0
            perp = pts - np.outer(pts @ pc1, pc1)
            return float(np.sqrt(np.mean(np.sum((perp - perp.mean(0)) ** 2, axis=1))))

        if _perp_spread(end_b) > _perp_spread(end_a):
            pc1 = -pc1

    # Ensure pc1 points toward +Z in original LPS frame
    proj = verts @ pc1
    proximal_z = verts[proj.argmax(), 2]
    distal_z = verts[proj.argmin(), 2]
    if proximal_z < distal_z:
        pc1 = -pc1

    # Determine pc2 (second principal axis) via Gram-Schmidt
    _, _, Vt = np.linalg.svd(verts_c, full_matrices=False)
    pc2_raw = Vt[1].copy()
    pc2 = pc2_raw - np.dot(pc2_raw, pc1) * pc1
    if np.linalg.norm(pc2) < 1e-6:
        pc2_raw = Vt[2].copy()
        pc2 = pc2_raw - np.dot(pc2_raw, pc1) * pc1
    pc2 /= np.linalg.norm(pc2)

    # Fix pc2 sign (deterministic, scanner-independent)
    if np.dot(pc2, [1, 0, 0]) < 0:
        pc2 = -pc2

    # Right-handed pc3: pc1 × pc2 = pc3
    pc3 = np.cross(pc1, pc2)
    pc3 /= np.linalg.norm(pc3)

    # Rotation matrix: pc2 -> +X, pc3 -> +Y, pc1 -> +Z
    R = np.array([pc2, pc3, pc1], dtype=np.float64)

    # Apply rotation
    aligned_verts = verts_c @ R.T

    return trimesh.Trimesh(vertices=aligned_verts, faces=mesh.faces, process=False)
