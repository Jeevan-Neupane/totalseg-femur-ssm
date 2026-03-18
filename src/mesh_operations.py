"""
Mesh processing operations.
"""

import numpy as np
from skimage import measure
import trimesh
import pymeshfix


def volume_to_mesh(volume, spacing, threshold=0.5):
    """
    Convert binary segmentation volume to triangle mesh via marching cubes.

    Args:
        volume: 3D array of segmentation mask
        spacing: Voxel spacing (x, y, z) in mm
        threshold: Isosurface threshold value

    Returns:
        trimesh.Trimesh object
    """
    vertices, faces, _, _ = measure.marching_cubes(
        volume,
        level=threshold,
        spacing=tuple(float(s) for s in spacing),
        allow_degenerate=False,
    )
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def keep_largest_component(mesh):
    """
    Keep only the largest connected component, removing stray fragments.

    Args:
        mesh: trimesh.Trimesh object

    Returns:
        trimesh.Trimesh with only largest component
    """
    components = mesh.split(only_watertight=False)
    if len(components) == 1:
        return mesh
    return max(components, key=lambda c: len(c.faces))


def waterproof_mesh(mesh):
    """
    Repair mesh (fill holes, fix normals) to make it watertight.

    Args:
        mesh: trimesh.Trimesh object

    Returns:
        trimesh.Trimesh watertight mesh
    """
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int32)

    fixer = pymeshfix.MeshFix(verts, faces)
    fixer.repair()

    return trimesh.Trimesh(vertices=fixer.points, faces=fixer.faces)


def cut_mesh_along_axis(mesh, long_axis, top_point, cut_length_mm):
    """
    Keep the proximal cut_length_mm of the bone from top_point along long_axis.
    
    The cutting plane is perpendicular to long_axis, ensuring a straight cut
    regardless of bone orientation.

    Args:
        mesh: trimesh.Trimesh object
        long_axis: Unit vector of bone's long axis
        top_point: Point on the proximal tip
        cut_length_mm: Length to keep from proximal end in mm

    Returns:
        trimesh.Trimesh cropped mesh
    """
    proj_top = float(top_point @ long_axis)
    cut_proj = proj_top - cut_length_mm
    plane_origin = long_axis * cut_proj

    # Keep the proximal segment
    cropped = trimesh.intersections.slice_mesh_plane(
        mesh, long_axis, plane_origin
    )
    return cropped
