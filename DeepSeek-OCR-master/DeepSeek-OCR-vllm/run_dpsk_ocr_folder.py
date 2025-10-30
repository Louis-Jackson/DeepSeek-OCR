#!/usr/bin/env python3
"""
DeepSeek-OCR Folder Batch Processor

Automatically processes all images and PDFs in a folder by calling existing scripts.
Deletes source files after successful processing.

Usage:
    1. Set INPUT_PATH to a folder path in config.py
    2. Set OUTPUT_PATH in config.py
    3. Run: python run_dpsk_ocr_folder.py
"""

import os
import glob
import subprocess
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import INPUT_PATH, OUTPUT_PATH


class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def modify_config_file(input_path, output_path=None):
    """
    Temporarily modify config.py INPUT_PATH for processing a single file.
    Returns the modified content to restore later.
    """
    config_file = os.path.join(os.path.dirname(__file__), 'config.py')

    with open(config_file, 'r', encoding='utf-8') as f:
        original_content = f.read()

    # Replace INPUT_PATH value
    import re
    modified_content = re.sub(
        r"INPUT_PATH\s*=\s*['\"].*?['\"]",
        f"INPUT_PATH = '{input_path}'",
        original_content
    )

    if output_path:
        modified_content = re.sub(
            r"OUTPUT_PATH\s*=\s*['\"].*?['\"]",
            f"OUTPUT_PATH = '{output_path}'",
            modified_content
        )

    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    return original_content


def restore_config_file(original_content):
    """Restore config.py to its original content."""
    config_file = os.path.join(os.path.dirname(__file__), 'config.py')
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(original_content)


def run_script(script_name, file_path, file_type):
    """
    Run the appropriate processing script for a file.
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Processing timed out (>1 hour)"
    except Exception as e:
        return False, str(e)


def process_folder():
    """
    Main function to process all files in INPUT_PATH folder.
    Routes each file to the appropriate script and deletes after completion.
    """

    if not os.path.isdir(INPUT_PATH):
        print(f'{Colors.RED}{Colors.BOLD}ERROR: INPUT_PATH must be a directory{Colors.RESET}')
        print(f'{Colors.YELLOW}Current INPUT_PATH: {INPUT_PATH}{Colors.RESET}')
        print(f'{Colors.YELLOW}Please set INPUT_PATH to a folder path in config.py{Colors.RESET}')
        return

    if not OUTPUT_PATH:
        print(f'{Colors.RED}{Colors.BOLD}ERROR: OUTPUT_PATH is not set in config.py{Colors.RESET}')
        return

    # Create output directory
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    os.makedirs(f'{OUTPUT_PATH}/images', exist_ok=True)

    # Supported file types
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.webp', '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.TIFF', '*.WEBP']
    pdf_extensions = ['*.pdf', '*.PDF']

    # Collect all files
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(INPUT_PATH, ext)))

    pdf_files = []
    for ext in pdf_extensions:
        pdf_files.extend(glob.glob(os.path.join(INPUT_PATH, ext)))

    total_files = len(image_files) + len(pdf_files)

    # Print header
    print(f'\n{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}DeepSeek-OCR Folder Batch Processor{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}')
    print(f'{Colors.YELLOW}Input folder:  {Colors.RESET}{INPUT_PATH}')
    print(f'{Colors.YELLOW}Output folder: {Colors.RESET}{OUTPUT_PATH}')
    print(f'{Colors.BLUE}Found: {len(image_files)} image(s), {len(pdf_files)} PDF(s) [{total_files} total]{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}\n')

    if total_files == 0:
        print(f'{Colors.YELLOW}No files to process. Exiting.{Colors.RESET}')
        return

    # Track processed files
    successfully_processed = []
    failed_files = []

    # Save original config
    config_file = os.path.join(os.path.dirname(__file__), 'config.py')
    with open(config_file, 'r', encoding='utf-8') as f:
        original_config = f.read()

    try:
        # Process image files
        if image_files:
            print(f'{Colors.BLUE}{Colors.BOLD}Processing {len(image_files)} image file(s)...{Colors.RESET}\n')

            for idx, image_path in enumerate(image_files, 1):
                file_name = Path(image_path).name
                print(f'{Colors.CYAN}[{idx}/{len(image_files)}]{Colors.RESET} {file_name}')

                # Modify config for this file
                modify_config_file(image_path, OUTPUT_PATH)

                # Run image processing script
                success, output = run_script('run_dpsk_ocr_image.py', image_path, 'image')

                if success:
                    successfully_processed.append(image_path)
                    print(f'{Colors.GREEN}  ✓ Completed{Colors.RESET}\n')
                else:
                    failed_files.append((image_path, output))
                    print(f'{Colors.RED}  ✗ Failed: {output[:100]}{Colors.RESET}\n')

        # Process PDF files
        if pdf_files:
            print(f'{Colors.BLUE}{Colors.BOLD}Processing {len(pdf_files)} PDF file(s)...{Colors.RESET}\n')

            for idx, pdf_path in enumerate(pdf_files, 1):
                file_name = Path(pdf_path).name
                print(f'{Colors.CYAN}[{idx}/{len(pdf_files)}]{Colors.RESET} {file_name}')

                # Modify config for this file
                modify_config_file(pdf_path, OUTPUT_PATH)

                # Run PDF processing script
                success, output = run_script('run_dpsk_ocr_pdf.py', pdf_path, 'pdf')

                if success:
                    successfully_processed.append(pdf_path)
                    print(f'{Colors.GREEN}  ✓ Completed{Colors.RESET}\n')
                else:
                    failed_files.append((pdf_path, output))
                    print(f'{Colors.RED}  ✗ Failed: {output[:100]}{Colors.RESET}\n')

    finally:
        # Always restore original config
        restore_config_file(original_config)

    # Delete successfully processed files
    deleted_count = 0
    if successfully_processed:
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
    print(f'{Colors.GREEN}  ✓ Files deleted: {deleted_count}{Colors.RESET}')

    if failed_files:
        print(f'{Colors.RED}  ✗ Failed: {len(failed_files)} file(s){Colors.RESET}')
        print(f'{Colors.YELLOW}\n  Failed files:{Colors.RESET}')
        for file_path, error in failed_files:
            print(f'{Colors.YELLOW}    - {Path(file_path).name}{Colors.RESET}')

    print(f'{Colors.BLUE}\n  Results saved to: {OUTPUT_PATH}{Colors.RESET}')
    print(f'{Colors.CYAN}{Colors.BOLD}{"=" * 70}{Colors.RESET}\n')


if __name__ == "__main__":
    try:
        process_folder()
    except KeyboardInterrupt:
        print(f'\n{Colors.YELLOW}Process interrupted by user{Colors.RESET}')
        sys.exit(1)
    except Exception as e:
        print(f'{Colors.RED}Unexpected error: {e}{Colors.RESET}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
