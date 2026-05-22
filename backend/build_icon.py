"""Generate icon.ico from the simplified purple logo shape.

The original favicon.svg uses CSS filters, masks, and display-p3 color space
that cairosvg renders as black. This script extracts just the main path and
creates a clean SVG, then converts to a proper multi-size ICO.
"""
import cairosvg
from PIL import Image
import io

# Simplified SVG: just the main diamond/star shape in purple, no filters/masks
SIMPLIFIED_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="48" height="46" viewBox="0 0 48 46">
  <path fill="#7e14ff" d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z"/>
</svg>"""

SIZES = [(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)]


def main():
    # Render simplified SVG to PNG at largest size
    png_data = cairosvg.svg2png(bytestring=SIMPLIFIED_SVG.encode(), output_width=256, output_height=256)
    img = Image.open(io.BytesIO(png_data)).convert("RGBA")

    # Create properly resized versions for each icon size
    frames: list[Image.Image] = []
    for w, h in SIZES:
        # Use LANCZOS for high-quality downscaling
        resized = img.resize((w, h), Image.LANCZOS)
        # Ensure RGBA mode
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")
        frames.append(resized)

    ico_path = "icon.ico"
    # Save with append_images to create a proper multi-frame ICO
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=SIZES,
        append_images=frames[1:],
    )
    print(f"Generated {ico_path} with {len(frames)} frames: {[f'{w}x{h}' for w,h in SIZES]}")


if __name__ == "__main__":
    main()
