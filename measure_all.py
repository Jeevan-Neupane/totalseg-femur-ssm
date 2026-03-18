"""
Measure the length of all mesh files in a directory.
"""

from pathlib import Path
import trimesh
import sys

def measure_all_meshes(directory):
    """Measure all .obj files in directory and subdirectories."""
    dir_path = Path(directory)
    obj_files = list(dir_path.rglob("*.obj"))
    
    if not obj_files:
        print(f"No .obj files found in {directory}")
        return
    
    print(f"Found {len(obj_files)} mesh files")
    print("=" * 80)
    
    results = []
    for obj_file in sorted(obj_files):
        try:
            mesh = trimesh.load(str(obj_file))
            z_coords = mesh.vertices[:, 2]
            length = z_coords.max() - z_coords.min()
            
            relative_path = obj_file.relative_to(dir_path)
            results.append((str(relative_path), length))
            print(f"{str(relative_path):40s} {length:6.2f} mm")
        except Exception as e:
            print(f"{str(obj_file.name):40s} ERROR: {e}")
    
    print("=" * 80)
    print(f"Total: {len(results)} meshes")
    if results:
        lengths = [r[1] for r in results]
        print(f"Min length: {min(lengths):.2f} mm")
        print(f"Max length: {max(lengths):.2f} mm")
        print(f"Avg length: {sum(lengths)/len(lengths):.2f} mm")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "output_test_20"
    
    measure_all_meshes(directory)
