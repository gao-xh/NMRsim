"""
PNG to ICO Converter

Converts a PNG image to multi-resolution ICO file for Windows application icons.

Usage:
    python scripts/png_to_ico.py <input.png> [output.ico]

Examples:
    python scripts/png_to_ico.py my_icon.png
    python scripts/png_to_ico.py my_icon.png assets/icons/app_icon.ico
"""

import sys
from pathlib import Path

def convert_png_to_ico(input_path, output_path=None):
    """
    Convert PNG to ICO with multiple resolutions
    
    Args:
        input_path: Path to input PNG file
        output_path: Path to output ICO file (optional)
    """
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow library not installed")
        print("Install with: pip install Pillow")
        sys.exit(1)
    
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    if not input_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']:
        print(f"Error: Input file must be an image (PNG, JPG, BMP)")
        sys.exit(1)
    
    # Determine output path
    if output_path is None:
        output_path = input_path.with_suffix('.ico')
    else:
        output_path = Path(output_path)
    
    print(f"Converting: {input_path}")
    print(f"Output to: {output_path}")
    
    # Load image
    try:
        img = Image.open(input_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create multi-resolution ICO
        # Windows recommends: 16x16, 32x32, 48x48, 256x256
        sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
        
        print(f"\nGenerating ICO with resolutions: {', '.join([f'{w}x{h}' for w, h in sizes])}")
        
        # Save as ICO
        img.save(output_path, format='ICO', sizes=sizes)
        
        print(f"\n✅ Success! ICO file created: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during conversion: {e}")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nQuick start:")
        print("  1. Place your PNG file in assets/icons/")
        print("  2. Run: python scripts/png_to_ico.py assets/icons/your_icon.png")
        print("  3. This will create: assets/icons/your_icon.ico")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_png_to_ico(input_file, output_file)


if __name__ == "__main__":
    main()
