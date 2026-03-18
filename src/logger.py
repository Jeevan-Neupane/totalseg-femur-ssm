"""
Logging utilities for tracking processed, skipped and failed files.
"""

import csv
from pathlib import Path
from datetime import datetime


class ProcessLogger:
    """Logger for tracking all file processing with detailed information."""
    
    def __init__(self, output_dir):
        """
        Initialize the process logger.
        
        Args:
            output_dir: Directory where log files will be saved
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate logs for different outcomes
        self.success_records = []
        self.skipped_records = []
        self.failed_records = []
        
        # Timestamp for this run
        self.run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def log_success(self, file_path, output_path, bone_length=None, voxel_count=None, 
                   processing_time=None, vertices=None, faces=None):
        """
        Log a successfully processed file.
        
        Args:
            file_path: Input file path
            output_path: Output mesh file path
            bone_length: Length of bone in mm
            voxel_count: Number of voxels in segmentation
            processing_time: Time taken to process in seconds
            vertices: Number of vertices in mesh
            faces: Number of faces in mesh
        """
        self.success_records.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'input_file': str(file_path),
            'output_file': str(output_path),
            'status': 'SUCCESS',
            'bone_length_mm': f"{bone_length:.2f}" if bone_length else 'N/A',
            'voxel_count': voxel_count if voxel_count else 'N/A',
            'vertices': vertices if vertices else 'N/A',
            'faces': faces if faces else 'N/A',
            'processing_time_sec': f"{processing_time:.2f}" if processing_time else 'N/A',
            'reason': 'Processed successfully'
        })
    
    def log_skip(self, file_path, reason, bone_length=None, voxel_count=None, 
                border_voxels=None, head_ratio=None):
        """
        Log a skipped file with detailed reason.
        
        Args:
            file_path: Path to the skipped file
            reason: Reason for skipping
            bone_length: Length of bone in mm (if measured)
            voxel_count: Number of voxels in segmentation
            border_voxels: Number of voxels touching border
            head_ratio: Femoral head ratio (if computed)
        """
        self.skipped_records.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'input_file': str(file_path),
            'output_file': 'N/A',
            'status': 'SKIPPED',
            'bone_length_mm': f"{bone_length:.2f}" if bone_length else 'N/A',
            'voxel_count': voxel_count if voxel_count else 'N/A',
            'border_voxels': border_voxels if border_voxels else 'N/A',
            'head_ratio': f"{head_ratio:.3f}" if head_ratio else 'N/A',
            'processing_time_sec': 'N/A',
            'reason': reason
        })
    
    def log_failure(self, file_path, error_message):
        """
        Log a failed file with error message.
        
        Args:
            file_path: Path to the failed file
            error_message: Error message
        """
        self.failed_records.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'input_file': str(file_path),
            'output_file': 'N/A',
            'status': 'FAILED',
            'bone_length_mm': 'N/A',
            'voxel_count': 'N/A',
            'processing_time_sec': 'N/A',
            'reason': f"Error: {error_message}"
        })
    
    def save_all(self):
        """Save all logs to separate CSV files."""
        # Save success log
        if self.success_records:
            success_path = self.output_dir / f"success_{self.run_timestamp}.csv"
            self._save_csv(success_path, self.success_records)
        
        # Save skipped log
        if self.skipped_records:
            skipped_path = self.output_dir / f"skipped_{self.run_timestamp}.csv"
            self._save_csv(skipped_path, self.skipped_records)
        
        # Save failed log
        if self.failed_records:
            failed_path = self.output_dir / f"failed_{self.run_timestamp}.csv"
            self._save_csv(failed_path, self.failed_records)
        
        # Save combined summary log
        all_records = self.success_records + self.skipped_records + self.failed_records
        if all_records:
            summary_path = self.output_dir / f"processing_log_{self.run_timestamp}.csv"
            self._save_csv(summary_path, all_records)
    
    def _save_csv(self, path, records):
        """Save records to CSV file."""
        if not records:
            return
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = records[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    
    def get_counts(self):
        """Get counts of success, skipped, and failed."""
        return {
            'success': len(self.success_records),
            'skipped': len(self.skipped_records),
            'failed': len(self.failed_records),
            'total': len(self.success_records) + len(self.skipped_records) + len(self.failed_records)
        }
    
    def get_skip_summary(self):
        """Get a summary of skip reasons."""
        summary = {}
        for record in self.skipped_records:
            reason = record['reason']
            summary[reason] = summary.get(reason, 0) + 1
        return summary
    
    def print_summary(self):
        """Print processing summary."""
        counts = self.get_counts()
        print("\n" + "=" * 80)
        print("PROCESSING SUMMARY")
        print("=" * 80)
        print(f"Total files processed: {counts['total']}")
        print(f"  ✓ Success: {counts['success']}")
        print(f"  ⊘ Skipped: {counts['skipped']}")
        print(f"  ✗ Failed:  {counts['failed']}")
        
        if self.skipped_records:
            print("\nSkip reasons:")
            for reason, count in sorted(self.get_skip_summary().items(), key=lambda x: -x[1]):
                print(f"  {count:3d} - {reason}")
        
        print(f"\n📁 Logs saved to: {self.output_dir}")
        if self.success_records:
            print(f"   - success_{self.run_timestamp}.csv")
        if self.skipped_records:
            print(f"   - skipped_{self.run_timestamp}.csv")
        if self.failed_records:
            print(f"   - failed_{self.run_timestamp}.csv")
        print(f"   - processing_log_{self.run_timestamp}.csv (combined)")
        print("=" * 80)
