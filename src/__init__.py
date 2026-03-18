"""
Femur mesh processing package.
"""

from .nifti_io import load_nifti, reorient_to_lps
from .quality_checks import head_border_check, mesh_length_check, head_check
from .mesh_operations import volume_to_mesh, keep_largest_component, waterproof_mesh, cut_mesh_along_axis
from .pca_alignment import compute_mesh_long_axis, align_mesh_to_canonical_axes
from .pipeline import process_nifti_to_mesh
from .logger import ProcessLogger

__all__ = [
    # NIfTI I/O
    'load_nifti',
    'reorient_to_lps',
    
    # Quality checks
    'head_border_check',
    'mesh_length_check',
    'head_check',
    
    # Mesh operations
    'volume_to_mesh',
    'keep_largest_component',
    'waterproof_mesh',
    'cut_mesh_along_axis',
    
    # PCA alignment
    'compute_mesh_long_axis',
    'align_mesh_to_canonical_axes',
    
    # Main pipeline
    'process_nifti_to_mesh',
    
    # Logging
    'ProcessLogger',
]
