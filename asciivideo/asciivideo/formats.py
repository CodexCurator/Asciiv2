# formats.py
# Handles the proprietary .asvid format and conversion to standard video.

import json
import os
from .video_utils import FFMPEG_PATH # For re-encoding to standard video
from .audio_utils import combine_video_and_audio # For re-attaching audio
# We'll need Pillow for creating images from text
# from PIL import Image, ImageDraw, ImageFont

# Define constants for .asvid format
ASVID_MAGIC_NUMBER = b"ASVID01" # Simple magic number to identify the file type
ASVID_HEADER_TERMINATOR = b"\n%%HEADER_END%%\n"
ASVID_FRAME_DELIMITER = b"\n%%FRAME_END%%\n" # More robust frame delimiter

class ASVIDExporter:
    def __init__(self, target_width_chars, processed_fps, char_display_aspect_ratio,
                 font_path="DejaVuSansMono.ttf", font_size=10):
        """
        Initializes the ASVIDExporter.
        Args:
            target_width_chars (int): Width of the ASCII art in characters.
            processed_fps (float): FPS of the processed ASCII frames.
            char_display_aspect_ratio (float): Display aspect ratio (height/width) of a single character cell.
            font_path (str): Path to the .ttf font file for rendering MP4s.
            font_size (int): Font size in pixels for rendering MP4s.
        """
        self.target_width_chars = target_width_chars
        # height_chars will be determined by the first frame, assuming all frames have same height.
        self.processed_fps = processed_fps
        self.char_display_aspect_ratio = char_display_aspect_ratio
        self.font_path = font_path
        self.font_size = font_size

    def export_to_asvid(self, ascii_frames, output_asvid_path, original_extracted_audio_path=None):
        """
        Exports ASCII frames and metadata to the .asvid format.

        Args:
            ascii_frames (list[str]): List of multi-line ASCII strings.
            output_asvid_path (str): Path to save the .asvid file.
            original_extracted_audio_path (str, optional): Path to the extracted audio file.
                                                          If provided, its basename is stored.
        Returns:
            bool: True on success, False otherwise.
        """
        if not ascii_frames:
            print("Error: No ASCII frames to export.")
            return False

        # Determine height_chars from the first frame
        # Assuming all frames have the same dimensions (number of lines)
        first_frame_lines = ascii_frames[0].split('\n')
        height_chars = len(first_frame_lines)
        # It's also good to verify that all lines in the first frame have target_width_chars,
        # but self.target_width_chars from init should be the source of truth for width.

        relative_audio_path = None
        if original_extracted_audio_path:
            # Ensure the audio path is relative to the .asvid file's *expected* location if they are meant to be bundled.
            # For simplicity, we often store just the basename and assume it's in the same directory or a known relative path.
            # If the audio file is already in the same directory as the output .asvid file, basename is fine.
            # If output_asvid_path is 'some/dir/video.asvid' and audio is 'some/dir/audio.aac', then basename is fine.
            # If audio is '/tmp/audio.aac', then just basename is not enough for portability.
            # For now, we'll store the basename and advise user to keep them together.
            # A more robust solution might involve copying the audio to be alongside the asvid file.
            relative_audio_path = os.path.basename(original_extracted_audio_path)


        header = {
            "asvid_version": 1,
            "content_type": "ascii_video",
            "target_width_chars": self.target_width_chars,
            "estimated_height_chars": height_chars, # Based on first frame
            "processed_fps": self.processed_fps,
            "total_frames": len(ascii_frames),
            "char_display_aspect_ratio": self.char_display_aspect_ratio,
            "audio_file_hint": relative_audio_path # Store only basename, user must keep them together
        }

        try:
            with open(output_asvid_path, "wb") as f: # Open in binary mode
                f.write(ASVID_MAGIC_NUMBER + b"\n")
                header_json = json.dumps(header, indent=4)
                f.write(header_json.encode('utf-8'))
                f.write(ASVID_HEADER_TERMINATOR)

                for frame_text in ascii_frames:
                    f.write(frame_text.encode('utf-8'))
                    f.write(ASVID_FRAME_DELIMITER) # Use the new delimiter

            print(f"Successfully exported ASCII video to {output_asvid_path}")
            if relative_audio_path:
                print(f"  Audio hint: '{relative_audio_path}'. Ensure this audio file is kept with the .asvid file.")
            return True
        except IOError as e:
            print(f"Error exporting to .asvid file {output_asvid_path}: {e}")
            return False

    def export_to_video(self, ascii_frames, output_video_path, original_audio_path=None, temp_frame_dir="temp_ascii_frames"):
        """
        Converts ASCII frames to images, then compiles them into a standard video file.
        Optionally re-attaches audio.
        """
        # This is a complex step. Requires Pillow.
        # 1. Ensure Pillow is installed.
        # 2. Create temp_frame_dir if it doesn't exist.
        # 3. For each ASCII frame:
        #    a. Determine image size (char_width * font_size_w, char_height * font_size_h)
        #    b. Create a new image with Pillow.
        #    c. Get a drawing context.
        #    d. Select a monospaced font (e.g., Courier New, Consolas). Font availability can be an issue.
        #    e. Draw the ASCII text onto the image.
        #    f. Save the image to temp_frame_dir (e.g., frame_0001.png).
        # 4. Use FFmpeg to create a video from these frames.
        #    ffmpeg -r {fps} -i temp_frame_dir/frame_%04d.png -c:v libx264 -pix_fmt yuv420p temp_video.mp4
        # 5. If original_audio_path is provided, combine temp_video.mp4 and audio_path into output_video_path.
        #    Otherwise, rename/move temp_video.mp4 to output_video_path.
        # 6. Clean up temp_frame_dir.

        print("Exporting to standard video format (Not fully implemented yet - requires Pillow and font handling).")
        print(f"ASCII Frames: {len(ascii_frames)}")
        print(f"Output Path: {output_video_path}")
        print(f"Original Audio: {original_audio_path}")
        print(f"Temp Frame Dir: {temp_frame_dir}")
        # Placeholder for actual implementation
        # raise NotImplementedError("Export to video requires Pillow and detailed image generation logic.")

        from PIL import Image, ImageDraw, ImageFont
        import shutil # For removing temp directory

        if not ascii_frames:
            print("Error: No ASCII frames to export to video.")
            return False

        if not os.path.exists(temp_frame_dir):
            try:
                os.makedirs(temp_frame_dir)
            except OSError as e:
                print(f"Error creating temporary frame directory {temp_frame_dir}: {e}")
                return False

        print(f"Starting export to video: {output_video_path}")
        print(f"Temporary frame directory: {temp_frame_dir}")

        # --- ASCII to Image Conversion ---
        # Determine font and image size
        # Use font_path and font_size from instance variables

        try:
            font = ImageFont.truetype(self.font_path, self.font_size)
            print(f"Using font: {self.font_path} at size {self.font_size}")
        except IOError:
            print(f"Warning: Font '{self.font_path}' not found. Trying a generic monospaced font.")
            try:
                font = ImageFont.truetype("monospace", self.font_size) # Request generic mono from system
                print(f"Using system 'monospace' font at size {self.font_size}")
            except IOError:
                print(f"Error: Generic monospaced font also not found at size {self.font_size}. Cannot render frames.")
                # Fallback to Pillow's default bitmap font if available (usually very basic)
                try:
                    print("Attempting to use Pillow's default bitmap font as a last resort.")
                    font = ImageFont.load_default() # Very basic, not ideal for scaling or style
                except Exception as e_font:
                    print(f"Could not load any font. Error: {e_font}")
                    shutil.rmtree(temp_frame_dir)
                    return False

        # Get text size for one character to determine cell width and height
        # For monospaced fonts, all chars should have roughly the same advance width.
        # bbox = font.getbbox("M") # left, top, right, bottom
        # char_width_px = bbox[2] - bbox[0]
        # char_height_px = bbox[3] - bbox[1] # This is for a single char, line height might be different
        # For line height, getfont().getsize("Py")[1] or textbbox for a full line.
        # Simpler: use textbbox for a line to get height, and for a char to get width.

        # Let's use font.getbbox to determine character cell size.
        # For 'M' (a common wide char), what's its bounding box?
        # (left, top, right, bottom)
        # Using textlength for width might be more accurate for some fonts.
        # For height, a full line like "M\nA" and divide by lines.
        # Or, more simply, assume font_size roughly corresponds to line height.

        # Estimate character cell size. This is tricky with Pillow's font metrics.
        # Let's use getbbox on a sample character. The width can be derived from this.
        # The height is more related to font_size and line spacing.
        # For simplicity, we'll use a fixed multiplier for width based on font_size.
        # A common ratio for monospaced fonts is width ~ 0.6 * height.
        try:
            # Get bounding box for a single character to estimate width
            # For a monospaced font, width of 'M' should be representative.
            char_bbox = font.getmask("M").getbbox() # getbbox of the mask gives (width, height) of the char itself
            if char_bbox:
                 char_width_px = char_bbox[2] # width of the character 'M'
            else: # Fallback if mask is empty for some reason
                 char_width_px = int(self.font_size * 0.6) # Approximate if specific metrics fail
            char_height_px = self.font_size # Assume font_size is a good proxy for line height
        except AttributeError: # .getmask().getbbox() might not work for default font
             char_width_px = int(self.font_size * 0.6)
             char_height_px = self.font_size


        if char_width_px <= 0 or char_height_px <=0:
            print(f"Error: Invalid character dimensions ({char_width_px}x{char_height_px}px). Cannot render.")
            shutil.rmtree(temp_frame_dir)
            return False

        num_cols = len(ascii_frames[0].split('\n')[0]) # Width in chars from first frame
        num_rows = len(ascii_frames[0].split('\n'))    # Height in chars from first frame

        img_width = num_cols * char_width_px
        img_height = num_rows * char_height_px

        # Check for excessively large images
        MAX_DIM = 16384 # Common limit for image dimensions / video codecs
        if img_width > MAX_DIM or img_height > MAX_DIM:
            print(f"Error: Calculated image dimensions ({img_width}x{img_height}) are too large. Max is {MAX_DIM}px.")
            shutil.rmtree(temp_frame_dir)
            return False


        for i, frame_text in enumerate(ascii_frames):
            img = Image.new("RGB", (img_width, img_height), color="black") # Black background
            draw = ImageDraw.Draw(img)

            # Draw text line by line
            lines = frame_text.split('\n')
            for row_idx, line_text in enumerate(lines):
                # Using (0,0) as anchor for textbbox is fine for Pillow >= 9.2.0
                # For older versions, anchor was 'lt'.
                # We'll draw text at (0, row_idx * char_height_px)
                try:
                    draw.text((0, row_idx * char_height_px), line_text, font=font, fill="white") # White text
                except Exception as e_draw:
                    print(f"Error drawing text for frame {i}, line {row_idx}: {e_draw}")
                    # This might happen if font is truly problematic.
                    shutil.rmtree(temp_frame_dir)
                    return False

            frame_filename = os.path.join(temp_frame_dir, f"frame_{i:05d}.png")
            try:
                img.save(frame_filename)
            except Exception as e_save:
                print(f"Error saving frame {frame_filename}: {e_save}")
                shutil.rmtree(temp_frame_dir)
                return False
            if (i+1) % 50 == 0 : print(f"Rendered {i+1}/{len(ascii_frames)} frames to images...")

        print(f"All {len(ascii_frames)} frames rendered to images in {temp_frame_dir}.")

        # --- Image Sequence to Video (FFmpeg) ---
        # Output video without audio first
        temp_video_no_audio_path = os.path.join(temp_frame_dir, "temp_video_no_audio.mp4")

        ffmpeg_cmd_video = [
            FFMPEG_PATH,
            "-framerate", str(self.processed_fps), # Use FPS from ASVIDExporter init
            "-i", os.path.join(temp_frame_dir, "frame_%05d.png"),
            "-c:v", "libx264",    # Common, good quality codec
            "-pix_fmt", "yuv420p", # Important for compatibility
            "-y",                 # Overwrite without asking
            temp_video_no_audio_path
        ]
        print(f"Compiling images into video: {' '.join(ffmpeg_cmd_video)}")
        try:
            subprocess.run(ffmpeg_cmd_video, check=True, capture_output=True, text=True, encoding='utf-8')
            print(f"Temporary video without audio created: {temp_video_no_audio_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error compiling video from frames with FFmpeg: {e}")
            print(f"FFmpeg stdout: {e.stdout}")
            print(f"FFmpeg stderr: {e.stderr}")
            shutil.rmtree(temp_frame_dir)
            return False

        # --- Audio Re-attachment ---
        final_output_succeeded = False
        if original_audio_path and original_audio_path != "no_audio_stream":
            print(f"Attempting to combine video with audio: {original_audio_path}")
            if combine_video_and_audio(temp_video_no_audio_path, original_audio_path, output_video_path):
                print(f"Successfully created final video with audio: {output_video_path}")
                final_output_succeeded = True
            else:
                print(f"Failed to combine video and audio. Video without audio is at: {temp_video_no_audio_path}")
                # As a fallback, copy the no-audio video to the final output path if combining fails
                try:
                    shutil.copy(temp_video_no_audio_path, output_video_path)
                    print(f"Copied video without audio to {output_video_path} as fallback.")
                    final_output_succeeded = True # Or False, depending on if audio was critical
                except Exception as e_copy:
                    print(f"Error copying no-audio video as fallback: {e_copy}")
                    final_output_succeeded = False
        else:
            # No original audio, so the video without audio is the final product
            print("No audio to attach or audio was discarded. Using video without audio.")
            try:
                shutil.move(temp_video_no_audio_path, output_video_path)
                print(f"Final video (no audio) saved as: {output_video_path}")
                final_output_succeeded = True
            except Exception as e_move:
                print(f"Error moving temporary video to final output path {output_video_path}: {e_move}")
                final_output_succeeded = False

        # --- Cleanup ---
        try:
            shutil.rmtree(temp_frame_dir)
            print(f"Temporary frame directory {temp_frame_dir} removed.")
        except OSError as e:
            print(f"Warning: Could not remove temporary frame directory {temp_frame_dir}: {e}")

        return final_output_succeeded


class ASVIDImporter:
    def read_asvid(self, file_path):
        """
        Reads an .asvid file and returns header info and ASCII frames.
        """
        try:
            with open(file_path, "rb") as f:
                magic = f.readline().rstrip(b"\n")
                if magic != ASVID_MAGIC_NUMBER:
                    raise ValueError("Not a valid .asvid file (magic number mismatch).")

                header_lines = []
                while True:
                    line = f.readline()
                    if line.strip() == ASVID_HEADER_TERMINATOR.strip(): # Compare stripped versions
                        break
                    if not line: # EOF before header end
                        raise ValueError("Invalid .asvid file (header terminator not found or premature EOF).")
                    header_lines.append(line.decode('utf-8'))

                header_json = "".join(header_lines)
                header = json.loads(header_json)

                content_after_header = f.read().decode('utf-8')
                # Split frames based on the delimiter we used during export
                ascii_frames = content_after_header.split("\nASCIIVIDEO_FRAME_DELIMITER\n")
                # The last split might result in an empty string if the file ends with the delimiter
                if ascii_frames and not ascii_frames[-1].strip():
                    ascii_frames.pop()

                return header, ascii_frames
        except IOError as e:
            print(f"Error reading .asvid file: {e}")
            return None, None
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing .asvid file: {e}")
            return None, None


if __name__ == '__main__':
    # Example Usage
    exporter = ASVIDExporter(width=80, height=25, fps=10)
    importer = ASVIDImporter()

    # Dummy data
    test_frames = [
        "Frame 1\nLine 2",
        "Frame 2\nLine 2\nLine 3",
        "Frame 3 is cool"
    ]
    test_output_asvid = "test.asvid"
    test_audio = "dummy_audio.aac" # Assume this exists for testing audio path storage

    # Test export
    if exporter.export_to_asvid(test_frames, test_output_asvid, audio_path=test_audio):
        print(f"\nSimulated export of {test_output_asvid} complete.")

        # Test import
        print(f"\nAttempting to import {test_output_asvid}...")
        header, frames = importer.read_asvid(test_output_asvid)
        if header and frames:
            print("Import successful!")
            print("Header:", header)
            print(f"Number of frames imported: {len(frames)}")
            # print("First frame:\n", frames[0])
        else:
            print("Import failed.")

        # Clean up test file
        # if os.path.exists(test_output_asvid):
        #     os.remove(test_output_asvid)

    # Placeholder for video export test
    # exporter.export_to_video(test_frames, "test_output.mp4", original_audio_path=test_audio)
    print("\nformats.py loaded.")
