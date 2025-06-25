# video_utils.py
# Utilities for video processing using FFmpeg.

import subprocess
import json

import sys # For sys.executable and sys._MEIPASS (PyInstaller)

# FFmpeg path resolution logic
def get_ffmpeg_exe_path(exe_name="ffmpeg"):
    """
    Determines the path to an FFmpeg executable (ffmpeg or ffprobe).
    1. Checks if running in a PyInstaller bundle and looks for it in `_MEIPASS`.
    2. Checks for it in the same directory as the executable/script.
    3. Checks for it in a 'ffmpeg_binaries' subdirectory relative to the executable/script.
    4. Falls back to the original hardcoded path (for development).
    5. Falls back to checking system PATH (less reliable for packaging).
    """
    # Path for PyInstaller bundle (when running as a frozen executable)
    if hasattr(sys, '_MEIPASS'):
        bundled_path = os.path.join(sys._MEIPASS, exe_name)
        if os.path.exists(bundled_path):
            return bundled_path
        # Also check for it if PyInstaller copied it to a subdirectory within _MEIPASS
        bundled_path_subdir = os.path.join(sys._MEIPASS, "ffmpeg_binaries", exe_name)
        if os.path.exists(bundled_path_subdir):
            return bundled_path_subdir


    # Path relative to the current script or executable
    # sys.executable is the python interpreter when running script, or the .exe when packaged
    # os.path.dirname(os.path.abspath(__file__)) is good for script location
    # For packaged app, it's better to use dirname of sys.executable

    base_path = ""
    if getattr(sys, 'frozen', False): # Check if running as a PyInstaller bundle
        base_path = os.path.dirname(sys.executable)
    else: # Running as a script
        base_path = os.path.dirname(os.path.abspath(__file__))


    # 1. Check in the same directory as the executable/script
    exe_path_same_dir = os.path.join(base_path, exe_name)
    if os.path.exists(exe_path_same_dir):
        return exe_path_same_dir
    exe_path_same_dir_ext = os.path.join(base_path, f"{exe_name}.exe") # For Windows
    if os.path.exists(exe_path_same_dir_ext):
        return exe_path_same_dir_ext

    # 2. Check in a 'ffmpeg_binaries' subdirectory (common packaging pattern)
    exe_path_subdir = os.path.join(base_path, "ffmpeg_binaries", exe_name)
    if os.path.exists(exe_path_subdir):
        return exe_path_subdir
    exe_path_subdir_ext = os.path.join(base_path, "ffmpeg_binaries", f"{exe_name}.exe")
    if os.path.exists(exe_path_subdir_ext):
        return exe_path_subdir_ext

    # 3. Fallback to original hardcoded paths (useful during development)
    # These are specific to your dev machine, so less useful for general packaging.
    # We should prioritize bundled versions.
    if exe_name == "ffmpeg":
        dev_path = r"C:\Users\artur\Desktop\Asciiv2\ffmpeg\ffmpeg.exe"
        if os.path.exists(dev_path): return dev_path
    elif exe_name == "ffprobe":
        dev_path = r"C:\Users\artur\Desktop\Asciiv2\ffmpeg\ffprobe.exe"
        if os.path.exists(dev_path): return dev_path

    # 4. Fallback to checking system PATH (using shutil.which)
    import shutil
    found_in_path = shutil.which(exe_name)
    if found_in_path:
        return found_in_path

    print(f"Warning: {exe_name} not found through bundled paths, dev paths, or system PATH. Extraction/Probing might fail.")
    return exe_name # Return the name itself, hoping it's in PATH and OS can find it.

FFMPEG_PATH = get_ffmpeg_exe_path("ffmpeg")
FFPROBE_PATH = get_ffmpeg_exe_path("ffprobe")


def get_video_info(video_path):
    """
    Uses ffprobe to get video information (width, height, fps, duration, etc.).
    """
    command = [
        FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)

        video_stream = next((stream for stream in info.get("streams", []) if stream.get("codec_type") == "video"), None)
        if not video_stream:
            raise RuntimeError("No video stream found in the file.")

        return {
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps_str": video_stream.get("r_frame_rate", "0/1"),
            "duration": float(info.get("format", {}).get("duration", 0)),
            "codec_name": video_stream.get("codec_name"),
            # Add more fields as needed
        }
    except subprocess.CalledProcessError as e:
        print(f"Error running ffprobe: {e}")
        print(f"Output: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("Error decoding ffprobe JSON output.")
        return None

def extract_frames(video_path, output_folder, frame_rate=None):
    """
    Extracts frames from a video using FFmpeg.
    Saves frames as image files (e.g., PNG) in the output_folder.
    Returns True on success, False otherwise.
    """
    # Example: ffmpeg -i input.mp4 -vf fps=1 output_folder/frame_%04d.png
    command = [
        FFMPEG_PATH,
        "-i", video_path,
    ]
    if frame_rate:
        command.extend(["-vf", f"fps={frame_rate}"])

    command.append(f"{output_folder}/frame_%04d.png") # Standard naming convention

    try:
        subprocess.run(command, check=True, capture_output=True)
        print(f"Frames extracted to {output_folder}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting frames with FFmpeg: {e}")
        print(f"FFmpeg stderr: {e.stderr.decode()}")
        return False

def process_video_frames(video_path, frame_processor_callback, target_fps=None):
    """
    Reads a video file frame by frame using OpenCV, processes each frame
    using the provided callback, and collects the results.

    Args:
        video_path (str): Path to the input video file.
        frame_processor_callback (function): A function that takes a single
                                             Pillow Image object (frame) and returns
                                             the processed result (e.g., ASCII string).
        target_fps (float, optional): If specified, frames will be sampled to match this FPS.
                                      Otherwise, processes all frames at original video FPS.

    Returns:
        list: A list of results from processing each selected frame.
        float: The actual FPS of the processed frames.
               (This will be target_fps if specified and achievable, otherwise original video FPS).
    """
    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return [], 0.0

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps <= 0: # Handle cases where FPS might not be available or is invalid
        print(f"Warning: Could not determine original FPS for {video_path}. Using 25.0 as a fallback.")
        original_fps = 25.0 # Fallback FPS

    processed_frames_data = []
    frame_count = 0
    processed_frame_count = 0

    # Frame skipping logic for target_fps
    if target_fps and target_fps > 0 and target_fps < original_fps:
        frame_skip_interval = original_fps / target_fps
        output_fps = target_fps
    else:
        frame_skip_interval = 1.0 # Process every frame
        output_fps = original_fps

    next_frame_to_process = 0.0

    while True:
        if frame_count >= next_frame_to_process:
            ret, frame_bgr = cap.read()
            if not ret:
                break # End of video or error

            # Convert BGR (OpenCV default) to RGB then to Pillow Image
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            processed_data = frame_processor_callback(pil_image)
            processed_frames_data.append(processed_data)
            processed_frame_count +=1

            next_frame_to_process += frame_skip_interval
        else:
            # Skip frame by simply reading it if not VideoCapture.set(cv2.CAP_PROP_POS_FRAMES) is efficient enough
            # For high skip intervals, seeking might be better if supported and reliable.
            # cap.grab() is faster than read() if you don't need the frame data.
            ret = cap.grab()
            if not ret:
                break

        frame_count += 1
        # Optional: Add a progress indicator here for long videos

    cap.release()

    # If target_fps was higher than original, output_fps will be original_fps
    # If no frames were processed, output_fps might be misleading, but it's the target/original.
    actual_output_fps = output_fps if processed_frame_count > 0 else original_fps

    print(f"Processed {processed_frame_count} frames from {video_path} at ~{actual_output_fps:.2f} FPS.")
    return processed_frames_data, actual_output_fps


if __name__ == '__main__':
    # Example usage (replace with a real video path for testing)
    # Ensure the 'output_frames' directory exists or FFmpeg might fail.
    # import os
    # if not os.path.exists("output_frames"):
    #     os.makedirs("output_frames")
    #
    # test_video = "path_to_your_test_video.mp4"
    # if os.path.exists(test_video):
    #    info = get_video_info(test_video)
    #    if info:
    #        print("Video Info:", info)
    #        # extract_frames(test_video, "output_frames", frame_rate=1) # Extract 1 frame per second
    #
    #    # Example for process_video_frames (requires a dummy processor)
    #    def dummy_frame_processor(pil_image):
    #        return f"Processed frame of size {pil_image.size}"
    #
    #    if os.path.exists(test_video):
    #        results, fps = process_video_frames(test_video, dummy_frame_processor, target_fps=5)
    #        print(f"Got {len(results)} results at {fps} FPS.")
    #        if results:
    #            print("First result:", results[0])
    # else:
    #    print(f"Test video '{test_video}' not found. Skipping examples.")
    print("video_utils.py loaded. FFmpeg/FFprobe paths are set.")
    print(f"FFMPEG: {FFMPEG_PATH}")
    print(f"FFPROBE: {FFPROBE_PATH}")
    # A simple check to see if ffprobe can be called (doesn't check if it's the *correct* ffprobe)
    try:
        subprocess.run([FFPROBE_PATH, "-version"], capture_output=True, text=True, check=True)
        print("FFprobe found and accessible.")
    except Exception as e:
        print(f"Error accessing FFprobe at {FFPROBE_PATH}: {e}")
