"""
Main entry point for femur mesh processing.
Allows user to choose between processing all files or a custom number.
"""

import os
import sys
import time
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from pipeline import process_nifti_to_mesh
from logger import ProcessLogger


def get_user_choice():
    """Get user's processing choice."""
    print("\n" + "=" * 80)
    print("FEMUR MESH PROCESSING - 90mm Crop with Left/Right Separation")
    print("=" * 80)
    print("\nOptions:")
    print("  1. Process ALL files")
    print("  2. Process custom number of files (left + right)")
    print("  3. Exit")
    print("=" * 80)
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        if choice in ['1', '2', '3']:
            return choice
        print("Invalid choice. Please enter 1, 2, or 3.")


def get_custom_count():
    """Get custom number of files to process."""
    while True:
        try:
            count = input("\nHow many files per side (left/right)? (e.g., 10): ").strip()
            count = int(count)
            if count > 0:
                return count
            print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def process_files(nifti_files, output_dir, max_per_side=None):
    """Process femur files with optional limit per side."""
    left_dir = output_dir / "left"
    right_dir = output_dir / "right"
    logs_dir = output_dir / "logs"
    left_dir.mkdir(parents=True, exist_ok=True)
    right_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize process logger
    logger = ProcessLogger(logs_dir)
    
    # Separate left and right files
    left_files = [f for f in nifti_files if 'left' in f.stem.lower()]
    right_files = [f for f in nifti_files if 'right' in f.stem.lower()]
    
    # Apply limit if specified
    if max_per_side:
        left_files = left_files[:max_per_side]
        right_files = right_files[:max_per_side]
    
    print(f"\nProcessing {len(left_files)} left and {len(right_files)} right femurs")
    print(f"Output: {output_dir}")
    print("Cropping: 90mm from top | Min length: 89.5mm")
    print("=" * 80)
    
    left_counter = 1
    right_counter = 1
    
    # Process left files
    for nifti_file in tqdm(left_files, desc="Left femurs"):
        output_path = left_dir / f"femur_{left_counter:03d}.obj"
        left_counter += 1
        
        start_time = time.time()
        try:
            mesh, reason = process_nifti_to_mesh(
                str(nifti_file), str(output_path), 
                threshold=0.5, crop_length_mm=90, 
                skip_bad=True, verbose=False
            )
            processing_time = time.time() - start_time
            
            if mesh is None:
                logger.log_skip(nifti_file, reason)
                tqdm.write(f"  SKIP ({nifti_file.name}): {reason}")
            else:
                # Get mesh info
                vertices = len(mesh.vertices)
                faces = len(mesh.faces)
                bone_length = mesh.vertices[:, 2].max() - mesh.vertices[:, 2].min()
                
                logger.log_success(
                    nifti_file, output_path,
                    bone_length=bone_length,
                    vertices=vertices,
                    faces=faces,
                    processing_time=processing_time
                )
        except Exception as e:
            logger.log_failure(nifti_file, str(e))
            tqdm.write(f"✗ Failed: {nifti_file.name} - {str(e)}")
    
    # Process right files
    for nifti_file in tqdm(right_files, desc="Right femurs"):
        output_path = right_dir / f"femur_{right_counter:03d}.obj"
        right_counter += 1
        
        start_time = time.time()
        try:
            mesh, reason = process_nifti_to_mesh(
                str(nifti_file), str(output_path), 
                threshold=0.5, crop_length_mm=90, 
                skip_bad=True, verbose=False
            )
            processing_time = time.time() - start_time
            
            if mesh is None:
                logger.log_skip(nifti_file, reason)
                tqdm.write(f"  SKIP ({nifti_file.name}): {reason}")
            else:
                # Get mesh info
                vertices = len(mesh.vertices)
                faces = len(mesh.faces)
                bone_length = mesh.vertices[:, 2].max() - mesh.vertices[:, 2].min()
                
                logger.log_success(
                    nifti_file, output_path,
                    bone_length=bone_length,
                    vertices=vertices,
                    faces=faces,
                    processing_time=processing_time
                )
        except Exception as e:
            logger.log_failure(nifti_file, str(e))
            tqdm.write(f"✗ Failed: {nifti_file.name} - {str(e)}")
    
    # Save all logs
    logger.save_all()
    
    # Print summary
    logger.print_summary()
    print(f"\n✓ Output directory: {output_dir}")
    print("=" * 80)


def main():
    """Main function."""
    input_dir = Path("Femur")
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"\n✗ Error: Input directory '{input_dir}' not found!")
        print("Please ensure the 'Femur' directory exists with train/val/test subdirectories.")
        return
    
    # Find all .nii.gz files
    nifti_files = []
    for split in ['train', 'val', 'test']:
        split_path = input_dir / split
        if split_path.exists():
            nifti_files.extend(list(split_path.rglob("*.nii.gz")))
    
    if not nifti_files:
        print(f"\n✗ Error: No .nii.gz files found in '{input_dir}'!")
        return
    
    nifti_files.sort()
    print(f"\nFound {len(nifti_files)} total files in dataset")
    
    # Get user choice
    choice = get_user_choice()
    
    if choice == '3':
        print("\nExiting...")
        return
    
    if choice == '1':
        # Process all files
        output_dir = Path("Femur_Meshes_90mm")
        process_files(nifti_files, output_dir, max_per_side=None)
    
    elif choice == '2':
        # Process custom number
        count = get_custom_count()
        output_dir = Path(f"output_{count}_per_side")
        process_files(nifti_files, output_dir, max_per_side=count)


if __name__ == "__main__":
    main()
