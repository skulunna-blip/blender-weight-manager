# -*- coding: utf-8 -*-
"""生成扩展上传图片：icon.png (128x128) + featured.png (1280x720)。

画法：Blender 权重管理器概念图——深灰背景 + 网格平面 + 橙色高亮点
（影响范围高亮），右侧一个面板 mockup（Joints 列表 + 橙色权重条 + 滑块），
示意「C4D 式权重刷」。用 4x 超采样抗锯齿。
"""
from PIL import Image, ImageDraw, ImageFont

SS = 4  # 超采样倍数

# Blender 风格配色
BG_TOP = (36, 36, 36)        # #242424
BG_BOTTOM = (54, 54, 54)     # #363636
GRID = (74, 74, 74)          # 网格线
GRID_DARK = (58, 58, 58)
ORANGE = (255, 168, 56)      # 高亮橙（C4D/选中风格）
ORANGE_DARK = (200, 120, 20)
WHITE = (245, 245, 245)
GRAY = (170, 170, 170)
PANEL = (45, 45, 45)         # 面板底色
PANEL_BORDER = (66, 66, 66)
SLIDER_BG = (30, 30, 30)


def font(path, size, bold=False):
    try:
        if bold:
            return ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", size)
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def draw_grid(dr, x0, y0, x1, y1, nx, ny, dark=True):
    """在矩形区域内画网格线。"""
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        c = GRID_DARK if dark and i % 2 == 0 else GRID
        dr.line([(x, y0), (x, y1)], fill=c, width=1)
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        c = GRID_DARK if dark and j % 2 == 0 else GRID
        dr.line([(x0, y), (x1, y)], fill=c, width=1)


def draw_highlight_dots(dr, x0, y0, x1, y1, nx, ny, seed=7):
    """网格交点上画橙色高亮点（权重>0 的影响范围），点径随机、大小不一。"""
    import random
    rng = random.Random(seed)
    for i in range(nx + 1):
        for j in range(ny + 1):
            if rng.random() < 0.45:
                x = x0 + (x1 - x0) * i / nx
                y = y0 + (y1 - y0) * j / ny
                r = (2 + rng.random() * 3) * SS
                dr.ellipse([x - r, y - r, x + r, y + r], fill=ORANGE)


def make_featured():
    W, H = 1280, 720
    img = Image.new("RGB", (W * SS, H * SS))
    dr = ImageDraw.Draw(img)

    # 背景渐变
    for y in range(H * SS):
        t = y / (H * SS)
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        dr.line([(0, y), (W * SS, y)], fill=c)

    # 左侧网格 + 橙色高亮点（影响范围）
    gx0, gy0, gx1, gy1 = 80 * SS, 200 * SS, 720 * SS, 600 * SS
    draw_grid(dr, gx0, gy0, gx1, gy1, 20, 12)
    draw_highlight_dots(dr, gx0, gy0, gx1, gy1, 20, 12, seed=7)
    # 圈一下选中区（橙色方框，示意选中顶点/面）
    dr.rectangle([gx0 + 6 * SS, gy0 + 4 * SS, gx0 + 10 * SS, gy0 + 6 * SS],
                 outline=ORANGE, width=3 * SS)

    # 右侧面板 mockup
    px0, py0, px1, py1 = 800 * SS, 120 * SS, 1200 * SS, 640 * SS
    dr.rounded_rectangle([px0, py0, px1, py1], radius=10 * SS, fill=PANEL)
    dr.rectangle([px0, py0, px1, py0 + 38 * SS], fill=PANEL_BORDER)
    # 面板标题
    f_title = font(r"C:\Windows\Fonts\arialbd.ttf", 30, bold=True)
    dr.text((px0 + 16 * SS, py0 + 6 * SS), "Weight Mgr", font=f_title, fill=WHITE)

    # Joints 列表行（行名 + 橙色小权重条）
    f_row = font(r"C:\Windows\Fonts\arial.ttf", 24)
    joints = [("Bone_A", 0.8), ("Bone_B", 0.6), ("Bone_C", 0.35), ("Bone_D", 0.0)]
    row_y = py0 + 58 * SS
    bar_x0 = px0 + 150 * SS
    bar_w = px1 - px0 - 180 * SS
    for name, w in joints:
        dr.text((px0 + 16 * SS, row_y), name, font=f_row, fill=GRAY)
        dr.rounded_rectangle([bar_x0, row_y + 4 * SS, bar_x0 + bar_w, row_y + 24 * SS],
                             radius=4 * SS, fill=SLIDER_BG)
        if w > 0:
            dr.rounded_rectangle([bar_x0, row_y + 4 * SS,
                                  bar_x0 + bar_w * w, row_y + 24 * SS],
                                 radius=4 * SS, fill=ORANGE)
        row_y += 34 * SS

    # 底部一个大滑块（Auto Weight 条）
    sl_y = py1 - 76 * SS
    dr.rounded_rectangle([px0 + 16 * SS, sl_y, px1 - 16 * SS, sl_y + 40 * SS],
                         radius=6 * SS, fill=SLIDER_BG)
    dr.rounded_rectangle([px0 + 16 * SS, sl_y,
                          px0 + 16 * SS + (px1 - px0 - 32 * SS) * 0.72, sl_y + 40 * SS],
                         radius=6 * SS, fill=ORANGE)
    dr.text((px0 + 24 * SS, sl_y + 4 * SS), "0.72", font=f_row, fill=(30, 30, 30))

    # 底部标题文字
    f_big = font(r"C:\Windows\Fonts\arialbd.ttf", 58, bold=True)
    f_sub = font(r"C:\Windows\Fonts\arial.ttf", 34)
    dr.text((80 * SS, 620 * SS), "Weight Manager", font=f_big, fill=WHITE)
    dr.text((82 * SS, 680 * SS), "C4D 式权重管理器 · 面板刷权重，精确到每根骨骼", font=f_sub, fill=GRAY)

    img = img.resize((W, H), Image.LANCZOS)
    return img


def make_icon():
    S = 128
    img = Image.new("RGB", (S * SS, S * SS))
    dr = ImageDraw.Draw(img)
    # 圆角深灰背景
    dr.rounded_rectangle([0, 0, S * SS - 1, S * SS - 1], radius=24 * SS, fill=BG_BOTTOM)
    # 中央小网格 + 高亮点
    g = 10 * SS
    gx0, gy0, gx1, gy1 = g, g, S * SS - g, S * SS - g
    draw_grid(dr, gx0, gy0, gx1, gy1, 6, 6)
    draw_highlight_dots(dr, gx0, gy0, gx1, gy1, 6, 6, seed=3)
    # 底部一条橙色权重条
    bw0, bw1 = g, S * SS - g
    dr.rounded_rectangle([bw0, gy1 + 6 * SS, bw1, gy1 + 16 * SS], radius=3 * SS, fill=SLIDER_BG)
    dr.rounded_rectangle([bw0, gy1 + 6 * SS, bw0 + (bw1 - bw0) * 0.6, gy1 + 16 * SS],
                         radius=3 * SS, fill=ORANGE)
    img = img.resize((S, S), Image.LANCZOS)
    return img


def main():
    import os
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(outdir, exist_ok=True)
    make_icon().save(os.path.join(outdir, "icon.png"))
    make_featured().save(os.path.join(outdir, "featured.png"))
    print("[gen] 已生成:")
    for f in ("icon.png", "featured.png"):
        p = os.path.join(outdir, f)
        im = Image.open(p)
        print(f"[gen]   {p}  {im.size}")


if __name__ == "__main__":
    main()
