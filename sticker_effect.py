"""
给透明背景的 PNG 加贴纸效果:白色描边 + 黑色投影
依赖: Pillow, numpy
不做任何抠图,只利用 PNG 自身的 alpha 通道。

所有尺寸参数默认按**图片短边的百分比**计算,这样不同分辨率的图白边粗细视觉一致。
如需固定像素,用 --outline-px / --blur-px / --dx-px / --dy-px 覆盖。

输出文件统一保存到 `output/` 子文件夹(可用 --output-dir 修改)。

用法:
    1. 直接点 PyCharm 运行按钮 → 自动处理本脚本同目录下所有 PNG
    2. 命令行:   python sticker_effect.py input.png
    3. 批量:     python sticker_effect.py *.png
"""
import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageFilter


# ============== 默认参数(比例,相对图片短边) ==============
OUTLINE_RATIO       = 0.030    # 白边宽度 ≈ 短边 3.0%
SHADOW_BLUR_RATIO   = 0.025    # 阴影模糊半径 ≈ 短边 2.5%
SHADOW_DX_RATIO     = 0.008    # 阴影水平偏移 ≈ 短边 0.8%
SHADOW_DY_RATIO     = 0.008    # 阴影垂直偏移 ≈ 短边 0.8%
SHADOW_OPACITY      = 110      # 阴影不透明度 0~255 (绝对值)

MIN_OUTLINE_PX      = 4        # 白边最少多少像素(避免小图边框消失)
MIN_BLUR_PX         = 3
OUTPUT_SUFFIX       = "_sticker"
OUTPUT_DIR_NAME     = "output"  # 输出子文件夹名称(相对于脚本所在目录)
# ==========================================================


def dilate_alpha(alpha: Image.Image, radius: int) -> Image.Image:
    """把 L 模式的 alpha 蒙版向外扩展 radius 像素(形态学膨胀)。"""
    out = alpha
    remaining = radius
    while remaining >= 4:
        out = out.filter(ImageFilter.MaxFilter(9))
        remaining -= 4
    if remaining > 0:
        out = out.filter(ImageFilter.MaxFilter(2 * remaining + 1))
    return out


def resolve_sizes(w: int, h: int, overrides: dict) -> dict:
    """根据图片尺寸 + 覆盖参数,计算最终使用的像素值。"""
    short = min(w, h)
    return {
        "outline_px":   overrides.get("outline_px")  or max(MIN_OUTLINE_PX, int(short * overrides["outline_ratio"])),
        "shadow_blur":  overrides.get("blur_px")     or max(MIN_BLUR_PX,    int(short * overrides["blur_ratio"])),
        "shadow_dx":    overrides.get("dx_px")       if overrides.get("dx_px") is not None else int(short * overrides["dx_ratio"]),
        "shadow_dy":    overrides.get("dy_px")       if overrides.get("dy_px") is not None else int(short * overrides["dy_ratio"]),
        "shadow_opacity": overrides["opacity"],
    }


def add_sticker_effect(img: Image.Image, sizes: dict) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    alpha = img.split()[-1]

    lo, _ = alpha.getextrema()
    if lo == 255:
        # 图片没有透明区 → 把整张矩形当作"主体",
        # 加矩形白边和矩形阴影(输出画布会变大)。
        print("    ℹ️  这张图 alpha 全 255(没有透明区),按矩形加白边和阴影")

    outline_px = sizes["outline_px"]
    shadow_blur = sizes["shadow_blur"]
    sx, sy = sizes["shadow_dx"], sizes["shadow_dy"]
    shadow_opacity = sizes["shadow_opacity"]

    pad = outline_px + shadow_blur + max(abs(sx), abs(sy)) + 10
    W, H = w + 2 * pad, h + 2 * pad

    subj = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    subj.paste(img, (pad, pad), img)

    big_alpha = Image.new("L", (W, H), 0)
    big_alpha.paste(alpha, (pad, pad))

    # 1) 白色描边
    outline_mask = dilate_alpha(big_alpha, outline_px)
    outline_mask = outline_mask.filter(ImageFilter.GaussianBlur(0.8))
    white_layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    white_layer.putalpha(outline_mask)

    # 2) 黑色阴影
    shadow_base = outline_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
    shadow_shifted = Image.new("L", (W, H), 0)
    shadow_shifted.paste(shadow_base, (sx, sy))
    if shadow_opacity < 255:
        arr = np.asarray(shadow_shifted, dtype=np.float32) * (shadow_opacity / 255.0)
        shadow_shifted = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "L")
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_shifted)

    # 3) 合成
    out = Image.alpha_composite(shadow_layer, white_layer)
    out = Image.alpha_composite(out, subj)
    return out


def process_file(src: str, dst: str, overrides: dict):
    print(f"→ {os.path.basename(src)}")
    img = Image.open(src)
    sizes = resolve_sizes(img.width, img.height, overrides)
    print(f"    (短边 {min(img.size)}px → 白边 {sizes['outline_px']}px, "
          f"阴影模糊 {sizes['shadow_blur']}px, 偏移 ({sizes['shadow_dx']},{sizes['shadow_dy']}))")
    result = add_sticker_effect(img, sizes)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    result.save(dst, "PNG", optimize=True)
    print(f"    ✓ 输出 → {dst}   {result.size}")


def find_pngs_in_script_folder(output_dir: str):
    """找到脚本所在目录下的所有 PNG(跳过 output 目录里的文件)。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    files = []
    for ext in ("*.png", "*.PNG"):
        files.extend(glob.glob(os.path.join(script_dir, ext)))
    unique, seen = [], set()
    output_dir_abs = os.path.abspath(output_dir)
    for f in files:
        key = os.path.normcase(os.path.abspath(f))
        if key in seen:
            continue
        seen.add(key)
        # 跳过输出目录里的文件(防止把已生成的贴纸当输入)
        if os.path.abspath(f).startswith(output_dir_abs + os.sep):
            continue
        # 兼容旧输出命名
        if OUTPUT_SUFFIX in os.path.basename(f):
            continue
        unique.append(f)
    return sorted(unique)


def main():
    ap = argparse.ArgumentParser(description="给 PNG 加白边 + 黑色投影(贴纸效果,按短边比例缩放)")
    ap.add_argument("inputs", nargs="*", help="输入 PNG 文件(留空则处理脚本同目录所有 PNG)")
    ap.add_argument("-o", "--output", help="输出文件名(仅单文件时有效,指定后忽略 --output-dir)")
    ap.add_argument("--output-dir", default=None,
                    help=f"输出目录,默认为脚本同目录下的 '{OUTPUT_DIR_NAME}/'")

    # 比例参数(默认)
    ap.add_argument("--outline-ratio", type=float, default=OUTLINE_RATIO)
    ap.add_argument("--blur-ratio",    type=float, default=SHADOW_BLUR_RATIO)
    ap.add_argument("--dx-ratio",      type=float, default=SHADOW_DX_RATIO)
    ap.add_argument("--dy-ratio",      type=float, default=SHADOW_DY_RATIO)

    # 绝对像素覆盖
    ap.add_argument("--outline-px", type=int, default=None)
    ap.add_argument("--blur-px",    type=int, default=None)
    ap.add_argument("--dx-px",      type=int, default=None)
    ap.add_argument("--dy-px",      type=int, default=None)

    ap.add_argument("--opacity", type=int, default=SHADOW_OPACITY)
    args = ap.parse_args()

    # 确定输出目录:命令行参数 > 默认(脚本同目录下的 output/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = args.output_dir or os.path.join(script_dir, OUTPUT_DIR_NAME)
    output_dir = os.path.abspath(output_dir)

    inputs = args.inputs or find_pngs_in_script_folder(output_dir)
    if not inputs:
        print("没找到任何 PNG 文件。把 PNG 放到脚本同一个文件夹里,再重新运行。")
        sys.exit(1)

    if not args.inputs:
        print(f"未指定输入,扫描 {script_dir}")
        print(f"找到 {len(inputs)} 个 PNG 文件")
    print(f"输出目录: {output_dir}\n")

    overrides = dict(
        outline_ratio=args.outline_ratio,
        blur_ratio=args.blur_ratio,
        dx_ratio=args.dx_ratio,
        dy_ratio=args.dy_ratio,
        outline_px=args.outline_px,
        blur_px=args.blur_px,
        dx_px=args.dx_px,
        dy_px=args.dy_px,
        opacity=args.opacity,
    )

    if args.output and len(inputs) == 1:
        # -o 指定完整输出路径时直接使用
        process_file(inputs[0], args.output, overrides)
    else:
        if args.output:
            print("提示: 多个输入时 -o 被忽略,统一输出到 output-dir\n")
        for p in inputs:
            if not os.path.isfile(p):
                print(f"  ✗ 跳过(文件不存在): {p}")
                continue
            base = os.path.splitext(os.path.basename(p))[0]
            dst = os.path.join(output_dir, base + OUTPUT_SUFFIX + ".png")
            process_file(p, dst, overrides)

    print("\n完成。")


if __name__ == "__main__":
    main()