# Application Icons

This directory contains application icons for the Multi-System ZULF-NMR Simulator.

## Required Icons

### 1. Application Icon (Window Icon)
- **File**: `app_icon.ico` or `app_icon.png`
- **Format**: ICO (Windows) or PNG (cross-platform)
- **Recommended Sizes**: 
  - ICO: 16x16, 32x32, 48x48, 256x256 (multi-resolution)
  - PNG: 256x256 or 512x512
- **Usage**: Window title bar, taskbar

### 2. Splash Screen Logo (Optional)
- **File**: `splash_logo.png`
- **Format**: PNG with transparency
- **Recommended Size**: 128x128 to 256x256
- **Usage**: Centered on splash screen

### 3. Toolbar Icons (Optional)
- **Directory**: `toolbar/`
- **Format**: PNG with transparency
- **Recommended Size**: 24x24 or 32x32
- **Usage**: Toolbar buttons

## How to Create Icons

### Option 1: Use Online Converter
1. Create a high-resolution image (512x512 or larger)
2. Use online tool: https://www.icoconverter.com/
3. Generate ICO file with multiple sizes

### Option 2: Use Python (PIL/Pillow)
```python
from PIL import Image

# Create from PNG
img = Image.open('logo.png')
img.save('app_icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (256,256)])
```

### Option 3: Use ImageMagick
```bash
convert logo.png -define icon:auto-resize=256,128,96,64,48,32,16 app_icon.ico
```

## Icon Design Guidelines

### Colors
- Use project colors (blue/purple theme)
- Ensure good contrast on both light and dark backgrounds

### Design
- Simple and recognizable at small sizes
- Avoid too much detail (16x16 should still be clear)
- Consider using:
  - Molecular structure motif
  - Spin/orbital representation
  - "NMR" or "ZULF" text stylized
  - Combination of atom symbols

### File Naming
- `app_icon.ico` - Main application icon (Windows)
- `app_icon.png` - Main application icon (cross-platform)
- `splash_logo.png` - Splash screen logo
- `{name}_{size}.png` - Specific size variants (e.g., `toolbar_save_32.png`)

## Current Status

⚠️ **No icons currently present**

To add your icons:
1. Place icon files in this directory
2. Update `config.txt` with icon paths
3. Application will automatically load them on next start

## Temporary Solution

If you don't have custom icons yet, the application will:
- Use default Qt window icon (system default)
- Display without custom logo on splash screen
- Function normally without any errors
