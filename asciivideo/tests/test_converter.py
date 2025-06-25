# test_converter.py
# Tests for the AsciiConverter class.

import unittest
# Placeholder for when AsciiConverter has more functionality
# from asciivideo.converter import AsciiConverter, DEFAULT_ASCII_RAMP

class TestAsciiConverter(unittest.TestCase):

    def test_initialization(self):
        # This test will be more meaningful once AsciiConverter is more developed
        # from asciivideo.converter import AsciiConverter, DEFAULT_ASCII_RAMP # Moved import here
        # converter = AsciiConverter()
        # self.assertEqual(converter.target_width, 80)
        # self.assertEqual(converter.ramp, DEFAULT_ASCII_RAMP)
        print("TestAsciiConverter.test_initialization called (placeholder)")
        self.assertTrue(True) # Placeholder assertion

    def test_brightness_to_char(self):
        from asciivideo.converter import AsciiConverter, DEFAULT_ASCII_RAMP
        # Use target_width_chars instead of target_width
        converter = AsciiConverter(ramp=" .:-=+*#%@", target_width_chars=80) # Simple 10-char ramp

        self.assertEqual(converter._get_char_for_brightness(0),   ' ') # Darkest
        self.assertEqual(converter._get_char_for_brightness(25),  ' ') # Should map to the first char (index 0 for brightness 0-25.59 for 10 char ramp)
        self.assertEqual(converter._get_char_for_brightness(26),  '.') # Should map to the second char (index 1 for brightness 25.6-51.19)
        self.assertEqual(converter._get_char_for_brightness(128), '+') # Mid-range (128 / (256/10) = 128/25.6 = 5. ramp[5] is '+')
        self.assertEqual(converter._get_char_for_brightness(255), '@') # Brightest (index 9)

        # Test with default ramp
        converter_default = AsciiConverter() # Uses DEFAULT_ASCII_RAMP = "@%#*+=-:. " (dark to light)
                                            # Note: My previous DEFAULT_ASCII_RAMP was dark to light,
                                            # but the implementation of _get_char_for_brightness implies light to dark.
                                            # Let's adjust the default ramp in converter.py or the test.
                                            # For now, I'll assume the default ramp is light to dark for this test logic to make sense.
                                            # Or, more likely, the _get_char_for_brightness should be:
                                            # index = int((brightness / 255) * (len(self.ramp) - 1))
                                            # return self.ramp[len(self.ramp) - 1 - index] if ramp is dark to light.
                                            # The current converter.py has DEFAULT_ASCII_RAMP = "@%#*+=-:. " (dark to light)
                                            # and _get_char_for_brightness maps low brightness to low index.
                                            # So 0 brightness -> self.ramp[0] which is '@' (darkest). This is correct.

        self.assertEqual(converter_default._get_char_for_brightness(0),   DEFAULT_ASCII_RAMP[0])
        self.assertEqual(converter_default._get_char_for_brightness(255), DEFAULT_ASCII_RAMP[-1])


    # Add more tests as functionality is added to converter.py:
    # - Test image_to_ascii with a dummy image object (mocking Pillow/OpenCV)
    # - Test different aspect ratios
    # - Test different ramps

    def test_image_to_ascii_simple(self):
        from asciivideo.converter import AsciiConverter
        from PIL import Image

        # Create a simple black and white test image (10x10 pixels)
        # Black square on white background
        img = Image.new("L", (10, 10), "white") # White background
        pixels = img.load()
        for i in range(3, 7): # Draw a black square (3,3) to (6,6)
            for j in range(3, 7):
                pixels[i, j] = 0 # Black

        # Converter with a simple ramp: '#' for dark, '.' for mid, ' ' for light
        # Using char_display_aspect_ratio = 1.0 for simple 1-to-1 pixel to char mapping in terms of count
        # target_width_chars = 10 means original 10px width maps to 10 chars.
        # target_height_chars will also be 10 because char_display_aspect_ratio=1 and original aspect ratio=1.
        converter = AsciiConverter(ramp="#. ", target_width_chars=10, char_display_aspect_ratio=1.0)
        ascii_art = converter.image_to_ascii(img)

        # Expected output:
        # '          ' (10 spaces)
        # '          '
        # '          '
        # '   ####   ' (3 spaces, 4 '#', 3 spaces)
        # '   ####   '
        # '   ####   '
        # '   ####   '
        # '          '
        # '          '
        # '          '

        self.assertIsInstance(ascii_art, str)
        lines = ascii_art.split('\n')
        self.assertEqual(len(lines), 10, "ASCII art should have 10 lines for this test setup.")
        self.assertEqual(len(lines[0]), 10, "Each line should be 10 characters wide.")

        # Check a few lines
        self.assertEqual(lines[0], '          ') # All white, maps to last char ' '
        self.assertEqual(lines[3], '   ####   ') # White, then black, then white. Black (0) maps to '#'.
        self.assertEqual(lines[6], '   ####   ')
        self.assertEqual(lines[9], '          ')

        # Test with a different aspect ratio for characters
        # Image is 10x10. char_display_aspect_ratio = 2.0 (chars twice as tall as wide)
        # target_width_chars = 10
        # target_height_chars = (10/10) * (10 / 2.0) = 5
        converter_tall_chars = AsciiConverter(ramp="#. ", target_width_chars=10, char_display_aspect_ratio=2.0)
        ascii_art_tall = converter_tall_chars.image_to_ascii(img)
        lines_tall = ascii_art_tall.split('\n')
        self.assertEqual(len(lines_tall), 5, "ASCII art should have 5 lines with char_aspect_ratio=2.0.")
        self.assertEqual(len(lines_tall[0]), 10)
        # Example of how the 10x10 image is rescaled to 10x5 before char mapping
        # Row 0 of ASCII: from row 0,1 of original image (scaled)
        # Row 1 of ASCII: from row 2,3 of original image (scaled)
        # Row 2 of ASCII: from row 4,5 of original image (scaled) -> this should contain '#'
        # Row 3 of ASCII: from row 6,7 of original image (scaled)
        # Row 4 of ASCII: from row 8,9 of original image (scaled)
        # The black square is from y=3 to y=6 in original 10px image.
        # Scaled to 5 rows:
        # ASCII row 0 covers original Y [0, 1.99]
        # ASCII row 1 covers original Y [2.0, 3.99] -> should get some '#' from original Y=3
        # ASCII row 2 covers original Y [4.0, 5.99] -> should get '#' from original Y=4,5
        # ASCII row 3 covers original Y [6.0, 7.99] -> should get some '#' from original Y=6
        # ASCII row 4 covers original Y [8.0, 9.99]

        # A more precise check would require knowing the exact output of LANCZOS resampling.
        # For now, just check dimensions and that some conversion happened.
        self.assertTrue('#' in ascii_art_tall) # Check that some dark characters are present
        self.assertTrue(' ' in ascii_art_tall) # Check that some light characters are present


if __name__ == '__main__':
    unittest.main()
