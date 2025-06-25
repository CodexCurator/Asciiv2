# converter.py
# Handles the conversion of image frames to ASCII art.

from PIL import Image

DEFAULT_ASCII_RAMP = "@%#*+=-:. " # A common ramp, from dark (dense) to light (sparse)
# A longer, perhaps more nuanced ramp:
# DEFAULT_ASCII_RAMP = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. " # Dark to light
# For testing, let's stick to the shorter one for now.

class AsciiConverter:
    def __init__(self, ramp=None, target_width_chars=80, char_display_aspect_ratio=2.0):
        """
        Initializes the AsciiConverter.
        Args:
            ramp (str, optional): The string of characters to use for mapping brightness.
                                  Should generally be ordered from darkest/densest to lightest/sparsest.
            target_width_chars (int, optional): The desired width of the ASCII art in characters.
            char_display_aspect_ratio (float, optional): The display aspect ratio of a single character cell
                                                       (cell_height / cell_width). Used to adjust image
                                                       scaling to make the final ASCII art look proportional
                                                       to the original image.
                                                       - For typical console fonts (e.g., 8px wide, 16px tall),
                                                         this would be 16/8 = 2.0.
                                                       - For square character cells (e.g. in some editors or
                                                         when rendering to an image with square cells), use 1.0.
                                                       Defaults to 2.0.
        """
        self.ramp = ramp or DEFAULT_ASCII_RAMP
        self.target_width_chars = target_width_chars
        self.char_display_aspect_ratio = char_display_aspect_ratio
        if not self.ramp:
            raise ValueError("ASCII character ramp cannot be empty.")

    def image_to_ascii(self, image_path_or_object):
        """
        Converts a single image (from path or Pillow Image object) to an ASCII string.
        """
        try:
            if isinstance(image_path_or_object, str):
                img = Image.open(image_path_or_object)
            elif isinstance(image_path_or_object, Image.Image):
                img = image_path_or_object
            else:
                raise TypeError("Input must be a file path or a Pillow Image object.")
        except FileNotFoundError:
            return f"Error: Image file not found at {image_path_or_object}"
        except Exception as e:
            return f"Error loading image: {e}"

        # 1. Resize image to target_width_chars, maintaining aspect ratio for height.
        original_width, original_height = img.size

        # Adjust for character aspect ratio to make the image look proportional in ASCII
        # If char_aspect_ratio is 0.5 (chars are twice as tall as wide),
        # we need fewer rows of characters for the same visual height.
        # So, the effective height for scaling is original_height * char_aspect_ratio.
        aspect_ratio = original_height / original_width
        # New height in pixels, before considering char aspect ratio for character grid
        # target_height_pixels_equivalent = aspect_ratio * self.target_width_chars

        # Now, calculate target height in characters
        # new_width_pixels = self.target_width_chars (each char is 1 pixel wide in this scaled image)
        # new_height_pixels = original_height * (self.target_width_chars / original_width)
        # target_height_chars = new_height_pixels * self.char_aspect_ratio
        # (No, this is simpler: target_height_chars should be proportional to target_width_chars, adjusted by aspect ratios)

        # The target dimensions for the intermediate pixel image (before ASCII mapping)
        # Width is target_width_chars (one pixel per char column)
        # Height needs to be calculated based on original aspect ratio and char aspect ratio
        # (target_char_height / target_char_width) = (original_pixel_height / original_pixel_width) * (1 / char_pixel_width_per_char_cell_aspect_ratio)
        # target_height_chars = (original_height / original_width) * self.target_width_chars * self.char_aspect_ratio

        # Let scaled image width be `w_scaled_px` and height be `h_scaled_px`.
        # We want `w_scaled_px = self.target_width_chars`.
        # To maintain image aspect ratio: `h_scaled_px / w_scaled_px = original_height / original_width`.
        # So, `h_scaled_px = (original_height / original_width) * self.target_width_chars`.
        # This `h_scaled_px` is the number of rows of pixels in the intermediate scaled image.
        # Each of these rows will become a row of ASCII characters.
        # The visual aspect ratio of the final ASCII art will be:
        # (num_char_rows * char_cell_height) / (num_char_cols * char_cell_width)
        # = (h_scaled_px * char_cell_height) / (self.target_width_chars * char_cell_width)
        # = (h_scaled_px / self.target_width_chars) * (char_cell_height / char_cell_width)
        # = (h_scaled_px / self.target_width_chars) * (1 / self.char_aspect_ratio) if char_aspect_ratio = char_width/char_height
        # If char_aspect_ratio = char_height / char_width (as defined in constructor):
        # = (h_scaled_px / self.target_width_chars) * self.char_aspect_ratio
        # We want this to be `original_height / original_width`.
        # So, `(h_scaled_px / self.target_width_chars) * self.char_aspect_ratio = original_height / original_width`
        # `h_scaled_px = (original_height / original_width) * self.target_width_chars / self.char_aspect_ratio`

        # Let's redefine char_aspect_ratio to be more intuitive:
        # char_display_height_factor: how much taller a char is than it is wide (e.g., 2.0 for typical console).
        # If we use self.char_aspect_ratio = char_cell_pixel_height / char_cell_pixel_width
        # target_height_chars = (original_pixel_height / original_pixel_width) * self.target_width_chars / self.char_aspect_ratio

        # Simpler: calculate target height in characters directly.
        # The number of rows of characters should be such that:
        # (target_height_chars / target_width_chars) approx = (original_height / (original_width * character_width_compensation_factor))
        # character_width_compensation_factor is how many times wider a character cell is than it is tall.
        # If char_aspect_ratio = height/width of a char cell (e.g. 0.5 means char cell is twice as wide as it is tall, or font is condensed)
        # If char_aspect_ratio = 2.0 means char cell is twice as tall as it is wide (typical console)
        # Let's assume the constructor's char_aspect_ratio means: actual_char_height / actual_char_width on screen.
        # A typical terminal char cell might be 8px wide, 16px tall. So char_aspect_ratio = 16/8 = 2.0.
        # To make the ASCII art aspect ratio match the image aspect ratio:
        # (num_ascii_rows * char_actual_height) / (num_ascii_cols * char_actual_width) = original_pixel_height / original_pixel_width
        # num_ascii_rows / num_ascii_cols * char_aspect_ratio = original_pixel_height / original_pixel_width
        # num_ascii_rows = (original_pixel_height / original_pixel_width) * num_ascii_cols / char_aspect_ratio

        # Let's adjust the definition of char_aspect_ratio in the class docstring for clarity if needed.
        # Assuming current char_aspect_ratio = char_pixel_height / char_pixel_width.
        # For example, if a character is 8px wide and 16px tall, char_aspect_ratio = 16/8 = 2.0.
        # To maintain the original image's visual aspect ratio:
        # (target_height_chars * char_pixel_height) / (target_width_chars * char_pixel_width) = original_height / original_width
        # (target_height_chars / target_width_chars) * self.char_aspect_ratio = original_height / original_width
        # target_height_chars = (original_height / original_width) * (self.target_width_chars / self.char_aspect_ratio)

        # The image should be resized to (self.target_width_chars, target_height_chars_for_pixels)
        # where target_height_chars_for_pixels is the number of pixel rows that will become character rows.
        if self.char_display_aspect_ratio <= 0: # Avoid division by zero or negative
            effective_char_display_aspect_ratio = 1.0
        else:
            effective_char_display_aspect_ratio = self.char_display_aspect_ratio

        # Calculate the target height for the resampled image (in pixels, which will map 1-to-1 to characters)
        # such that the final ASCII art has the correct visual aspect ratio.
        target_height_chars_float = (original_height / original_width) * \
                                    (self.target_width_chars / effective_char_display_aspect_ratio)
        target_height_chars = max(1, int(target_height_chars_float)) # Ensure at least 1 char high

        # Resample the image to these character dimensions.
        # Each pixel in this resampled image will correspond to one ASCII character.
        img_resized = img.resize((self.target_width_chars, target_height_chars), Image.Resampling.LANCZOS)

        # 2. Convert to grayscale.
        img_gray = img_resized.convert("L")

        # 3. Iterate over pixels.
        ascii_rows = []
        pixels = img_gray.load()
        for y in range(target_height_chars):
            row_chars = []
            for x in range(self.target_width_chars):
                brightness = pixels[x, y]
                # 4. Map brightness to ASCII character.
                row_chars.append(self._get_char_for_brightness(brightness))
            ascii_rows.append("".join(row_chars))

        # 5. Assemble the ASCII string.
        return "\n".join(ascii_rows)


    def _get_char_for_brightness(self, brightness):
        """
        Maps a brightness value (0-255) to an ASCII character.
        Brightness 0 should map to the first character in the ramp.
        Brightness 255 should map to the last character in the ramp.
        """
        # Ensure brightness is within bounds
        brightness = max(0, min(brightness, 255))

        # Calculate the index
        num_chars = len(self.ramp)
        if num_chars == 0:
            return '' # Or raise error
        if num_chars == 1:
            return self.ramp[0]

        # Map the brightness (0-255) to an index in the ramp (0 to num_chars-1)
        # Each character represents a slice of the brightness range.
        # The size of each slice is 256 / num_chars
        # Example: 10 chars. Slice size = 25.6
        # Brightness 0-25.59 -> index 0
        # Brightness 25.6-51.19 -> index 1
        index = int(brightness / (256 / num_chars))

        # Ensure index is within bounds (it should be, but as a safeguard)
        index = max(0, min(index, num_chars - 1))

        return self.ramp[index]

if __name__ == '__main__':
    # Example usage (for testing during development)
    converter = AsciiConverter()
    # Simulate a brightness value
    char = converter._get_char_for_brightness(0) # Darkest
    print(f"Brightness 0 -> '{char}'")
    char = converter._get_char_for_brightness(128) # Mid
    print(f"Brightness 128 -> '{char}'")
    char = converter._get_char_for_brightness(255) # Brightest
    print(f"Brightness 255 -> '{char}'")
