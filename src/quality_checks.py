"""
Quality check functions for femur segmentation validation.
"""

import numpy as np


def head_border_check(volume, threshold=0.5, min_border_voxels=500):
    """
    Check whether the femoral head is clipped at the superior boundary.

    After LPS reorientation, axis 2 runs Inferior → Superior, so the
    femoral head sits at the superior end (last slice along axis 2).

    Args:
        volume: 3D array in LPS orientation
        threshold: Voxels >= threshold are considered bone
        min_border_voxels: Minimum voxels on superior face to count as clipped

    Returns:
        tuple: (ok: bool, reason: str)
    """
    bone = volume >= threshold
    sup_face = bone[:, :, -1]  # Superior face in LPS
    count = int(sup_face.sum())
    
    if count >= min_border_voxels:
        return False, f"femoral head clipped at superior boundary ({count} voxels)"
    return True, "ok"


def mesh_length_check(mesh, min_length_mm):
    """
    Measure bone's anatomical length using PCA and reject if too short.

    Args:
        mesh: trimesh.Trimesh object
        min_length_mm: Minimum required length in mm

    Returns:
        tuple: (ok: bool, reason: str, bone_length_mm: float)
    """
    if len(mesh.vertices) < 100:
        return False, f"mesh too small ({len(mesh.vertices)} vertices)", 0.0

    verts = mesh.vertices
    centroid = verts.mean(axis=0)
    _, _, Vt = np.linalg.svd(verts - centroid, full_matrices=False)
    proj = verts @ Vt[0]
    bone_length = float(proj.max() - proj.min())

    if bone_length < min_length_mm:
        return False, f"bone too short ({bone_length:.1f} mm < {min_length_mm:.0f} mm)", bone_length

    return True, "ok", bone_length


def head_check(mesh, long_axis):
    """
    Detect shaft-only bones (missing femoral head) by analyzing shape profile.

    Anatomical signature of a proximal femur:
        - Tip (top 10%): femoral head sphere -> NARROW
        - Trochanteric region (10-30%): flares out -> WIDER
        - Shaft: roughly uniform width

    Args:
        mesh: trimesh.Trimesh object
        long_axis: Unit vector of bone's long axis

    Returns:
        tuple: (ok: bool, reason: str)
    """
    verts = mesh.vertices
    proj = verts @ long_axis
    p_max = proj.max()
    p_min = proj.min()
    bone_len = p_max - p_min
    
    if bone_len < 1.0:
        return False, "degenerate mesh (near-zero length)"

    def perp_spread(mask):
        """RMS spread perpendicular to long_axis for selected vertices."""
        pts = verts[mask]
        if len(pts) < 3:
            return 0.0
        perp = pts - np.outer(pts @ long_axis, long_axis)
        return float(np.sqrt(np.mean(np.sum((perp - perp.mean(0)) ** 2, axis=1))))

    # Top 10% = femoral head sphere
    tip_mask = proj > (p_max - 0.10 * bone_len)
    tip_spread = perp_spread(tip_mask)

    # Top 50% in 10%-bands
    band_spreads = []
    for i in range(5):
        lo = p_max - (i + 1) * 0.10 * bone_len
        hi = p_max - i * 0.10 * bone_len
        band_spreads.append(perp_spread((proj >= lo) & (proj <= hi)))
    max_top_spread = max(band_spreads) if band_spreads else 0.0

    if max_top_spread < 1.0:
        return False, "mesh too small to evaluate"

    tip_ratio = tip_spread / max_top_spread
    MAX_TIP_RATIO = 0.85
    
    if tip_ratio >= MAX_TIP_RATIO:
        return False, f"femoral head missing (tip/max-top ratio {tip_ratio:.2f} >= {MAX_TIP_RATIO})"
    
    return True, "ok"
