from PIL import Image, ImageFilter, ImageEnhance, ImageOps

# Character ramps ordered from dark to light
RAMP_STANDARD = "@%#*+=-:. "
RAMP_DETAILED = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
RAMP_BLOCKS = "█▓▒░ "

def convert_to_ascii(
    image_path: str,
    target_width: int = 90,
    aspect_ratio: float = 0.5,
    ramp: str = RAMP_STANDARD,
    edge_enhance: bool = True
) -> str:
    """
    Converts an image to ASCII art with optional edge enhancement for UI/diagram clarity.
    """
    img = Image.open(image_path)
    img = img.convert("L")  # Convert to grayscale

    # Auto aspect ratio scaling
    orig_w, orig_h = img.size
    target_height = int((orig_h / orig_w) * target_width * aspect_ratio)
    target_height = max(1, target_height)

    # Enhance contrast slightly to sharpen visual structures
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)

    if edge_enhance:
        # Detect edges and invert so flat white background remains pure white (255)
        edges = img.filter(ImageFilter.FIND_EDGES)
        inv_edges = ImageOps.invert(edges)
        # Blend inverted edges to sharpen borders without darkening light/white backgrounds
        img = Image.blend(img, inv_edges, 0.2)

    # Resize image
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    if hasattr(img, "get_flattened_data"):
        pixels = list(img.get_flattened_data())
    else:
        pixels = [img.getpixel((x, y)) for y in range(target_height) for x in range(target_width)]

    # Map pixels to ASCII
    num_chars = len(ramp)
    ascii_str = ""
    for i, pixel in enumerate(pixels):
        if i > 0 and i % target_width == 0:
            ascii_str += "\n"
        # Pixel luminance range [0, 255] -> index in ramp [0, num_chars - 1]
        char_idx = int((pixel / 255.0) * (num_chars - 1))
        ascii_str += ramp[char_idx]

    return ascii_str, target_width, target_height
