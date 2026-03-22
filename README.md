# Femur Mesh Processing Pipeline


A robust Python toolkit for converting TotalSegmentator femur segmentation masks (NIfTI format) into high-quality, watertight 3D meshes ready for Statistical Shape Model (SSM) construction. Features automatic 90mm cropping, PCA-based canonical alignment, quality filtering, and watertight mesh generation.

*Figure 1: Complete processing pipeline from NIfTI segmentation to aligned mesh*

## Features

- **Automatic 90mm cropping** from femoral head along anatomical axis
- **PCA-based alignment** ensures straight cuts regardless of CT orientation
- **LPS reorientation** standardizes all scans (Left-Posterior-Superior)
- **Quality filtering** rejects bones with clipped heads or insufficient length
- **Canonical alignment** all output meshes share the same coordinate frame
- **Watertight meshes** automatic hole filling and mesh repair
- **Comprehensive logging** CSV logs with detailed processing information
- **Interactive CLI** user-friendly command-line interface
- **Modular architecture** clean, maintainable code structure

![Feature Highlights](path/to/features.png)
*Figure 2: Key features - cropping, alignment, and quality filtering*

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Pipeline Overview](#pipeline-overview)
- [Output Structure](#output-structure)
- [Quality Checks](#quality-checks)
- [Logging](#logging)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Setup

1. Clone the repository
2. Create a virtual environment (recommended)
3. Install dependencies using requirements.txt or install as a package

## Quick Start

1. **Prepare your data:**

Place your NIfTI files (.nii.gz) in the Femur directory with train/val/test subdirectories. Each patient folder should contain a ct-scan directory with femur_left_msk.nii.gz and femur_right_msk.nii.gz files.

![Input Data Structure](path/to/input_structure.png)
*Figure 3: Expected input directory structure*

2. **Run the processing pipeline:**

Execute main.py and choose from the interactive menu options.

3. **Choose your option:**

- Option 1: Process ALL files
- Option 2: Process custom number of files (left + right)
- Option 3: Exit

![CLI Interface](path/to/cli_interface.png)
*Figure 4: Interactive command-line interface*

## Usage

### Interactive CLI

The main script provides an interactive menu with three options for processing files.

**Option 1:** Process all files → Output: Femur_Meshes_90mm/

**Option 2:** Process custom number (e.g., 10 per side) → Output: output_10_per_side/

**Option 3:** Exit

### Measure Mesh Lengths

Use measure_all.py to measure all processed meshes in a directory.

## Project Structure

The project is organized into modular components:

- **src/**: Source code package containing all modules
  - **nifti_io.py**: NIfTI file I/O operations and LPS reorientation
  - **quality_checks.py**: Head border check, length check, head presence check
  - **mesh_operations.py**: Marching cubes, component filtering, waterproofing, cutting
  - **pca_alignment.py**: Long axis computation and canonical alignment
  - **pipeline.py**: Complete end-to-end processing pipeline
  - **logger.py**: Comprehensive CSV logging system
- **main.py**: Interactive CLI entry point
- **measure_all.py**: Utility to measure mesh lengths
- **requirements.txt**: Python dependencies
- **setup.py**: Package installation script

## Pipeline Overview

The processing pipeline consists of 11 sequential steps:

![Pipeline Steps](path/to/pipeline_steps.png)
*Figure 5: 11-step processing pipeline*

### 1. Load NIfTI File
Loads the segmentation mask from NIfTI format.

### 2. Reorient to LPS Standard
Standardizes orientation to Left-Posterior-Superior regardless of scanner convention.

![LPS Reorientation](path/to/lps_reorientation.png)
*Figure 6: LPS reorientation standardizes all scans*

### 3. Head Border Check
Detects if the femoral head is clipped at the superior boundary (>=500 voxels threshold).

### 4. Marching Cubes
Converts binary volume to triangle mesh using marching cubes algorithm.

![Marching Cubes](path/to/marching_cubes.png)
*Figure 7: Volume to mesh conversion*

### 5. Keep Largest Component
Removes stray fragments (patella, acetabulum, etc.) by keeping only the largest connected component.

### 6. Length Check
Rejects bones shorter than 89.5mm using PCA-based length measurement.

### 7. Compute Long Axis (PCA)
Finds the anatomical long axis using Principal Component Analysis.

![PCA Alignment](path/to/pca_alignment.png)
*Figure 8: PCA-based long axis computation*

### 8. Head Check
Detects shaft-only bones (missing femoral head) by analyzing shape profile. Tip/max-top ratio must be < 0.85.

### 9. Cut Perpendicular to Axis
Crops to exactly 90mm from the proximal end, perpendicular to the anatomical axis.

![Perpendicular Cut](path/to/perpendicular_cut.png)
*Figure 9: 90mm cropping perpendicular to bone axis*

### 10. Waterproof Mesh
Fills holes and ensures watertight mesh suitable for SSM analysis.

### 11. Canonical Alignment
Aligns all meshes to the same coordinate frame (+Z = head up) for consistent SSM input.

![Canonical Alignment](path/to/canonical_alignment.png)
*Figure 10: All meshes aligned to canonical coordinate frame*

## Output Structure

Processed meshes are organized by side with comprehensive logging:

- **left/**: Left femur meshes (femur_001.obj, femur_002.obj, ...)
- **right/**: Right femur meshes (femur_001.obj, femur_002.obj, ...)
- **logs/**: CSV logs with timestamps
  - success_*.csv: Successfully processed files
  - skipped_*.csv: Skipped files with reasons
  - failed_*.csv: Failed files with error messages
  - processing_log_*.csv: Combined log of all files

![Output Structure](path/to/output_structure.png)
*Figure 11: Output directory organization*

### Mesh Characteristics

- **Cropped:** 90mm from top along anatomical axis (PCA-based)
- **Straight cut:** Perpendicular to bone axis regardless of CT orientation
- **Separated:** Left and right femurs in separate directories
- **Quality filtered:** Bones shorter than 89.5mm or with clipped heads are skipped
- **Canonically aligned:** All meshes in same coordinate frame (+Z = head up)
- **Watertight:** All holes are filled
- **Proper scaling:** Voxel spacing from NIfTI header is preserved
- **Format:** Standard Wavefront OBJ format

![Mesh Characteristics](path/to/mesh_characteristics.png)
*Figure 12: Final mesh properties - cropped, aligned, and watertight*

## ✅ Quality Checks

The pipeline performs three quality checks to ensure high-quality meshes for SSM:

![Quality Checks](path/to/quality_checks.png)
*Figure 13: Three quality validation checks*

### 1. Head Border Check
- **Purpose:** Detect clipped femoral heads
- **Method:** Checks if >=500 voxels touch the superior boundary
- **Action:** Skip if clipped

### 2. Length Check
- **Purpose:** Ensure sufficient bone length
- **Method:** PCA-based length measurement
- **Threshold:** >=89.5mm
- **Action:** Skip if too short

### 3. Head Check
- **Purpose:** Detect shaft-only bones (missing femoral head)
- **Method:** Analyzes shape profile along long axis
- **Metric:** Tip/max-top ratio < 0.85
- **Action:** Skip if head missing

## Logging

All processing details are logged to timestamped CSV files in the logs/ directory. Each log contains comprehensive information including timestamp, file paths, status, bone length, voxel count, mesh statistics, processing time, and detailed reasons for success/skip/failure.

![Logging System](path/to/logging_system.png)
*Figure 14: Comprehensive CSV logging system*

## API Reference

The main pipeline function is process_nifti_to_mesh() which accepts parameters for input/output paths, marching cubes threshold, crop length, quality checks, verbosity, canonical alignment, and border check threshold.

## Troubleshooting

### Common Issues

**1. ImportError: No module named 'nibabel'**
Install all required dependencies from requirements.txt

**2. File not found errors**
- Check that your data is in the Femur/ directory
- Verify the folder structure matches the expected format

**3. Memory errors with large files**
- The 90mm cropping reduces memory usage significantly
- Process files in smaller batches using Option 2

**4. Too many bones being skipped**
- Check skip reasons in the logs
- Adjust min_border_voxels parameter if needed (default: 500)
- Common reasons: bone too short (<89.5mm), femoral head clipped, head missing

**5. Import errors after restructuring**
Reinstall the package using pip install -e .

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Citation

If you use this code in your research, please cite:

**BibTeX format:**

@software{totalseg_femur_ssm,
  author = {Jeevan Neupane},
  title = {TotalSegmentator Femur SSM Preprocessing Pipeline},
  year = {2024},
  url = {https://github.com/yourusername/totalseg-femur-ssm}
}

## 🙏 Acknowledgments

- Marching cubes implementation from [scikit-image](https://scikit-image.org/)
- Mesh repair using [PyMeshFix](https://github.com/pyvista/pymeshfix)
- Medical imaging I/O with [NiBabel](https://nipy.org/nibabel/)

## 📧 Contact

For questions or issues, please open an issue on GitHub or contact [jeevan.neupane003@gmail.com](mailto:jeevan.neupane003@gmail.com).

---

