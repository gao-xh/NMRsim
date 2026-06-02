# 🎬 Loading Animations

## 📁 Required Files

Place these two files in this directory:

1. **background.mp4** - Background video (looping)
2. **spinach_logo.gif** - Spinach logo animation (overlay)

## 📐 Recommended Specifications

### background.mp4
- **Resolution**: 300x300 pixels (or any square aspect ratio)
- **Duration**: 2-5 seconds (will loop automatically)
- **Format**: MP4 (H.264 codec recommended)
- **Size**: Keep under 5MB for fast loading
- **Content**: Abstract background, particle effects, or any looping animation

### spinach_logo.gif
- **Resolution**: 300x300 pixels (or transparent PNG with same size)
- **Format**: GIF with transparency support
- **Frame rate**: 10-30 FPS
- **Content**: Your Spinach logo with transparent background
- **Size**: Keep under 2MB

## 🎨 Current Setup

```
assets/animations/
├── background.mp4        👈 Put your MP4 video here
├── spinach_logo.gif      👈 Put your GIF animation here
└── README.md             (this file)
```

## 🔧 How It Works

The splash screen will:
1. Load **background.mp4** as the base layer (looping video)
2. Overlay **spinach_logo.gif** on top (centered, transparent background)
3. Both animations play simultaneously
4. Video is muted automatically
5. GIF scales to 300x300 pixels

## 🎯 Fallback Behavior

If files are missing:
- **No background.mp4**: Shows plain white background
- **No spinach_logo.gif**: Shows "Loading..." text
- **No multimedia support**: Falls back to basic loading indicator

## 💡 Tips

1. **For best results**: Use transparent background in GIF
2. **File naming**: Must match exactly (`background.mp4`, `spinach_logo.gif`)
3. **Testing**: Run `python run.py` to see the animation
4. **Optimization**: Compress videos with HandBrake or FFmpeg
5. **GIF creation**: Use GIMP, Photoshop, or online tools

## 🔄 Converting Formats

### Create GIF from video:
```bash
ffmpeg -i input.mp4 -vf "scale=300:300" -r 15 spinach_logo.gif
```

### Compress MP4:
```bash
ffmpeg -i input.mp4 -vf "scale=300:300" -c:v libx264 -crf 28 background.mp4
```

### Add transparency to GIF:
Use GIMP → Layer → Transparency → Add Alpha Channel
