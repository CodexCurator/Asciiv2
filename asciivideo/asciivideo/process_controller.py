from PyQt6.QtCore import QObject, pyqtSignal
import os # For os.path.dirname

# Import necessary functions from other project modules
from .converter import AsciiConverter
from .video_utils import process_video_frames, get_video_info
from .audio_utils import extract_audio # combine_video_and_audio is in formats.py's scope
from .formats import ASVIDExporter # ASVIDExporter handles both .asvid and .mp4 (video from frames)

class ConversionWorker(QObject):
    # Signals to communicate with the GUI thread
    progress_updated = pyqtSignal(str)  # For text updates
    percentage_updated = pyqtSignal(int) # For progress bar (0-100)
    conversion_finished = pyqtSignal(bool, str) # Success (bool), message/output_path (str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        # More sophisticated cancellation might involve signaling internal loops to break
        self.progress_updated.emit("Cancellation requested...")


    def run_conversion(self):
        try:
            p = self.params # Shorthand for params
            self.progress_updated.emit(f"Starting conversion for: {p['input_video']}")
            self.percentage_updated.emit(5)

            if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled before start."); return

            # 1. Get Video Info (already done in CLI main, but good to confirm here or pass info)
            self.progress_updated.emit("Getting video information...")
            video_info = get_video_info(p['input_video'])
            if not video_info:
                self.conversion_finished.emit(False, f"Could not get video info for {p['input_video']}.")
                return
            self.progress_updated.emit(f"Original video: {video_info['width']}x{video_info['height']}, FPS: {video_info['fps_str']}")
            self.percentage_updated.emit(10)

            if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled."); return

            # 2. Audio Extraction (if needed)
            extracted_audio_path_worker = None
            if p['audio'] == 'keep':
                self.progress_updated.emit("Attempting to extract audio...")
                # Determine output directory for audio: alongside the main output file if specified, else with input.
                audio_out_dir = None
                if p['output_file']:
                    audio_out_dir = os.path.dirname(p['output_file'])
                    if not audio_out_dir: # If output_file is just a filename, save audio next to it (current dir)
                        audio_out_dir = "."

                extracted_audio_path_worker = extract_audio(p['input_video'], output_dir=audio_out_dir)

                if extracted_audio_path_worker == "no_audio_stream":
                    self.progress_updated.emit("Video has no audio stream.")
                    extracted_audio_path_worker = None
                elif extracted_audio_path_worker:
                    self.progress_updated.emit(f"Audio extracted to: {extracted_audio_path_worker}")
                else:
                    self.progress_updated.emit("Audio extraction failed or was skipped by backend.")
            else:
                self.progress_updated.emit("Audio processing set to 'discard'.")
            self.percentage_updated.emit(20)

            if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled."); return

            # 3. Initialize AsciiConverter
            self.progress_updated.emit("Initializing ASCII converter...")
            converter = AsciiConverter(
                ramp=p['ramp'],
                target_width_chars=p['width'],
                char_display_aspect_ratio=p['char_aspect_ratio']
            )
            self.percentage_updated.emit(25)

            if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled."); return

            # 4. Process Video Frames to ASCII
            # TODO: process_video_frames needs to be adapted to emit progress signals for GUI
            # For now, it's a blocking call. We can wrap it or modify it.
            # Let's assume for now it runs and we update progress after.
            self.progress_updated.emit("Converting video frames to ASCII (this may take a while)...")

            # --- Modification needed for process_video_frames for progress ---
            # A simple way is to pass a callback to process_video_frames that it can call periodically
            # def frame_processing_progress_callback(processed_count, total_frames_estimate):
            #    if self._is_cancelled: raise OperationCancelledException() # Custom exception
            #    percentage = int((processed_count / total_frames_estimate) * 100) # Rough estimate
            #    self.percentage_updated.emit(25 + int(percentage * 0.5)) # ASCII conversion 25% to 75%
            #    self.progress_updated.emit(f"Processed frame {processed_count} / ~{total_frames_estimate}")
            # For now, we don't have this callback in process_video_frames.

            ascii_frames, processed_fps = process_video_frames(
                p['input_video'],
                converter.image_to_ascii,
                target_fps=p['fps']
            )

            if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled during ASCII conversion."); return

            if not ascii_frames:
                self.conversion_finished.emit(False, "No frames were processed into ASCII.")
                return
            self.progress_updated.emit(f"Successfully converted {len(ascii_frames)} frames to ASCII at ~{processed_fps:.2f} FPS.")
            self.percentage_updated.emit(75)


            # 5. Export ASCII frames (to .asvid or .mp4)
            exporter = ASVIDExporter(
                target_width_chars=p['width'],
                processed_fps=processed_fps,
                char_display_aspect_ratio=p['char_aspect_ratio'],
                font_path=p['font_path'],
                font_size=p['font_size']
            )

            output_file_path = p['output_file']
            if not output_file_path:
                 self.conversion_finished.emit(False, "Output file path not specified.")
                 return

            if p['out_format'] == 'asvid':
                self.progress_updated.emit(f"Exporting to .asvid: {output_file_path}")
                success = exporter.export_to_asvid(
                    ascii_frames,
                    output_file_path,
                    original_extracted_audio_path=extracted_audio_path_worker
                )
                if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled during .asvid export."); return
                if success:
                    self.progress_updated.emit(f".asvid file saved: {output_file_path}")
                    self.conversion_finished.emit(True, output_file_path)
                else:
                    self.conversion_finished.emit(False, f"Failed to save .asvid file to {output_file_path}")

            elif p['out_format'] == 'mp4':
                self.progress_updated.emit(f"Exporting to .mp4: {output_file_path} (this can take time)...")
                # Temp frame dir for MP4 rendering. Could make this unique.
                temp_frame_dir = "temp_gui_ascii_render_frames"

                # ASVIDExporter.export_to_video also needs to be adapted for cancellation and progress.
                # For now, it's blocking.
                success = exporter.export_to_video(
                    ascii_frames,
                    output_file_path,
                    original_audio_path=extracted_audio_path_worker,
                    temp_frame_dir=temp_frame_dir
                    # TODO: Pass a progress callback or cancellation flag into export_to_video
                )
                if self._is_cancelled: self.conversion_finished.emit(False, "Cancelled during .mp4 export."); return
                if success:
                    self.progress_updated.emit(f"MP4 file saved: {output_file_path}")
                    self.conversion_finished.emit(True, output_file_path)
                else:
                    self.conversion_finished.emit(False, f"Failed to save .mp4 file to {output_file_path}")

            elif p['out_format'] == 'none':
                self.progress_updated.emit("Output format 'none': processing complete (debug mode).")
                if ascii_frames:
                     self.progress_updated.emit("First ASCII frame (debug):\n" + ascii_frames[0][:200] + "...") # Show a snippet
                self.conversion_finished.emit(True, "Debug processing complete. No file saved.")

            else:
                self.conversion_finished.emit(False, f"Unknown output format: {p['out_format']}")

            self.percentage_updated.emit(100)

        except Exception as e:
            self.progress_updated.emit(f"An error occurred: {e}")
            import traceback
            self.progress_updated.emit(traceback.format_exc()) # Log full traceback for debugging
            self.conversion_finished.emit(False, f"Conversion failed due to an error: {e}")
            self.percentage_updated.emit(0) # Or some error indication on progress bar
```
