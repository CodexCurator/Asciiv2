# audio_utils.py
# Utilities for audio processing using FFmpeg.

import subprocess
import os

import json # For parsing ffprobe output

# Assuming video_utils.py contains FFMPEG_PATH and FFPROBE_PATH
from .video_utils import FFMPEG_PATH, FFPROBE_PATH


def extract_audio(video_path, output_dir=None, filename_prefix="extracted_audio_"):
    """
    Extracts audio from a video file using FFmpeg.
    Saves the audio to a file. The output filename will attempt to use an extension
    based on the detected audio codec, defaulting to '.aac'.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str, optional): Directory to save the extracted audio.
                                    Defaults to the same directory as the input video.
        filename_prefix (str, optional): Prefix for the extracted audio filename.

    Returns:
        str: The path to the extracted audio file if successful.
        "no_audio_stream": If the video explicitly contains no audio stream.
        None: If any other error occurs.
    """
    audio_codec_extension = 'aac' # Default fallback extension

    # Probe for audio stream info to get a better extension
    ffprobe_command = [
        FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "a", # Select only audio streams
        video_path
    ]
    try:
        result = subprocess.run(ffprobe_command, capture_output=True, text=True, check=True, encoding='utf-8')
        streams_info = json.loads(result.stdout)
        audio_streams = streams_info.get("streams", [])
        if not audio_streams:
            print(f"No audio streams found in {video_path} by ffprobe.")
            # It's possible ffprobe doesn't list streams if the container is unusual but audio exists.
            # FFmpeg call later will be the final arbiter.
            # However, if ffprobe is definite, we can trust it.
            # For safety, we can let ffmpeg try, but this is a good early indicator.
            pass # Continue to let ffmpeg try, but we won't have a good extension.

        if audio_streams: # If we found audio streams
            codec_name = audio_streams[0].get("codec_name")
            if codec_name:
                codec_map = {
                    "aac": "aac", "mp3": "mp3", "vorbis": "ogg",
                    "opus": "opus", "flac": "flac", "ac3": "ac3",
                    "eac3": "eac3", "dts": "dts", "pcm_s16le": "wav"
                    # Add more mappings if needed
                }
                audio_codec_extension = codec_map.get(codec_name, audio_codec_extension)
    except subprocess.CalledProcessError as e:
        stderr_str = e.stderr.lower() if e.stderr else ""
        if "does not have any audio stream" in stderr_str or "could not find stream" in stderr_str : # typical ffprobe messages for no audio
             print(f"ffprobe indicates no audio stream in {video_path}.")
             # We will return "no_audio_stream" based on ffmpeg's final say, as ffprobe might sometimes be wrong
             # or ffmpeg might handle obscure cases better.
        else:
            print(f"ffprobe failed for {video_path}. Proceeding with default audio extension. Error: {e.stderr}")
    except json.JSONDecodeError:
        print(f"Error decoding ffprobe JSON output for {video_path}. Defaulting audio extension.")
    except Exception as e:
        print(f"Unexpected error during ffprobe for {video_path}: {e}. Defaulting audio extension.")


    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_filename = f"{filename_prefix}{base_name}.{audio_codec_extension}"

    target_dir = output_dir if output_dir else (os.path.dirname(video_path) or '.')
    if target_dir and not os.path.exists(target_dir): # Ensure target_dir is not empty string if dirname is empty
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating output directory {target_dir}: {e}")
            return None

    final_output_audio_path = os.path.join(target_dir, output_filename)

    if os.path.exists(final_output_audio_path):
        print(f"Output audio file {final_output_audio_path} already exists. Overwriting.")
        try:
            os.remove(final_output_audio_path)
        except OSError as e:
            print(f"Error removing existing audio file {final_output_audio_path}: {e}")
            return None

    ffmpeg_command = [
        FFMPEG_PATH,
        "-i", video_path,
        "-vn",              # No video
        "-acodec", "copy",  # Copy audio stream directly
        "-y",               # Overwrite output files without asking
        final_output_audio_path
    ]
    try:
        # Before running ffmpeg, check if ffprobe already told us there are no audio streams.
        # This check is a bit redundant if ffprobe logic above is perfect, but acts as a belt-and-suspenders.
        # For now, we let ffmpeg try, as it's the ultimate test.
        process = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True, encoding='utf-8')
        if os.path.exists(final_output_audio_path) and os.path.getsize(final_output_audio_path) > 0:
            print(f"Audio extracted to {final_output_audio_path}")
            return final_output_audio_path
        else:
            # FFmpeg might succeed (return code 0) but produce no file or an empty file if no audio stream.
            # This can happen with -acodec copy.
            print(f"FFmpeg ran but produced no valid audio output for {video_path}. Assuming no audio stream.")
            if os.path.exists(final_output_audio_path):
                try: os.remove(final_output_audio_path)
                except OSError: pass
            return "no_audio_stream"

    except subprocess.CalledProcessError as e:
        stderr_str = e.stderr.lower() if e.stderr else ""
        # Common ffmpeg messages indicating no audio stream
        no_audio_messages = [
            "does not contain an audio stream", "audio stream not found",
            "could not find audio stream", "output file #0 does not contain any stream"
        ]
        if any(msg in stderr_str for msg in no_audio_messages):
            print(f"Video file {video_path} does not contain an audio stream (confirmed by ffmpeg).")
            if os.path.exists(final_output_audio_path): # Clean up potentially empty file
                try:
                    if os.path.getsize(final_output_audio_path) == 0:
                        os.remove(final_output_audio_path)
                        print(f"Removed empty audio artifact: {final_output_audio_path}")
                except OSError: pass # Ignore if removal fails
            return "no_audio_stream"

        print(f"Error extracting audio with FFmpeg from {video_path}: {e}")
        if e.stdout: print(f"FFmpeg stdout: {e.stdout}")
        if e.stderr: print(f"FFmpeg stderr: {e.stderr}")
        return None
    except Exception as e: # Catch any other unexpected error during ffmpeg execution
        print(f"Unexpected error during ffmpeg audio extraction for {video_path}: {e}")
        return None

def combine_video_and_audio(video_path, audio_path, output_path):
    """
    Combines a video file (assumed silent or with unwanted audio)
    with an audio file into a new video file using FFmpeg.
    """
    if os.path.exists(output_path):
        print(f"Output file {output_path} already exists. Overwriting.")
        try:
            os.remove(output_path)
        except OSError as e:
            print(f"Error removing existing output file: {e}")
            return False

    # ffmpeg -i input_video_no_audio.mp4 -i input_audio.aac -c:v copy -c:a aac -strict experimental output_video_with_audio.mp4
    # -c:v copy: copy video stream without re-encoding
    # -c:a aac: re-encode audio to AAC (can be 'copy' if format is compatible)
    # We might need to adjust codecs based on input/output requirements.
    command = [
        FFMPEG_PATH,
        "-i", video_path,    # Input video (ASCII visuals, no audio)
        "-i", audio_path,    # Input audio (original)
        "-c:v", "copy",      # Copy video stream
        "-c:a", "aac",       # Encode audio to AAC (common, widely compatible)
                             # For direct copy: "-c:a", "copy" if compatible
        "-shortest",         # Finish encoding when the shortest input stream ends
        output_path
    ]
    try:
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Video and audio combined into {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error combining video and audio with FFmpeg: {e}")
        print(f"FFmpeg stdout: {e.stdout}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False

if __name__ == '__main__':
    # Example usage (requires test files)
    # test_video = "path_to_your_test_video.mp4"
    # extracted_audio_path = "extracted_audio.aac"
    # final_video_path = "final_video_with_audio.mp4"
    # dummy_ascii_video = "dummy_ascii_frames_video.mp4" # This would be output of ASCII to video frames step

    # if os.path.exists(test_video):
    #    if extract_audio(test_video, extracted_audio_path):
    #        print(f"Dummy: Now imagine '{dummy_ascii_video}' exists (video made from ASCII frames).")
    #        print(f"Dummy: We would then run: combine_video_and_audio('{dummy_ascii_video}', '{extracted_audio_path}', '{final_video_path}')")
    # else:
    #    print(f"Test video '{test_video}' not found. Skipping examples.")
    print("audio_utils.py loaded.")
