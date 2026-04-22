# StickerMaker

一个简单的 Python 小工具,给透明背景的 PNG 图片添加 **白色描边 + 黑色投影**,一键把普通 PNG 变成 iOS / iMessage 风格的贴纸。

不做抠图,只利用 PNG 自身的 alpha 通道。所有尺寸参数按**图片短边的百分比**计算,不同分辨率的图片产出视觉一致。

## 效果预览

| 原图 (透明背景 PNG) | 处理后 |
| :---: | :---: |
| 主体 + 透明背景 | 主体 + 白色描边 + 柔和黑色投影 |

## 环境要求

- Python 3.7+
- Pillow
- numpy

安装依赖:

```bash
pip install Pillow numpy
```

## 使用方法

### 方式一:在 PyCharm / VS Code 里直接运行

1. 把所有要处理的 PNG 放到 `sticker_effect.py` 同一个文件夹
2. 右键 → Run,或点编辑器里的运行按钮
3. 结果出现在同目录的 `output/` 子文件夹里

### 方式二:命令行

```bash
# 处理脚本同目录下所有 PNG
python sticker_effect.py

# 处理指定文件
python sticker_effect.py input.png

# 批量
python sticker_effect.py *.png

# 单文件指定输出路径
python sticker_effect.py input.png -o mysticker.png
```

## 参数说明

所有尺寸默认按图片**短边的百分比**计算,保证不同分辨率图片效果一致。

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--outline-ratio` | `0.030` | 白边宽度占短边的比例(3%) |
| `--blur-ratio` | `0.025` | 阴影模糊半径占短边的比例 |
| `--dx-ratio` | `0.008` | 阴影水平偏移占短边的比例 |
| `--dy-ratio` | `0.008` | 阴影垂直偏移占短边的比例 |
| `--opacity` | `110` | 阴影不透明度 (0-255) |
| `--output-dir` | `output` | 输出目录 |

如需固定像素(不随图片缩放),使用绝对像素覆盖:

| 参数 | 说明 |
| --- | --- |
| `--outline-px` | 白边宽度(像素) |
| `--blur-px` | 阴影模糊半径(像素) |
| `--dx-px` / `--dy-px` | 阴影偏移(像素) |

### 示例

```bash
# 白边更粗、阴影更深
python sticker_effect.py --outline-ratio 0.04 --opacity 150

# 某张图用固定像素
python sticker_effect.py IMG_0941.png --outline-px 50

# 输出到自定义目录
python sticker_effect.py --output-dir ~/Desktop/my_stickers
```

## 输入要求

**输入必须是真正透明背景的 PNG(RGBA 模式)。** 如果 PNG 的 alpha 通道全为 255(即完全不透明,黑边其实是真实黑像素),脚本会打印警告并跳过——白边和阴影没地方画。

**怎么拿到透明背景 PNG?**

- **iOS**:打开照片 App → 长按主体自动抠图 → **拖拽**(不是复制)到"备忘录" → 长按图片"存储到照片"
- **macOS**:预览.app 可以用"即时 Alpha"工具去背景后导出 PNG
- **抠图网站**:remove.bg、Adobe Express 免费抠图等
- **Python 里**可以用 [rembg](https://github.com/danielgatis/rembg) 批量去背景

## 项目结构

```
StickerMaker/
├── sticker_effect.py      # 主脚本
├── README.md
├── IMG_xxxx.png           # 待处理的 PNG
└── output/                # 处理结果(自动创建)
    └── IMG_xxxx_sticker.png
```

## 实现原理

1. 读取 PNG 的 alpha 通道作为主体蒙版
2. 对蒙版做**形态学膨胀**(向外扩展 N 像素)→ 得到描边蒙版
3. 描边蒙版填白色 → 白边图层
4. 描边蒙版做**高斯模糊** + 偏移 + 降不透明度 → 阴影图层
5. 从下到上合成:阴影 → 白边 → 原图主体

## License

MIT