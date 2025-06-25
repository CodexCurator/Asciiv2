# main.py
# This will be the entry point for the CLI.

import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Ultra High Definition Video to ASCII Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows default values in help
    )
    parser.add_argument("input_video", help="Path to the input video file.")
    parser.add_argument("-o", "--output", help="Path to the output file (type depends on --format).")

    # ASCII conversion parameters
    parser.add_argument("--width", type=int, default=100, help="Width of the ASCII output in characters.")
    parser.add_argument("--char_aspect_ratio", type=float, default=2.0,
                        help="Display aspect ratio of a single character (height/width). "
                             "Typical console fonts are ~2.0 (e.g., 8px W x 16px H). Use 1.0 for square cells.")
    parser.add_argument("--ramp", type=str, default="@%#*+=-:. ",
                        help="ASCII character ramp from darkest to lightest.")

    # Video processing parameters
    parser.add_argument("--fps", type=float, default=None,
                        help="Target FPS for processing. If None, uses original video FPS. "
                             "Lower values process fewer frames.")

    parser.add_argument("--out_format", choices=['asvid', 'mp4', 'none'], default='asvid',
                        help="Output format: 'asvid' for proprietary ASCII video, "
                             "'mp4' for standard video (requires rendering frames to images first - future step), "
                             "'none' to only print first frame (for debugging).")

    parser.add_argument("--audio", choices=['keep', 'discard'], default='keep',
                        help="Action for the audio track: 'keep' to extract and potentially re-attach, "
                             "'discard' to ignore audio.")

    # Font options for MP4 output
    parser.add_argument("--font_path", type=str, default="DejaVuSansMono.ttf",
                        help="Path to the .ttf font file for rendering MP4 output. "
                             "Fallback to 'monospace' then Pillow default if not found.")
    parser.add_argument("--font_size", type=int, default=10,
                        help="Font size in pixels for rendering MP4 output.")

    args = parser.parse_args()

    print(f"Input video: {args.input_video}")
    if args.output:
        print(f"Output file: {args.output}")
    print(f"Target ASCII width: {args.width} chars")
    print(f"Character display AR: {args.char_aspect_ratio}")
    print(f"Target processing FPS: {'Original' if args.fps is None else args.fps}")

    # Initialize AsciiConverter
    from .converter import AsciiConverter
    converter = AsciiConverter(
        ramp=args.ramp,
        target_width_chars=args.width,
        char_display_aspect_ratio=args.char_aspect_ratio
    )

    # Process video frames
    from .video_utils import process_video_frames, get_video_info

    video_info = get_video_info(args.input_video)
    if not video_info:
        print(f"Could not get video info for {args.input_video}. Exiting.")
        return

    print(f"Original video info: {video_info['width']}x{video_info['height']}, FPS: {video_info['fps_str']}")

    extracted_audio_path = None
    if args.audio == 'keep':
        from .audio_utils import extract_audio
        print("\nAttempting to extract audio...")
        # For now, save extracted audio in the same dir as input video
        # Later, this might go to a temp dir or alongside the output file.
        extracted_audio_path = extract_audio(args.input_video, output_dir=os.path.dirname(args.output) if args.output else None)
        if extracted_audio_path == "no_audio_stream":
            print("Video has no audio stream.")
            extracted_audio_path = None # Ensure it's None, not the string
        elif extracted_audio_path:
            print(f"Audio successfully extracted to: {extracted_audio_path}")
        else:
            print("Audio extraction failed or was skipped.")
            # Decide if this is a fatal error or if we can proceed without audio. For now, proceed.
    else:
        print("\nAudio processing is set to 'discard'. Skipping audio extraction.")


    # The frame_processor_callback is converter.image_to_ascii
    print("\nStarting ASCII conversion for video frames...")
    ascii_frames, processed_fps = process_video_frames(
        args.input_video,
        converter.image_to_ascii, # Pass the method directly
        target_fps=args.fps
    )

    if ascii_frames:
        print(f"\nSuccessfully processed {len(ascii_frames)} frames into ASCII art at ~{processed_fps:.2f} FPS.")
        print(f"Each ASCII frame is {args.width} characters wide.")

        if args.out_format == 'asvid':
            if not args.output:
                print("Error: Output file path (-o) is required for .asvid format.")
            else:
                from .formats import ASVIDExporter
                exporter = ASVIDExporter(
                    target_width_chars=args.width,
                    processed_fps=processed_fps,
                    char_display_aspect_ratio=args.char_aspect_ratio,
                    font_path=args.font_path,
                    font_size=args.font_size
                )
                success = exporter.export_to_asvid(
                    ascii_frames,
                    args.output,
                    original_extracted_audio_path=extracted_audio_path
                )
                if success:
                    print(f"ASCII video saved to {args.output}")
                else:
                    print(f"Failed to save ASCII video to {args.output}")

        elif args.out_format == 'mp4':
            if not args.output:
                print("Error: Output file path (-o) is required for .mp4 format.")
            else:
                # ASVIDExporter instance 'exporter' is already created
                print(f"\nAttempting to export to MP4 video: {args.output}")
                temp_frame_dir = "temp_ascii_render_frames" # Could be made configurable or more unique
                success = exporter.export_to_video(
                    ascii_frames,
                    args.output,
                    original_audio_path=extracted_audio_path,
                    temp_frame_dir=temp_frame_dir
                )
                if success:
                    print(f"Video successfully saved to {args.output}")
                else:
                    print(f"Failed to save video to {args.output}")

        elif args.out_format == 'none': # For debugging
            print("\nFirst ASCII frame (output_format='none'):")
            print(ascii_frames[0])
            if extracted_audio_path and extracted_audio_path != "no_audio_stream":
                 print(f"(Audio was extracted to: {extracted_audio_path})")

    else: # if not ascii_frames
        print("No frames were processed.")


if __name__ == "__main__":
    main()
