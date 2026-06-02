# 🎬 加载动画设置指南

## 📋 步骤总览

1. 安装多媒体支持
2. 准备动画文件
3. 放置文件到正确位置
4. 测试运行

---

## 1️⃣ 安装多媒体支持

在 `matlab312` 环境中运行：

```powershell
conda activate matlab312
pip install PySide6-Addons
```

验证安装：
```powershell
python -c "from PySide6.QtMultimedia import QMediaPlayer; print('✓ 多媒体模块安装成功')"
```

---

## 2️⃣ 准备动画文件

您需要两个文件：

### 📹 background.mp4 (背景视频)
- **尺寸**: 300x300 像素（正方形）
- **时长**: 2-5 秒（自动循环）
- **格式**: MP4 (H.264)
- **内容**: 任何循环动画背景

### 🎨 spinach_logo.gif (Spinach Logo)
- **尺寸**: 300x300 像素
- **格式**: GIF（支持透明背景）
- **内容**: 您提供的那个紫色/橙色 Spinach 图标
- **背景**: 透明（这样才能叠加在视频上）

---

## 3️⃣ 放置文件

把两个文件复制到这个文件夹：

```
c:\Users\16179\Desktop\MUI_10_7\assets\animations\
```

最终结构：
```
assets/
└── animations/
    ├── background.mp4        👈 您的 MP4 视频
    ├── spinach_logo.gif      👈 您的 GIF 动画
    └── README.md
```

**重要**: 文件名必须完全一致！

---

## 4️⃣ 测试运行

```powershell
cd c:\Users\16179\Desktop\MUI_10_7
conda activate matlab312
python run.py
```

**预期效果**：
1. 启动画面出现 (600x400 窗口)
2. 中央显示 300x300 的加载动画区域
3. **MP4 视频**在后台循环播放
4. **Spinach GIF**叠加在视频上方旋转
5. 进度条显示初始化进度
6. 初始化完成后打开主窗口

---

## 🔧 如果您还没有这些文件

### 把您的图片转换成 GIF：

**在线工具**:
- https://ezgif.com/maker
- https://gifmaker.me/

**桌面软件**:
- GIMP (免费)
- Photoshop

### 创建背景视频：

**简单方法** - 使用纯色或渐变：
```powershell
# 用 FFmpeg 创建简单的渐变背景（如果有 FFmpeg）
ffmpeg -f lavfi -i "color=c=0x2196F3:s=300x300:d=3" -vf "fade=in:0:30" background.mp4
```

**推荐方法** - 使用视频编辑器：
- DaVinci Resolve (免费)
- Blender (免费，可以做粒子效果)
- Canva (在线，简单)

---

## 💡 临时方案（如果暂时没有文件）

代码已经有**降级方案**：

- **缺少 background.mp4**: 使用白色背景
- **缺少 spinach_logo.gif**: 显示 "Loading..." 文字
- **缺少多媒体模块**: 使用旋转圆圈动画

所以您可以：
1. 先运行看效果（会显示降级版本）
2. 然后逐步添加文件
3. 每次添加文件后重新运行就能看到效果

---

## 🎯 最终效果预览

```
┌──────────────────────────────────────────────┐
│  Multi-System ZULF-NMR Simulator             │
│  Version 3.0 (October 2025)                  │
│  Initializing simulation environment...      │
│                                              │
│     ┌────────────────────────┐               │
│     │  ╔════════════════╗   │               │
│     │  ║   MP4 视频    ║   │               │
│     │  ║   (循环播放)   ║   │               │
│     │  ║               ║   │               │
│     │  ║   🎨 GIF 动画  ║   │               │
│     │  ║   (叠加在上方) ║   │               │
│     │  ╚════════════════╝   │               │
│     └────────────────────────┘               │
│                                              │
│  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░  60%                │
│  Creating 1H-1H validation system...         │
└──────────────────────────────────────────────┘
```

---

## ❓ 常见问题

### Q: GIF 不透明怎么办？
**A**: 使用 GIMP 或 Photoshop 添加透明通道：
- GIMP: `Layer → Transparency → Add Alpha Channel`
- Photoshop: 删除背景图层，保存为 GIF

### Q: 视频太大怎么办？
**A**: 压缩视频：
```bash
ffmpeg -i input.mp4 -vf "scale=300:300" -crf 28 background.mp4
```

### Q: 可以用 PNG 序列吗？
**A**: 目前只支持单个 GIF 文件，如果有 PNG 序列可以转换：
```bash
ffmpeg -framerate 15 -i frame_%03d.png spinach_logo.gif
```

### Q: 动画不流畅？
**A**: 检查：
1. GIF 帧率（推荐 15-30 FPS）
2. 文件大小（建议 < 2MB）
3. 系统性能

---

## 📞 需要帮助？

如果遇到问题，请检查：
1. ✅ 文件名是否完全正确
2. ✅ 文件是否在正确的文件夹
3. ✅ PySide6-Addons 是否安装
4. ✅ 文件是否损坏（尝试在其他程序打开）

运行诊断：
```powershell
python -c "from pathlib import Path; print('MP4:', (Path('assets/animations/background.mp4')).exists()); print('GIF:', (Path('assets/animations/spinach_logo.gif')).exists())"
```
