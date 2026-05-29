"""Generate icon.ico from app-icon.png.

The source PNG is the product icon used by the frontend favicon and splash
screen, so the packaged exe keeps the same visual identity.
"""
from pathlib import Path

from PIL import Image

SIZES = [(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)]


def main():
    source = Path(__file__).with_name("app-icon.png")
    if not source.exists():
        raise FileNotFoundError(f"Missing icon source: {source}")

    img = Image.open(source).convert("RGBA")
    frames = [img.resize(size, Image.Resampling.LANCZOS) for size in SIZES]
    frames[0].save(
        Path(__file__).with_name("icon.ico"),
        format="ICO",
        sizes=SIZES,
        append_images=frames[1:],
    )
    print(f"Generated icon.ico from {source.name}")


if __name__ == "__main__":
    main()
