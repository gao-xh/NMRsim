# Geometry Warning Fix

**Issue**: QWindowsWindow::setGeometry warnings on splash screen  
**Cause**: Widget with `setFixedSize()` added to parent with different fixed size  
**Solution**: Remove size constraints from child widget, let layout manage it

---

## Problem Description

When launching the application, you may see warnings like:

```
QWindowsWindow::setGeometry: Unable to set geometry 1050x825+753+387 on QWidgetWindow/"SplashScreenClassWindow"
Resulting geometry: 1050x1107+752+387
minimum size: 700x550 maximum size: 700x550
```

---

## Root Cause

**Conflicting Size Constraints**:

1. **Parent Widget** (`SplashScreen`):
   - Set to fixed size: 700x550 (from `config.txt`)
   - `self.setFixedSize(700, 550)`

2. **Child Widget** (`AnimatedLoadingWidget`):
   - Also set to fixed size: 400x400 (from `config.txt`)
   - `self.setFixedSize(400, 400)`

When a child widget with fixed size is added to a parent with different fixed size:
- Qt tries to satisfy both constraints
- Parent's constraint wins (700x550)
- But child's constraint (400x400) creates internal conflict
- Results in geometry calculation warnings

---

## Solution

**Don't set fixed size on child widgets that are managed by layouts.**

### Before (❌ Incorrect):

```python
class AnimatedLoadingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        anim_size = config.get('ANIMATION_SIZE', 400)
        self.setFixedSize(anim_size, anim_size)  # ❌ Conflicts with parent size
        
        container = QWidget()
        container.setFixedSize(anim_size, anim_size)
```

### After (✅ Correct):

```python
class AnimatedLoadingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        anim_size = config.get('ANIMATION_SIZE', 400)
        # ✅ Don't set fixed size on self - let layout manage it
        
        # ✅ Only set size on internal container
        container = QWidget()
        container.setFixedSize(anim_size, anim_size)
```

---

## Key Principles

### 1. **Layout-Managed Widgets**
- If a widget is added to a layout (`addWidget()`), don't use `setFixedSize()`
- Let the layout system calculate the size
- Use size hints or size policies instead

### 2. **Size Constraint Hierarchy**
- **Top-level windows**: Can use `setFixedSize()` (e.g., `SplashScreen`)
- **Layout children**: Should NOT use `setFixedSize()` (e.g., `AnimatedLoadingWidget`)
- **Internal components**: Can use `setFixedSize()` if not in layout (e.g., video widget)

### 3. **Proper Size Control**

Instead of `setFixedSize()` on layout children, use:

```python
# Option 1: Size policy
widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
widget.setMinimumSize(400, 400)
widget.setMaximumSize(400, 400)

# Option 2: Size hints
def sizeHint(self):
    return QSize(400, 400)

# Option 3: Let layout handle it (best for flexible layouts)
# Don't set any size constraints - just let parent manage
```

---

## Testing

After fix, application should start without geometry warnings:

```powershell
.\start.bat
```

Expected output:
- ✅ No `QWindowsWindow::setGeometry` warnings
- ✅ Splash screen displays correctly at 700x550
- ✅ Animation displays at 400x400 centered in splash screen

---

## Related Files

- **Fixed File**: `src/ui/splash_screen.py` (line 160)
- **Configuration**: `config.txt` (SPLASH_WINDOW_WIDTH, SPLASH_WINDOW_HEIGHT, ANIMATION_SIZE)
- **Related**: `docs/troubleshooting/QT_PLUGIN_CONFLICT.md`

---

**Last Updated**: October 9, 2025  
**Status**: ✅ Fixed
