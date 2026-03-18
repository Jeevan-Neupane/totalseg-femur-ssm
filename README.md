# Femur Mesh Processing Pipeline

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust Python toolkit for converting femur segmentation masks (NIfTI format) into high-quality, watertight 3D meshes with automatic cropping, quality filtering, and left/right separation.

## 🎯 Features

- ✅ **Automatic 90mm cropping** from femoral head along anatomical axis
- ✅ **PCA-based alignment** ensures straight cuts regardless of CT orientation
- ✅ **LPS reorientation** standardizes all scans (Left-Posterior-Superior)
- ✅ **Quality filtering** rejects bones with clipped heads or insufficient length
- ✅ **Canonical alignment** all output meshes share the same coordinate frame
- ✅ **Watertight meshes** automatic hole filling and mesh repair
- ✅ **Comprehensive logging** CSV logs with detailed processing information
- ✅ **Interactive CLI** user-friendly command-line interface
- ✅ **Modular architecture** clean, maintainable code structure

## 📋 Table of Contents

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

## 🚀 Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Setup

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/femur-mesh-processing.git
cd femur-mesh-processing
```

2. **Create a virtual environment (recommended):**

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

## ⚡ Quick Start

1. **Prepare your data:**

Place your NIfTI files (`.nii.gz`) in the following structure:

```
Femur/
├── train/
│   ├── p_0001/
│   │   └── ct-scan/
│   │       ├── femur_left_msk.nii.gz
│   │       └── femur_right_msk.nii.gz
│   └── ...
├── val/
└── test/
```

2. **Run the processing pipeline:**

```bash
python main.py
```

3. **Choose your option:**

```
Options:
  1. Process ALL files
  2. Process custom number of files (left + right)
  3. Exit
```

## 📖 Usage

### Interactive CLI

The main script provides an interactive menu:

```bash
python main.py
```

**Option 1:** Process all files → Output: `Femur_Meshes_90mm/`

**Option 2:** Process custom number (e.g., 10 per side) → Output: `output_10_per_side/`

**Option 3:** Exit



### Measure Mesh Lengths

Measure all processed meshes:

```bash
python measure_all.py [directory]
```

Example:
```bash
python measure_all.py Femur_Meshes_90mm
```

## 📁 Project Structure

```
femur-mesh-processing/
├── src/                        # Source code package
│   ├── __init__.py            # Package initialization & exports
│   ├── nifti_io.py            # NIfTI file I/O operations
│   ├── quality_checks.py      # Quality validation functions
│   ├── mesh_operations.py     # Mesh processing operations
│   ├── pca_alignment.py       # PCA-based alignment
│   ├── pipeline.py            # Main processing pipeline
│   └── logger.py              # Logging utilities
├── main.py                     # Interactive CLI entry point
├── measure_all.py              # Utility to measure mesh lengths
├── requirements.txt            # Python dependencies
├── setup.py                    # Package installation script
├── README.md                   # Main documentation
├── CONTRIBUTING.md             # Contribution guidelines
├── PROJECT_STRUCTURE.md        # Detailed structure documentation
├── LICENSE                     # MIT License
└── .gitignore                  # Git ignore rules
```

### Module Descriptions

- **nifti_io.py**: NIfTI file loading and LPS reorientation
- **quality_checks.py**: Head border check, length check, head presence check
- **mesh_operations.py**: Marching cubes, component filtering, waterproofing, cutting
- **pca_alignment.py**: Long axis computation and canonical alignment
- **pipeline.py**: Complete end-to-end processing pipeline
- **logger.py**: Comprehensive CSV logging system

## 🔄 Pipeline Overview

The processing pipeline consists of 10 steps:

### 1. Load NIfTI File
Loads the segmentation mask from NIfTI format.

### 2. Reorient to LPS Standard
Standardizes orientation regardless of scanner convention.

### 3. Head Border Check
Detects if the femoral head is clipped at the superior boundary.

### 4. Marching Cubes
Converts volume to triangle mesh.

### 5. Keep Largest Component
Removes stray fragments (patella, acetabulum, etc.).

### 6. Length Check
Rejects bones shorter than 89.5mm.

### 7. Compute Long Axis (PCA)
Finds the anatomical long axis using Principal Component Analysis.

### 8. Head Check
Detects shaft-only bones (missing femoral head).

### 9. Cut Perpendicular to Axis
Crops to 90mm from the proximal end.

### 10. Waterproof Mesh
Fills holes and ensures watertight mesh.

### 11. Canonical Alignment
Aligns all meshes to the same coordinate frame.

## 📁 Output Structure

```
Femur_Meshes_90mm/
├── left/
│   ├── femur_001.obj
│   ├── femur_002.obj
│   └── ...
├── right/
│   ├── femur_001.obj
│   ├── femur_002.obj
│   └── ...
└── logs/
    ├── success_20240115_103045.csv
    ├── skipped_20240115_103045.csv
    ├── failed_20240115_103045.csv
    └── processing_log_20240115_103045.csv
```

### Mesh Characteristics

- **Cropped:** 90mm from top along anatomical axis (PCA-based)
- **Straight cut:** Perpendicular to bone axis regardless of CT orientation
- **Separated:** Left and right femurs in separate directories
- **Quality filtered:** Bones shorter than 89.5mm or with clipped heads are skipped
- **Canonically aligned:** All meshes in same coordinate frame (+Z = head up)
- **Watertight:** All holes are filled
- **Proper scaling:** Voxel spacing from NIfTI header is preserved
- **Format:** Standard Wavefront OBJ format

## ✅ Quality Checks

The pipeline performs three quality checks:

### 1. Head Border Check
- **Purpose:** Detect clipped femoral heads
- **Method:** Checks if ≥500 voxels touch the superior boundary
- **Action:** Skip if clipped

### 2. Length Check
- **Purpose:** Ensure sufficient bone length
- **Method:** PCA-based length measurement
- **Threshold:** ≥89.5mm
- **Action:** Skip if too short

### 3. Head Check
- **Purpose:** Detect shaft-only bones (missing femoral head)
- **Method:** Analyzes shape profile along long axis
- **Metric:** Tip/max-top ratio < 0.85
- **Action:** Skip if head missing

## 📊 Logging

All processing details are logged to CSV files in the `logs/` directory:

### success_*.csv
```csv
timestamp,input_file,output_file,status,bone_length_mm,voxel_count,vertices,faces,processing_time_sec,reason
2024-01-15 10:30:45,path/to/input.nii.gz,path/to/output.obj,SUCCESS,92.34,125000,15234,30468,4.52,Processed successfully
```

### skipped_*.csv
```csv
timestamp,input_file,output_file,status,bone_length_mm,voxel_count,border_voxels,head_ratio,processing_time_sec,reason
2024-01-15 10:31:12,path/to/input.nii.gz,N/A,SKIPPED,85.3,98000,N/A,N/A,N/A,bone too short (85.3 mm < 90 mm)
```

### failed_*.csv
```csv
timestamp,input_file,output_file,status,bone_length_mm,voxel_count,processing_time_sec,reason
2024-01-15 10:32:05,path/to/input.nii.gz,N/A,FAILED,N/A,N/A,N/A,Error: File corrupted
```

### processing_log_*.csv
Combined log of all files (success + skipped + failed)

## 📚 API Reference

The main pipeline function is process_nifti_to_mesh() which accepts parameters for input/output paths, marching cubes threshold, crop length, quality checks, verbosity, canonical alignment, and border check threshold.

## 🔧 Troubleshooting

### Common Issues

**1. ImportError: No module named 'nibabel'**
```bash
pip install -r requirements.txt
```

**2. File not found errors**
- Check that your data is in the `Femur/` directory
- Verify the folder structure matches the expected format

**3. Memory errors with large files**
- The 90mm cropping reduces memory usage significantly
- Process files in smaller batches using Option 2

**4. Too many bones being skipped**
- Check skip reasons in the logs
- Adjust `min_border_voxels` parameter if needed (default: 500)
- Common reasons: bone too short (<89.5mm), femoral head clipped, head missing

**5. Import errors after restructuring**
```bash
# Reinstall the package
pip install -e .
```

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

```bibtex
@software{femur_mesh_processing,
  author = {Your Name},
  title = {Femur Mesh Processing Pipeline},
  year = {2024},
  url = {https://github.com/yourusername/femur-mesh-processing}
}
```

## 🙏 Acknowledgments

- Marching cubes implementation from [scikit-image](https://scikit-image.org/)
- Mesh repair using [PyMeshFix](https://github.com/pyvista/pymeshfix)
- Medical imaging I/O with [NiBabel](https://nipy.org/nibabel/)

## 📧 Contact

For questions or issues, please open an issue on GitHub or contact [jeevan.neupane003@gmail.com](mailto:jeevan.neupane003@gmail.com).

---

