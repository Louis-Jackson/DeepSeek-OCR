#!/usr/bin/env python3
"""
DeepSeek-OCR Folder Batch Processor

Automatically processes all images and PDFs in a folder by calling existing scripts.
Deletes source files after successful processing.

Usage:
    Method 1 - Set environment variables:
        export DEEPSEEK_OCR_INPUT_PATH=/path/to/input/folder
        export DEEPSEEK_OCR_OUTPUT_PATH=/path/to/output/folder
        python run_dpsk_ocr_folder.py

    Method 2 - Set in config.py:
        Set _DEFAULT_INPUT_PATH and _DEFAULT_OUTPUT_PATH in config.py
        python run_dpsk_ocr_folder.py

    Method 3 - Command line arguments:
        python run_dpsk_ocr_folder.py --input /path/to/input --output /path/to/output
"""

import os
import glob
import subprocess
import sys
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def run_script_with_env(script_name, input_path, output_path, file_type):
    """
    Run the appropriate processing script with environment variables set.

    Args:
        script_name: Name of the script to run
        input_path: Path to input file
        output_path: Path to output directory
        file_type: Type of file ('image' or 'pdf')

    Returns:
        (success, output): Tuple of success boolean and output/error message
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)

    # Create environment with INPUT_PATH and OUTPUT_PATH set
    env = os.environ.copy()
    env['DEEPSEEK_OCR_INPUT_PATH'] = input_path
    env['DEEPSEEK_OCR_OUTPUT_PATH'] = output_path

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(__file__),
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per file
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr if result.stderr else result.stdout

    except subprocess.TimeoutExpired:
        return False, "Processing timed out (>1 hour)"
    except Exception as e:
        return False, str(e)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='DeepSeek-OCR Folder Batch Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variables
  export DEEPSEEK_OCR_INPUT_PATH=/data/documents
  export DEEPSEEK_OCR_OUTPUT_PATH=/data/results
  python run_dpsk_ocr_folder.py

  # Using command line arguments
  python run_dpsk_ocr_folder.py --input /data/documents --output /data/results

  # Without deleting source files
  python run_dpsk_ocr_folder.py --input /data/docs --output /data/results --no-delete
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input folder path (can also use DEEPSEEK_OCR_INPUT_PATH env var)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output folder path (can also use DEEPSEEK_OCR_OUTPUT_PATH env var)'
    )

    parser.add_argument(
        '--no-delete',
        action='store_true',
        help='Do not delete source files after processing'
    )

    return parser.parse_args()


def get_input_output_paths(args):
    """
    Determine INPUT_PATH and OUTPUT_PATH from arguments, environment variables, or config.
    Priority: command line args > environment variables > config.py defaults
    """
    # Try command line arguments first
    input_path = args.input
    output_path = args.output

    # Fall back to environment variables
    if not input_path:
        input_path = os.getenv('DEEPSEEK_OCR_INPUT_PATH')

    if not output_path:
        output_path = os.getenv('DEEPSEEK_OCR_OUTPUT_PATH')

    # Fall back to config.py defaults
    if not input_path or not output_path:
        from config import INPUT_PATH, OUTPUT_PATH
        if not input_path:
            input_path = INPUT_PATH
        if not output_path:
            output_path = OUTPUT_PATH

    return input_path, output_path


def process_folder(input_path, output_path, delete_files=True):
    """
    Main function to process all files in input_path folder.
    Routes each file to the appropriate script and optionally deletes after completion.

    Args:
        input_path: Path to input folder
        output_path: Path to output folder
        delete_files: Whether to delete source files after processing
    """

    if not input_path:
        print(f'{Colors.RED}{Colors.BOLD}ERROR: INPUT_PATH is not set{Colors.RESET}')
        print(f'{Colors.YELLOW}Please set it via:{Colors.RESET}')
        print(f'{Colors.YELLOW}  1. Environment variable: export DEEPSEEK_OCR_INPUT_PATH=/path/to/folder{Colors.RESET}')
        print(f'{Colors.YELLOW}  2. Command line: --input /path/to/folder{Colors.RESET}')
        print(f'{Colors.YELLOW}  3. config.py: _DEFAULT_INPUT_PATH = "/path/to/folder"{Colors.RESET}')
        return

    if not output_path:
        print(f'{Colors.RED}{Colors.BOLD}ERROR: OUTPUT_PATH is not set{Colors.RESET}')
        print(f'{Colors.YELLOW}Please set it via:{Colors.RESET}')
        print(f'{Colors.YELLOW}  1. Environment variable: export DEEPSEEK_OCR_OUTPUT_PATH=/path/to/folder{Colors.RESET}')
        print(f'{Colors.YELLOW}  2. Command line: --output /path/to/folder{Colors.RESET}')
        print(f'{Colors.YELLOW}  3. config.py: _DEFAULT_OUTPUT_PATH = "/path/to/folder"{Colors.RESET}')
        return

    if not os.path.isdir(input_path):
        print(f'{Colors.RED}{Colors.BOLD}ERROR: INPUT_PATH is not a valid directory{Colors.RESET}')
        print(f'{Colors.YELLOW}Current INPUT_PATH: {input_path}{Colors.RESET}')
        return

    # Create output directory
    os.makedirs(output_path, exist_ok=True)

    # Supported file types
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.webp',
                       '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.TIFF', '*.WEBP']
    pdf_extensions = ['*.pdf', '*.PDF']

    # Collect all files
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(input_path, ext)))

    pdf_files = []
    for ext in pdf_extensions:
        pdf_files.extend(glob.glob(os.path.join(input_path, ext)))

    total_files = len(image_files) + len(pdf_files)

    # Print header
    print(f'\n{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}      DeepSeek-OCR Folder Batch Processor{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
    print(f'{Colors.YELLOW}Input folder:  {Colors.RESET}{input_path}')
    print(f'{Colors.YELLOW}Output folder: {Colors.RESET}{output_path}')
    print(f'{Colors.BLUE}Found: {len(image_files)} image(s), {len(pdf_files)} PDF(s) = {total_files} total{Colors.RESET}')
    print(f'{Colors.MAGENTA}Delete after processing: {Colors.RESET}{"Yes" if delete_files else "No"}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}\n')

    if total_files == 0:
        print(f'{Colors.YELLOW}No files to process. Exiting.{Colors.RESET}')
        return

    # Track processed files
    successfully_processed = []
    failed_files = []

    # Process image files
    if image_files:
        print(f'{Colors.BLUE}{Colors.BOLD}Processing {len(image_files)} image file(s)...{Colors.RESET}\n')

        for idx, image_path in enumerate(image_files, 1):
            file_name = Path(image_path).name
            print(f'{Colors.CYAN}[{idx}/{len(image_files)}]{Colors.RESET} {file_name}')

            # Create a unique output subdirectory for this file
            file_name_without_ext = Path(image_path).stem
            file_output_path = os.path.join(output_path, file_name_without_ext)
            os.makedirs(file_output_path, exist_ok=True)
            os.makedirs(f'{file_output_path}/images', exist_ok=True)

            # Run image processing script with environment variables
            success, output = run_script_with_env(
                'run_dpsk_ocr_image.py',
                image_path,
                file_output_path,
                'image'
            )

            if success:
                successfully_processed.append(image_path)
                print(f'{Colors.GREEN}  ✓ Completed{Colors.RESET}\n')
            else:
                failed_files.append((image_path, output))
                print(f'{Colors.RED}  ✗ Failed{Colors.RESET}')
                if output:
                    # Print first line of error
                    error_line = output.split('\n')[0][:80]
                    print(f'{Colors.RED}    Error: {error_line}...{Colors.RESET}\n')

    # Process PDF files
    if pdf_files:
        print(f'{Colors.BLUE}{Colors.BOLD}Processing {len(pdf_files)} PDF file(s)...{Colors.RESET}\n')

        for idx, pdf_path in enumerate(pdf_files, 1):
            file_name = Path(pdf_path).name
            print(f'{Colors.CYAN}[{idx}/{len(pdf_files)}]{Colors.RESET} {file_name}')

            # Create a unique output subdirectory for this file
            file_name_without_ext = Path(pdf_path).stem
            file_output_path = os.path.join(output_path, file_name_without_ext)
            os.makedirs(file_output_path, exist_ok=True)
            os.makedirs(f'{file_output_path}/images', exist_ok=True)

            # Run PDF processing script with environment variables
            success, output = run_script_with_env(
                'run_dpsk_ocr_pdf.py',
                pdf_path,
                file_output_path,
                'pdf'
            )

            if success:
                successfully_processed.append(pdf_path)
                print(f'{Colors.GREEN}  ✓ Completed{Colors.RESET}\n')
            else:
                failed_files.append((pdf_path, output))
                print(f'{Colors.RED}  ✗ Failed{Colors.RESET}')
                if output:
                    # Print first line of error
                    error_line = output.split('\n')[0][:80]
                    print(f'{Colors.RED}    Error: {error_line}...{Colors.RESET}\n')

    # Delete successfully processed files if requested
    deleted_count = 0
    if delete_files and successfully_processed:
        print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
        print(f'{Colors.YELLOW}{Colors.BOLD}Cleaning up processed files...{Colors.RESET}')

        for file_path in successfully_processed:
            try:
                os.remove(file_path)
                deleted_count += 1
                print(f'{Colors.GREEN}  ✓ Deleted: {Path(file_path).name}{Colors.RESET}')
            except Exception as e:
                print(f'{Colors.RED}  ✗ Failed to delete {Path(file_path).name}: {e}{Colors.RESET}')

    # Print summary
    print(f'\n{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}Processing Summary{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
    print(f'{Colors.GREEN}  ✓ Successfully processed: {len(successfully_processed)}/{total_files} file(s){Colors.RESET}')

    if delete_files:
        print(f'{Colors.GREEN}  ✓ Files deleted: {deleted_count}{Colors.RESET}')

    if failed_files:
        print(f'{Colors.RED}  ✗ Failed: {len(failed_files)} file(s){Colors.RESET}')
        print(f'{Colors.YELLOW}\n  Failed files:{Colors.RESET}')
        for file_path, error in failed_files[:5]:  # Show first 5 failed files
            print(f'{Colors.YELLOW}    - {Path(file_path).name}{Colors.RESET}')
        if len(failed_files) > 5:
            print(f'{Colors.YELLOW}    ... and {len(failed_files) - 5} more{Colors.RESET}')

    print(f'{Colors.BLUE}\n  Results saved to: {output_path}{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}\n')


def main():
    """Main entry point."""
    args = parse_arguments()

    # Get input and output paths
    input_path, output_path = get_input_output_paths(args)

    # Process folder
    try:
        process_folder(input_path, output_path, delete_files=not args.no_delete)
    except KeyboardInterrupt:
        print(f'\n{Colors.YELLOW}Process interrupted by user{Colors.RESET}')
        sys.exit(1)
    except Exception as e:
        print(f'{Colors.RED}Unexpected error: {e}{Colors.RESET}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
