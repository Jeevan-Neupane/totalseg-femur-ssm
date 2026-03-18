"""
Main processing pipeline for femur mesh generation.
"""

import nibabel as nib
from .nifti_io import load_nifti, reorient_to_lps
from .quality_checks import head_border_check, mesh_length_check, head_check
from .mesh_operations import volume_to_mesh, keep_largest_component, waterproof_mesh, cut_mesh_along_axis
from .pca_alignment import compute_mesh_long_axis, align_mesh_to_canonical_axes


def process_nifti_to_mesh(input_path, output_path, threshold=0.5,
                          crop_length_mm=90.0, skip_bad=True, verbose=True,
                          align=True, min_border_voxels=500):
    """
    End-to-end pipeline for converting NIfTI segmentation to watertight mesh.

    Pipeline steps:
        1. Load NIfTI
        2. Reorient to LPS
        3. Head border check
        4. Marching cubes
        5. Keep largest component
        6. Length check
        7. Compute long axis (PCA) + head check
        8. Cut perpendicular to axis
        9. Waterproof
        10. Canonical alignment
        11. Save

    Args:
        input_path: Path to .nii.gz segmentation mask
        output_path: Path to write .obj mesh
        threshold: Marching cubes iso-value (default: 0.5)
        crop_length_mm: Length to keep from proximal end in mm (default: 90)
        skip_bad: If True, run quality checks and skip bad bones (default: True)
        verbose: Print progress messages (default: True)
        align: Apply canonical alignment (default: True)
        min_border_voxels: Min voxels on border to count as clipped (default: 500)

    Returns:
        tuple: (mesh, reason)
            - mesh: trimesh.Trimesh if successful, None if skipped
            - reason: Skip reason string if skipped, None if successful
    """
    def log(msg):
        if verbose:
            print(msg)

    log(f"\n{'='*60}")
    log(f"Processing: {input_path}")

    # 1. Load NIfTI
    log("  [1/10] Loading NIfTI ...")
    volume, nifti_img = load_nifti(input_path)
    log(f"          shape={volume.shape}  "
        f"spacing={tuple(float(s) for s in nifti_img.header.get_zooms()[:3])}")
    log(f"          original orientation: {nib.aff2axcodes(nifti_img.affine)}")

    # 2. Reorient to LPS
    log("  [2/10] Reorienting to LPS ...")
    volume, spacing, ornt = reorient_to_lps(nifti_img)
    log(f"          shape={volume.shape}  spacing={spacing}  axes={ornt}")

    # 3. Head border check
    if skip_bad:
        log("  [3/10] Head border check ...")
        ok, reason = head_border_check(
            volume, threshold=threshold, min_border_voxels=min_border_voxels)
        if not ok:
            log(f"          REJECTED: {reason}")
            return None, reason
        log(f"          head not clipped — OK")

    # 4. Marching cubes
    log("  [4/10] Marching cubes ...")
    mesh = volume_to_mesh(volume, spacing, threshold=threshold)
    log(f"          {len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    # 5. Keep largest component
    log("  [5/10] Removing stray fragments ...")
    mesh = keep_largest_component(mesh)
    log(f"          {len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    # 6. Length check
    if skip_bad and crop_length_mm is not None:
        log("  [6/10] Length check ...")
        ok, reason, bone_length = mesh_length_check(mesh, crop_length_mm - 0.5)
        if not ok:
            log(f"          REJECTED: {reason}")
            return None, reason
        log(f"          {bone_length:.1f} mm >= {crop_length_mm:.0f} mm — OK")

    # 7. Compute long axis + head check
    log("  [7/10] Computing long axis (PCA) ...")
    long_axis, top_point = compute_mesh_long_axis(mesh)

    if skip_bad:
        log("  [7/10] Head check ...")
        ok, reason = head_check(mesh, long_axis)
        if not ok:
            log(f"          REJECTED: {reason}")
            return None, reason
        log(f"          passed")

    # 8. Cut perpendicular to long axis
    if crop_length_mm is not None:
        proj = mesh.vertices @ long_axis
        bone_len = float(proj.max() - proj.min())
        if bone_len > crop_length_mm:
            log(f"  [8/10] Cutting at {crop_length_mm} mm from proximal end "
                f"(bone {bone_len:.1f} mm) ...")
            mesh = cut_mesh_along_axis(mesh, long_axis, top_point, crop_length_mm)
            log(f"          {len(mesh.vertices)} verts, {len(mesh.faces)} faces after cut")
        else:
            log(f"  [8/10] No cut needed (bone {bone_len:.1f} mm <= {crop_length_mm:.0f} mm)")

    # 9. Waterproof
    log("  [9/10] Waterproofing ...")
    mesh = waterproof_mesh(mesh)
    log(f"          watertight={mesh.is_watertight}, "
        f"{len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    # 10. Canonical alignment
    if align:
        log("  [10/10] Aligning to canonical axes ...")
        mesh = align_mesh_to_canonical_axes(mesh, long_axis=long_axis)
        log(f"           centroid~{mesh.vertices.mean(axis=0).round(2)}, "
            f"Z-extent [{mesh.vertices[:,2].min():.1f}, {mesh.vertices[:,2].max():.1f}] mm")
    else:
        log("  [10/10] Alignment skipped (align=False)")

    # Save
    mesh.export(output_path)
    log(f"  Saved: {output_path}")

    return mesh, None
