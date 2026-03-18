"""
NIfTI file I/O operations.
"""

import nibabel as nib
import numpy as np


def load_nifti(file_path):
    """
    Load a NIfTI file and return (volume, nifti_image).
    
    Args:
        file_path: Path to the .nii or .nii.gz file
        
    Returns:
        tuple: (data array, nifti image object)
    """
    nifti_img = nib.load(file_path)
    data = nifti_img.get_fdata()
    return data, nifti_img


def reorient_to_lps(nifti_img):
    """
    Reorient a NIfTI image so its voxel axes correspond to LPS directions.

    CT scans arrive in many orientation conventions (RAS, LPS, LAS, etc.)
    depending on the scanner. Reorienting to LPS (Left-Posterior-Superior)
    ensures consistent array axes across all scans.

    Args:
        nifti_img: nibabel.nifti1.Nifti1Image object

    Returns:
        tuple: (volume, spacing, orientation_code)
            - volume: reoriented 3D array
            - spacing: voxel sizes in mm (x, y, z)
            - orientation_code: nibabel axcodes ('L','P','S')
    """
    # Step 1: bring to RAS+ (nibabel canonical orientation)
    canonical = nib.as_closest_canonical(nifti_img)

    # Step 2: RAS+ -> LPS+ (flip first two axes: R->L, A->P; S stays)
    ras_data = canonical.get_fdata()
    lps_data = ras_data[::-1, ::-1, :].copy()

    # Build the new affine: flip the first two columns
    lps_affine = canonical.affine.copy()
    # Flip axis 0 (R->L)
    lps_affine[:3, 0] = -lps_affine[:3, 0]
    lps_affine[:3, 3] += canonical.affine[:3, 0] * (ras_data.shape[0] - 1)
    # Flip axis 1 (A->P)
    lps_affine[:3, 1] = -lps_affine[:3, 1]
    lps_affine[:3, 3] += canonical.affine[:3, 1] * (ras_data.shape[1] - 1)

    lps_img = nib.Nifti1Image(lps_data, lps_affine, canonical.header)
    spacing = tuple(float(s) for s in lps_img.header.get_zooms()[:3])
    ornt = nib.aff2axcodes(lps_affine)

    return lps_data, spacing, ornt
