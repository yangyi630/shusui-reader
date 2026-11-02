"""
生成书髓 PWA 图标
使用 Pillow 生成各个尺寸的图标
"""
from PIL import Image, ImageDraw, ImageFont
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons')
os.makedirs(ICON_DIR, exist_ok=True)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_icon(size):
    """创建指定尺寸的图标"""
    img = Image.new('RGBA', (size, size), (200, 149, 108, 255))
    draw = ImageDraw.Draw(img)

    center = size // 2
    book_w = int(size * 0.55)
    book_h = int(size * 0.7)

    left = center - book_w // 2
    top = center - book_h // 2

    # 书脊
    spine_w = int(size * 0.05)
    draw.rectangle(
        [center - spine_w // 2, top, center + spine_w // 2, top + book_h],
        fill=(166, 117, 72, 255)
    )

    # 左页
    draw.rectangle(
        [left, top, center - spine_w // 2, top + book_h],
        fill=(255, 250, 245, 255),
        outline=(166, 117, 72, 255),
        width=max(2, size // 100)
    )

    # 右页
    draw.rectangle(
        [center + spine_w // 2, top, left + book_w, top + book_h],
        fill=(255, 250, 245, 255),
        outline=(166, 117, 72, 255),
        width=max(2, size // 100)
    )

    # 页边装饰线
    line_color = (200, 149, 108, 180)
    line_width = max(1, size // 200)
    for i in range(3):
        y = top + int(book_h * (0.3 + i * 0.2))
        draw.line(
            [left + int(size * 0.04), y, center - spine_w // 2 - int(size * 0.04), y],
            fill=line_color,
            width=line_width
        )
        draw.line(
            [center + spine_w // 2 + int(size * 0.04), y, left + book_w - int(size * 0.04), y],
            fill=line_color,
            width=line_width
        )

    return img

def main():
    print(f"生成图标到: {ICON_DIR}")
    for size in SIZES:
        img = create_icon(size)
        path = os.path.join(ICON_DIR, f'icon-{size}.png')
        img.save(path, 'PNG')
        print(f"  ✓ icon-{size}.png")
    print("完成！")

if __name__ == '__main__':
    main()
