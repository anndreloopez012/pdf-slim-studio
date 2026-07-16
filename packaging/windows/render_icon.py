from pathlib import Path
import sys

from PIL import Image, ImageDraw


def _make_icon() -> Image.Image:
    scale = 4
    size = 256 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Approximate the shared SVG artwork at high resolution, then downsample it.
    for y in range(8 * scale, 248 * scale):
        mix = (y - 8 * scale) / (240 * scale)
        color = tuple(round(a + (b - a) * mix) for a, b in zip((29, 123, 96), (13, 79, 60)))
        draw.line((8 * scale, y, 248 * scale, y), fill=color, width=1)
    draw.rounded_rectangle((8 * scale, 8 * scale, 248 * scale, 248 * scale), radius=56 * scale,
                           outline=(13, 79, 60, 255), width=1)
    draw.ellipse((174 * scale, 26 * scale, 230 * scale, 82 * scale), fill=(229, 118, 58, 242))

    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((70 * scale, 58 * scale, 190 * scale, 208 * scale),
                                  radius=15 * scale, fill=(8, 44, 34, 80))
    shadow = shadow.rotate(7, resample=Image.Resampling.BICUBIC, center=(130 * scale, 133 * scale))
    image.alpha_composite(shadow)

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((70 * scale, 50 * scale, 190 * scale, 200 * scale), radius=15 * scale,
                           fill=(255, 254, 250, 255))
    draw.rounded_rectangle((90 * scale, 85 * scale, 168 * scale, 93 * scale), radius=4 * scale,
                           fill=(23, 35, 31, 255))
    for top, right in ((105, 153), (121, 168), (137, 143)):
        draw.rounded_rectangle((90 * scale, top * scale, right * scale, (top + 6) * scale),
                               radius=3 * scale, fill=(139, 160, 151, 255))
    draw.line((102 * scale, 171 * scale, 157 * scale, 171 * scale), fill=(21, 107, 81, 255),
              width=11 * scale)
    draw.line((143 * scale, 157 * scale, 159 * scale, 171 * scale, 143 * scale, 185 * scale),
              fill=(21, 107, 81, 255), width=10 * scale, joint="curve")
    return image.resize((256, 256), Image.Resampling.LANCZOS)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render_icon.py input.svg output.ico")
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    if not source.is_file():
        raise SystemExit(f"Missing icon source: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    icon = _make_icon()
    icon.save(destination, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                                (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
