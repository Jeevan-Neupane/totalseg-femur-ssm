"""
Femur mesh processing utilities.

Pipeline:
  NIfTI -> Reorient to LPS -> Head Border Check -> Mesh -> Largest Component
       -> Length Check -> Head Check
       -> Straight Cut (perp. to PCA long axis)
       -> Waterproof
       -> Canonical Alignment (PC1->+Z head-up, PC2->+X, PC3->+Y)
       -> Save

All input volumes are first reoriented to LPS (Left-Posterior-Superior)
so that the physical axes are consistent across all scans regardless
of scanner convention.

All output meshes share the same coordinate frame:
  +Z  = anatomical proximal direction (femoral head at top)
  +X  = widest transverse direction
  +Y  = cross product (right-handed)
  origin = mesh centroid
"""

import nibabel as nib
import numpy as np
from skimage import measure
import trimesh
import pymeshfix


# ---------------------------------------------------------------------------
# 1. Loading
# ---------------------------------------------------------------------------

def load_nifti(file_path):
    """Load a NIfTI file and return (volume, nifti_image)."""
    nifti_img = nib.load(file_path)
    data = nifti_img.get_fdata()
    return data, nifti_img


# ---------------------------------------------------------------------------
# 2. Reorient volume to LPS (Left-Posterior-Superior)
# ---------------------------------------------------------------------------

def reorient_to_lps(nifti_img):
    """
    Reorient a NIfTI image so its voxel axes correspond to LPS directions.

    CT scans arrive in many orientation conventions (RAS, LPS, LAS, etc.)
    depending on the scanner, the DICOM-to-NIfTI converter, and the patient
    position.  Reorienting to a single standard — here LPS
    (Left-Posterior-Superior) — ensures that array axis 0 always runs
    Left->Right, axis 1 runs Posterior->Anterior, and axis 2 runs
    Inferior->Superior consistently.  This removes the "random orientation"
    problem before any downstream processing.

    The function uses nibabel's ``as_closest_canonical()`` to first move
    the volume into RAS+ (the nibabel canonical), then flips axes 0 and 1
    to reach LPS+.

    Parameters
    ----------
    nifti_img : nibabel.nifti1.Nifti1Image
        The loaded NIfTI image (header + data).

    Returns
    -------
    (volume, spacing, ornt_code)
        volume  : ndarray — the reoriented 3-D array
        spacing : tuple of 3 floats — voxel sizes in mm after reorientation
        ornt_code : str — the nibabel axcodes of the result (should be
                    ('L','P','S'))
    """
    # Step 1: bring to RAS+ (nibabel canonical orientation)
    canonical = nib.as_closest_canonical(nifti_img)

    # Step 2: RAS+ -> LPS+  (flip first two axes: R->L, A->P; S stays)
    ras_data = canonical.get_fdata()
    lps_data = ras_data[::-1, ::-1, :].copy()

    # Build the new affine: flip the first two columns of the canonical affine
    lps_affine = canonical.affine.copy()
    # Flip axis 0 (R->L): negate column 0, shift origin
    lps_affine[:3, 0] = -lps_affine[:3, 0]
    lps_affine[:3, 3] += canonical.affine[:3, 0] * (ras_data.shape[0] - 1)
    # Flip axis 1 (A->P): negate column 1, shift origin
    lps_affine[:3, 1] = -lps_affine[:3, 1]
    lps_affine[:3, 3] += canonical.affine[:3, 1] * (ras_data.shape[1] - 1)

    lps_img = nib.Nifti1Image(lps_data, lps_affine, canonical.header)
    spacing = tuple(float(s) for s in lps_img.header.get_zooms()[:3])

    # Verify orientation code
    ornt = nib.aff2axcodes(lps_affine)

    return lps_data, spacing, ornt


# ---------------------------------------------------------------------------
# 3. Head border check — reject only if the proximal (head) end is clipped
# ---------------------------------------------------------------------------

def head_border_check(volume, threshold=0.5, min_border_voxels=500):
    """
    Check whether the femoral head is clipped at the superior boundary.

    After LPS reorientation axis 2 runs Inferior → Superior, so the
    femoral head sits at the **superior end** (last slice along axis 2).
    Only that face is inspected — bone touching the inferior, left/right,
    or anterior/posterior boundaries is acceptable because those regions
    are either the distal shaft (which will be cropped anyway) or lateral
    surfaces that do not affect the head shape.

    Parameters
    ----------
    volume : ndarray, shape (D, H, W)
        The binary (or soft) segmentation mask **in LPS orientation**.
    threshold : float
        Voxels with value >= threshold are considered bone.
    min_border_voxels : int
        Minimum number of bone voxels on the superior face to count as
        clipped.  Small counts (< min_border_voxels) are treated as noise.

    Returns
    -------
    (ok : bool, reason : str)
        ok is True when the head is not clipped.
    """
    bone = volume >= threshold
    sup_face = bone[:, :, -1]          # axis2_max = superior face in LPS
    count = int(sup_face.sum())
    if count >= min_border_voxels:
        return False, f"femoral head clipped at superior boundary ({count} voxels)"
    return True, "ok"


# ---------------------------------------------------------------------------
# 4. Volume → Mesh  (marching cubes)
# ---------------------------------------------------------------------------

def volume_to_mesh(volume, spacing, threshold=0.5):
    """
    Convert a binary segmentation volume to a triangle mesh via marching cubes.

    Returns:
        trimesh.Trimesh
    """
    vertices, faces, _, _ = measure.marching_cubes(
        volume,
        level=threshold,
        spacing=tuple(float(s) for s in spacing),
        allow_degenerate=False,
    )
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


# ---------------------------------------------------------------------------
# 5. Keep only the largest connected component (removes stray fragments)
# ---------------------------------------------------------------------------

def keep_largest_component(mesh):
    """
    Split the mesh into connected components and return only the largest one.
    Discards small stray fragments (patella, acetabulum, etc.) included in
    the segmentation mask.
    """
    components = mesh.split(only_watertight=False)
    if len(components) == 1:
        return mesh
    return max(components, key=lambda c: len(c.faces))


# ---------------------------------------------------------------------------
# 6. Compute the bone's anatomical long axis from mesh vertices
# ---------------------------------------------------------------------------

def compute_mesh_long_axis(mesh):
    """
    PCA on mesh vertices to find the femur's long axis.  The axis is oriented
    toward the WIDER end (femoral head / trochanteric region) so that
    head_check and cut_mesh_along_axis always know which end is proximal.

    Returns:
        long_axis (ndarray shape (3,))  - unit vector pointing toward head
        top_point (ndarray shape (3,))  - point on the proximal tip
    """
    verts = mesh.vertices
    centroid = verts.mean(axis=0)
    _, _, Vt = np.linalg.svd(verts - centroid, full_matrices=False)
    axis = Vt[0]  # first principal component (unit vector)

    # Project all vertices onto the axis and find the two endpoints
    proj = verts @ axis
    end_a = verts[proj.argmax()]   # one tip
    end_b = verts[proj.argmin()]   # other tip

    # The proximal (head) end is WIDER — higher RMS spread perpendicular to axis
    def perp_spread(tip_point):
        # vertices within 15% of bone length from that tip
        tip_proj = float(tip_point @ axis)
        bone_len = float(proj.max() - proj.min())
        mask = np.abs(verts @ axis - tip_proj) < 0.15 * bone_len
        pts = verts[mask]
        if len(pts) < 3:
            return 0.0
        # component perpendicular to axis
        perp = pts - np.outer(pts @ axis, axis)
        return float(np.sqrt(np.mean(np.sum((perp - perp.mean(0)) ** 2, axis=1))))

    if perp_spread(end_b) > perp_spread(end_a):
        axis = -axis   # flip so it points toward the wider (proximal) end

    top_point = verts[(verts @ axis).argmax()]
    return axis, top_point


# ---------------------------------------------------------------------------
# 7a. Femoral head quality check (works on unaligned mesh)
# ---------------------------------------------------------------------------

def head_check(mesh, long_axis):
    """
    Detect shaft-only bones (missing femoral head) by looking at the shape
    profile along the long axis.

    Anatomical signature of a proximal femur:
        - The very tip (top 10%) is the femoral head sphere -> NARROW
        - The trochanteric region (10-30% from top) flares out -> WIDER
        - Then the shaft maintains roughly uniform width

    A shaft-only bone has near-uniform width from tip to mid, so
    tip_spread / max_spread_top_50% is HIGH (~0.85-1.0).
    A proper proximal femur has a narrow tip, so the ratio is LOW (~0.4-0.75).

    Returns:
        (ok: bool, reason: str)
    """
    verts = mesh.vertices
    proj = verts @ long_axis   # scalar projection of each vertex onto long axis
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

    tip_mask = proj > (p_max - 0.10 * bone_len)   # top 10% = femoral head sphere
    tip_spread = perp_spread(tip_mask)

    band_spreads = []
    for i in range(5):  # top 50% in 10%-bands
        lo = p_max - (i + 1) * 0.10 * bone_len
        hi = p_max - i * 0.10 * bone_len
        band_spreads.append(perp_spread((proj >= lo) & (proj <= hi)))
    max_top_spread = max(band_spreads) if band_spreads else 0.0

    if max_top_spread < 1.0:
        return False, "mesh too small to evaluate"

    tip_ratio = tip_spread / max_top_spread
    MAX_TIP_RATIO = 0.85   # above this -> shaft-only
    if tip_ratio >= MAX_TIP_RATIO:
        return False, (f"femoral head missing "
                       f"(tip/max-top ratio {tip_ratio:.2f} >= {MAX_TIP_RATIO})")
    return True, "ok"


# ---------------------------------------------------------------------------
# 7b. Cut perpendicular to the long axis (no mesh rotation needed)
# ---------------------------------------------------------------------------

def cut_mesh_along_axis(mesh, long_axis, top_point, cut_length_mm):
    """
    Keep the proximal *cut_length_mm* of the bone, measured from *top_point*
    along *long_axis*.  The cutting plane is perpendicular to *long_axis*, so
    the cut face is always perfectly straight regardless of bone orientation.

    No mesh rotation is performed.

    Returns:
        trimesh.Trimesh
    """
    # Project all vertices; the proximal end has the highest projection
    proj_top = float(top_point @ long_axis)
    cut_proj = proj_top - cut_length_mm          # cut plane position along axis
    plane_origin = long_axis * cut_proj           # a point on the cut plane

    # Keep the side where vertex_proj >= cut_proj (i.e. the proximal segment)
    cropped = trimesh.intersections.slice_mesh_plane(
        mesh, long_axis, plane_origin
    )
    return cropped


# ---------------------------------------------------------------------------
# 8. Waterproofing (hole-filling) — applied AFTER cutting
# ---------------------------------------------------------------------------

def waterproof_mesh(mesh):
    """
    Repair the mesh (fill holes from the cut, fix normals, etc.)
    using pymeshfix so the result is watertight.

    Returns:
        trimesh.Trimesh
    """
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int32)

    fixer = pymeshfix.MeshFix(verts, faces)
    fixer.repair()

    return trimesh.Trimesh(vertices=fixer.points, faces=fixer.faces)


# ---------------------------------------------------------------------------
# 9. Canonical alignment — rotate every mesh to the same coordinate frame
# ---------------------------------------------------------------------------

def align_mesh_to_canonical_axes(mesh, long_axis=None):
    """
    Rigidly align a mesh to a canonical coordinate frame so that every bone
    processed by this pipeline ends up facing the same direction.

    Canonical frame
    ---------------
      +Z  = anatomical long axis, femoral head (proximal end) at the top
      +X  = second principal component (widest transverse direction)
      +Y  = X x Z — right-handed completion
      origin = mesh centroid

    Parameters
    ----------
    mesh : trimesh.Trimesh
        The (already cropped + waterproofed) mesh to align.
    long_axis : array-like, shape (3,), optional
        The unit vector of the bone's long axis already correctly oriented
        toward the proximal (head) end.  When provided — as computed by
        ``compute_mesh_long_axis`` on the *full uncut* bone in the pipeline —
        the function skips re-running PCA on the cut mesh, which avoids
        being confused by the large flat cut face at the distal end.
        If None, the axis is recomputed from the mesh itself (suitable when
        calling this function in isolation on a full-length bone).

    Why pass long_axis from outside?
    ---------------------------------
    After cutting to 100 mm, the distal end has a large flat circular face.
    The vertices on that ring have significant perpendicular spread, so the
    heuristic that picks the "wider end" may incorrectly pick the cut end
    instead of the femoral head.  Using the axis computed *before* cutting
    (when the full shaft/neck/head contrast is visible) is always reliable.

    Returns
    -------
    trimesh.Trimesh  centred at the origin, long axis along +Z.
    """
    verts    = np.array(mesh.vertices, dtype=np.float64)
    centroid = verts.mean(axis=0)
    verts_c  = verts - centroid                       # centre at origin

    # -- Determine pc1 (long axis, oriented toward head) ----------------------
    if long_axis is not None:
        # Use the pre-computed, correctly-oriented axis from the full bone.
        pc1 = np.asarray(long_axis, dtype=np.float64).copy()
        pc1 /= np.linalg.norm(pc1)                   # ensure unit length
    else:
        # Recompute everything from the mesh (may be unreliable on cut mesh).
        _, _, Vt = np.linalg.svd(verts_c, full_matrices=False)
        pc1 = Vt[0].copy()

        # Orient pc1 toward the wider (proximal) end via perp-spread heuristic
        proj = verts_c @ pc1
        end_a = verts_c[proj.argmax()]
        end_b = verts_c[proj.argmin()]

        def _perp_spread(tip_pt):
            tip_p = float(tip_pt @ pc1)
            blen  = float(proj.max() - proj.min())
            mask  = np.abs(verts_c @ pc1 - tip_p) < 0.15 * blen
            pts   = verts_c[mask]
            if len(pts) < 3:
                return 0.0
            perp = pts - np.outer(pts @ pc1, pc1)
            return float(np.sqrt(np.mean(np.sum((perp - perp.mean(0)) ** 2, axis=1))))

        if _perp_spread(end_b) > _perp_spread(end_a):
            pc1 = -pc1

    # Ensure pc1 points toward +Z in the original LPS frame's Z direction
    proj = verts @ pc1
    proximal_z = verts[proj.argmax(), 2]
    distal_z = verts[proj.argmin(), 2]
    if proximal_z < distal_z:
        pc1 = -pc1

    # -- Determine pc2 (second principal axis) --------------------------------
    # Gram-Schmidt: remove any pc1 component from the other PCA axes
    _, _, Vt = np.linalg.svd(verts_c, full_matrices=False)
    pc2_raw = Vt[1].copy()
    pc2 = pc2_raw - np.dot(pc2_raw, pc1) * pc1
    if np.linalg.norm(pc2) < 1e-6:  # if pc1 and pc2 were collinear
        pc2_raw = Vt[2].copy()
        pc2 = pc2_raw - np.dot(pc2_raw, pc1) * pc1
    pc2 /= np.linalg.norm(pc2)

    # -- Fix pc2 sign (deterministic, scanner-independent) -------------------
    # Use the original LPS X-axis to break symmetry.
    if np.dot(pc2, [1, 0, 0]) < 0:
        pc2 = -pc2

    # -- Right-handed pc3: pc1 x pc2 = pc3 (Z x X = Y) -----------------------
    pc3 = np.cross(pc1, pc2)
    pc3 /= np.linalg.norm(pc3)

    # -- Rotation matrix: rows = canonical basis expressed in original frame --
    #    pc2 -> +X, pc3 -> +Y, pc1 -> +Z
    R = np.array([pc2, pc3, pc1], dtype=np.float64)

    # -- Apply rotation (row-vector convention: x_aligned = verts_c @ R.T) ----
    aligned_verts = verts_c @ R.T

    return trimesh.Trimesh(vertices=aligned_verts, faces=mesh.faces, process=False)


# ---------------------------------------------------------------------------
# 6b. Quality checks  — reject incomplete / bad segmentations
# ---------------------------------------------------------------------------

def mesh_length_check(mesh, min_length_mm):
    """
    Measure the bone's anatomical length from the mesh vertices using PCA,
    and reject if shorter than min_length_mm.

    Returns:
        (ok: bool, reason: str, bone_length_mm: float)
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


# ---------------------------------------------------------------------------
# 10. Full pipeline
# ---------------------------------------------------------------------------

def process_nifti_to_mesh(input_path, output_path, threshold=0.5,
                          crop_length_mm=90.0, skip_bad=True, verbose=True,
                          align=True, min_border_voxels=500):
    """
    End-to-end pipeline:

        NIfTI -> Reorient to LPS -> Head Border Check -> Mesh ->
        Largest Component -> Length Check -> Head Check ->
        Cut perp. to long axis -> Waterproof ->
        Canonical Alignment -> Save

    Args:
        input_path:        path to .nii.gz segmentation mask
        output_path:       path to write .obj mesh
        threshold:         marching-cubes iso-value
        crop_length_mm:    keep this many mm from the proximal (head) end
                           (None = no cut)
        skip_bad:          if True, run quality checks and return None for
                           bad bones instead of saving
        verbose:           print progress
        align:             if True (default), apply canonical alignment so that
                           all output meshes share the same coordinate frame
                           (PC1->+Z head-up, PC2->+X, centred at origin)
        min_border_voxels: minimum bone voxels on a volume face to count as
                           clipped (passed to volume_border_check)

    Returns:
        (trimesh.Trimesh | None, str | None)
            - mesh: the processed mesh if successful, None if rejected
            - reason: rejection reason string if rejected, None if successful
    """
    def log(msg):
        if verbose:
            print(msg)

    log(f"\n{'='*60}")
    log(f"Processing: {input_path}")

    # -- 1. Load --
    log("  [1/10] Loading NIfTI ...")
    volume, nifti_img = load_nifti(input_path)
    log(f"          shape={volume.shape}  "
        f"spacing={tuple(float(s) for s in nifti_img.header.get_zooms()[:3])}")
    log(f"          original orientation: {nib.aff2axcodes(nifti_img.affine)}")

    # -- 2. Reorient to LPS --
    log("  [2/10] Reorienting to LPS ...")
    volume, spacing, ornt = reorient_to_lps(nifti_img)
    log(f"          shape={volume.shape}  spacing={spacing}  axes={ornt}")

    # -- 3. Head border check (detect clipped proximal end before meshing) --
    if skip_bad:
        log("  [3/10] Head border check (proximal end touching superior boundary?) ...")
        ok, reason = head_border_check(
            volume, threshold=threshold, min_border_voxels=min_border_voxels)
        if not ok:
            log(f"          REJECTED: {reason}")
            return None, reason
        log(f"          head not clipped — OK")

    # -- 4. Marching cubes --
    log("  [4/10] Marching cubes ...")
    mesh = volume_to_mesh(volume, spacing, threshold=threshold)
    log(f"          {len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    # -- 5. Keep largest component (remove stray fragments) --
    log("  [5/10] Removing stray fragments ...")
    mesh = keep_largest_component(mesh)
    log(f"          {len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    # -- 6. Length check --
    if skip_bad and crop_length_mm is not None:
        log("  [6/10] Length check ...")
        ok, reason, bone_length = mesh_length_check(mesh, crop_length_mm - 0.5)
        if not ok:
            log(f"          REJECTED: {reason}")
            return None, reason
        log(f"          {bone_length:.1f} mm >= {crop_length_mm:.0f} mm — OK")

    # -- 7. Head check + compute long axis for cutting --
    log("  [7/10] Computing long axis (PCA) ...")
    long_axis, top_point = compute_mesh_long_axis(mesh)

    if skip_bad:
        log("  [7/10] Head check ...")
        ok, reason = head_check(mesh, long_axis)
        if not ok:
            log(f"          REJECTED: {reason}")
            return None, reason
        log(f"          passed")

    # -- 8. Cut perpendicular to long axis --
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

    # -- 9. Waterproof --
    log("  [9/10] Waterproofing ...")
    mesh = waterproof_mesh(mesh)
    log(f"          watertight={mesh.is_watertight}, "
        f"{len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    # -- 10. Canonical alignment --
    if align:
        log("  [10/10] Aligning to canonical axes (pre-cut long_axis -> +Z head-up, PC2->+X) ...")
        mesh = align_mesh_to_canonical_axes(mesh, long_axis=long_axis)
        log(f"           centroid~{mesh.vertices.mean(axis=0).round(2)}, "
            f"Z-extent [{mesh.vertices[:,2].min():.1f}, {mesh.vertices[:,2].max():.1f}] mm")
    else:
        log("  [10/10] Alignment skipped (align=False)")

    # -- Save --
    mesh.export(output_path)
    log(f"  Saved: {output_path}")

    return mesh, None
