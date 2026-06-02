# Assets Directory

## Structure

```
assets/
├── animations/          # Loading animations, spinners, etc.
├── icons/              # Application icons
├── images/             # Images, logos, backgrounds
└── styles/             # QSS stylesheets (optional)
```

## Loading Animations

Place your loading animation files in `animations/`:

- `animations/loading_circle.png` - Main loading circle
- `animations/loading_arc.png` - Arc/segment animation
- `animations/spinner.gif` - Animated spinner
- etc.

## Usage in Code

```python
import os
from pathlib import Path

# Get assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets"
ANIMATIONS_DIR = ASSETS_DIR / "animations"

# Load animation resources
loading_image = str(ANIMATIONS_DIR / "loading_circle.png")
```

## Supported Formats

- **Images**: PNG, SVG, JPG
- **Icons**: ICO, PNG (with transparency)
- **Animations**: GIF, PNG sequences
