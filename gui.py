import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit,
    QProgressBar, QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox, QComboBox
    QProgressBar, QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox, QComboBox,
    QMainWindow, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, QUrl
from PyQt6.QtGui import QDesktopServices, QAction # For opening folder and menu actions
import os # For os.path.dirname
import webbrowser # Fallback for opening folder

# Import the worker
from asciivideo.process_controller import ConversionWorker


class AsciiVideoGUI(QMainWindow): # Changed from QWidget to QMainWindow
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AsciiVideo Tool")
        self.setGeometry(100, 100, 750, 650) # Adjusted initial size for more params

        # Main widget and layout
        # QMainWindow requires a central widget where layouts are set
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget) # Main layout for the central widget

        self._create_menu_bar() # Create menu bar

        # --- Input Video Selection ---
        self.input_video_label = QLabel("Input Video:")
        self.input_video_path_edit = QLineEdit()
        self.input_video_path_edit.setPlaceholderText("Select input video file...")
        self.input_video_path_edit.setReadOnly(True)
        self.browse_input_button = QPushButton("Browse...")
        # self.browse_input_button.clicked.connect(self.browse_input_video) # Connect later

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_video_label)
        input_layout.addWidget(self.input_video_path_edit)
        input_layout.addWidget(self.browse_input_button)
        self.layout.addLayout(input_layout)

        # --- Output File Selection ---
        self.output_file_label = QLabel("Output File:")
        self.output_file_path_edit = QLineEdit()
        self.output_file_path_edit.setPlaceholderText("Select output file path...")
        self.output_file_path_edit.setReadOnly(True) # Or allow typing
        self.browse_output_button = QPushButton("Browse...")
        # self.browse_output_button.clicked.connect(self.browse_output_file) # Connect later

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_file_label)
        output_layout.addWidget(self.output_file_path_edit)
        output_layout.addWidget(self.browse_output_button)
        self.layout.addLayout(output_layout)

        # --- Parameters Grid ---
        self.params_group_box = QGroupBox("Conversion Parameters")
        self.params_layout = QGridLayout() # Use QGridLayout for parameters

        # ASCII Width
        self.params_layout.addWidget(QLabel("ASCII Width (chars):"), 0, 0)
        self.ascii_width_spinbox = QSpinBox()
        self.ascii_width_spinbox.setRange(10, 1000)
        self.ascii_width_spinbox.setValue(100)
        self.ascii_width_spinbox.setToolTip("Width of the ASCII output in characters.")
        self.params_layout.addWidget(self.ascii_width_spinbox, 0, 1)

        # Character Aspect Ratio
        self.params_layout.addWidget(QLabel("Char Display AR (H/W):"), 0, 2)
        self.char_ar_dspinbox = QDoubleSpinBox()
        self.char_ar_dspinbox.setRange(0.1, 5.0)
        self.char_ar_dspinbox.setSingleStep(0.1)
        self.char_ar_dspinbox.setValue(2.0)
        self.char_ar_dspinbox.setToolTip("Display aspect ratio of a single character (Height/Width).\n"
                                       "Typical console fonts ~2.0. Square cells = 1.0.")
        self.params_layout.addWidget(self.char_ar_dspinbox, 0, 3)

        # Character Ramp
        self.params_layout.addWidget(QLabel("ASCII Ramp:"), 1, 0)
        self.char_ramp_edit = QLineEdit("@%#*+=-:. ")
        self.char_ramp_edit.setToolTip("Characters from darkest to lightest.")
        self.params_layout.addWidget(self.char_ramp_edit, 1, 1, 1, 3) # Span 3 columns

        # Target FPS
        self.params_layout.addWidget(QLabel("Target FPS:"), 2, 0)
        self.fps_dspinbox = QDoubleSpinBox()
        self.fps_dspinbox.setRange(1, 300) # Max reasonable FPS
        self.fps_dspinbox.setDecimals(1)
        self.fps_dspinbox.setValue(15.0) # Default FPS
        self.fps_dspinbox.setSpecialValueText("Original") # Allow "Original"
        self.fps_dspinbox.setToolTip("Target frames per second for processing. Select 0 for original FPS.")
        # To use "Original", we can set range from 0, and if value is 0, interpret as None/original.
        self.fps_dspinbox.setMinimum(0) # 0 will mean original
        self.params_layout.addWidget(self.fps_dspinbox, 2, 1)

        # Output Format
        self.params_layout.addWidget(QLabel("Output Format:"), 2, 2)
        self.out_format_combo = QComboBox()
        self.out_format_combo.addItems(["asvid", "mp4", "none (debug)"])
        self.out_format_combo.setToolTip("Select the output format.")
        # self.out_format_combo.currentTextChanged.connect(self.update_ui_for_format) # Connect later
        self.params_layout.addWidget(self.out_format_combo, 2, 3)

        # Audio Action
        self.params_layout.addWidget(QLabel("Audio:"), 3, 0)
        self.audio_action_combo = QComboBox()
        self.audio_action_combo.addItems(["keep", "discard"])
        self.audio_action_combo.setToolTip("Keep or discard audio track.")
        self.params_layout.addWidget(self.audio_action_combo, 3, 1)

        # --- Font settings (for MP4) ---
        self.font_path_label = QLabel("Font Path (.ttf):")
        self.params_layout.addWidget(self.font_path_label, 4, 0)
        self.font_path_edit = QLineEdit("DejaVuSansMono.ttf")
        self.font_path_edit.setToolTip("Path to .ttf font file for MP4 rendering.")
        self.browse_font_button = QPushButton("Browse...")
        # self.browse_font_button.clicked.connect(self.browse_font_file) # Connect later
        font_path_layout = QHBoxLayout()
        font_path_layout.addWidget(self.font_path_edit)
        font_path_layout.addWidget(self.browse_font_button)
        self.params_layout.addLayout(font_path_layout, 4, 1, 1, 3) # Span 3 columns

        self.font_size_label = QLabel("Font Size (px):")
        self.params_layout.addWidget(self.font_size_label, 5, 0)
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(6, 72)
        self.font_size_spinbox.setValue(10)
        self.font_size_spinbox.setToolTip("Font size in pixels for MP4 rendering.")
        self.params_layout.addWidget(self.font_size_spinbox, 5, 1)

        self.params_group_box.setLayout(self.params_layout)
        self.layout.addWidget(self.params_group_box)

        # Initially update UI based on default format
        # self.update_ui_for_format(self.out_format_combo.currentText()) # Call later

        # --- Start Conversion Button ---
        self.start_button = QPushButton("Start Conversion")
        # self.start_button.clicked.connect(self.start_conversion) # Connect later
        self.layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Status/Log Area ---
        self.status_label = QLabel("Status:")
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setFixedHeight(150) # Increased height for logs
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.status_text_edit)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.progress_bar)

        # --- Open Output Folder Button ---
        self.open_output_folder_button = QPushButton("Open Output Folder")
        self.open_output_folder_button.setEnabled(False) # Enabled on successful conversion
        self.layout.addWidget(self.open_output_folder_button, alignment=Qt.AlignmentFlag.AlignCenter)


        self.setLayout(self.layout)

        self.worker_thread = None
        self.conversion_worker = None

        # Connect signals to slots
        self.browse_input_button.clicked.connect(self.browse_input_video)
        self.browse_output_button.clicked.connect(self.browse_output_file)
        self.browse_font_button.clicked.connect(self.browse_font_file)
        self.out_format_combo.currentTextChanged.connect(self.update_ui_for_format)
        self.start_button.clicked.connect(self.start_conversion)
        self.open_output_folder_button.clicked.connect(self.open_output_directory)

        # Initialize UI state for font options
        self.update_ui_for_format(self.out_format_combo.currentText())

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        open_input_action = QAction("&Open Input Video...", self)
        open_input_action.triggered.connect(self.browse_input_video)
        file_menu.addAction(open_input_action)

        set_output_action = QAction("&Set Output File...", self)
        set_output_action.triggered.connect(self.browse_output_file)
        file_menu.addAction(set_output_action)

        file_menu.addSeparator()

        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close) # QMainWindow has close()
        file_menu.addAction(exit_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About AsciiVideo Tool", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About AsciiVideo Tool",
            "<b>AsciiVideo Tool v0.1 (GUI)</b><br><br>"
            "Converts video files to ASCII art representations.<br>"
            "Supports output to .asvid format or standard MP4 video.<br><br>"
            "Developed by Jules (AI Software Engineer)."
        )

    # --- Slot methods ---
    def browse_input_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input Video",
            "", # Start directory (empty means current or last used)
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv);;All Files (*)"
        )
        if file_path:
            self.input_video_path_edit.setText(file_path)
            self.status_text_edit.append(f"Input video selected: {file_path}")

    def browse_output_file(self):
        # For now, let's assume a generic save dialog.
        # We can refine this later based on selected output format (e.g. .asvid, .mp4)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "", # Start directory
            "ASVID Files (*.asvid);;MP4 Video Files (*.mp4);;All Files (*)"
            # TODO: Dynamically change filter based on selected output format from GUI
        )
        if file_path:
            self.output_file_path_edit.setText(file_path)
            self.status_text_edit.append(f"Output file set to: {file_path}")

    def browse_font_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Font File",
            "",
            "Font Files (*.ttf *.otf);;All Files (*)"
        )
        if file_path:
            self.font_path_edit.setText(file_path)
            self.status_text_edit.append(f"Font file selected: {file_path}")

    def update_ui_for_format(self, selected_format_text):
        is_mp4 = "mp4" in selected_format_text # Handles "mp4"
        self.font_path_label.setVisible(is_mp4)
        self.font_path_edit.setVisible(is_mp4)
        self.browse_font_button.setVisible(is_mp4)
        self.font_size_label.setVisible(is_mp4)
        self.font_size_spinbox.setVisible(is_mp4)

    # --- GUI Slots for Worker Signals ---
    def update_status_message(self, message):
        self.status_text_edit.append(message)

    def update_progress_bar_value(self, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"{percentage}%")


    def handle_conversion_finished(self, success, message_or_path):
        self.progress_bar.setValue(100 if success else 0)
        if success:
            self.output_file_path_cache = message_or_path # Cache for "Open Folder"
            # Make the path clickable (basic HTML for QTextEdit)
            # To make it truly clickable and open, QTextEdit needs setOpenExternalLinks(True)
            # or we need to handle anchorClicked signal. For simplicity, just show it.
            # A better way is a dedicated button.
            self.status_text_edit.append(f"<b>Conversion successful!</b>")
            self.status_text_edit.append(f"Output: <a href=\"file:///{message_or_path}\">{message_or_path}</a>")
            self.status_text_edit.append("<i>Note: Link might not be clickable depending on OS/setup. Use 'Open Folder'.</i>")
            self.open_output_folder_button.setEnabled(True)

        else:
            self.status_text_edit.append(f"<b>Conversion failed:</b> {message_or_path}")
            self.open_output_folder_button.setEnabled(False)

        self.start_button.setText("Start Conversion")
        self.start_button.setEnabled(True)

        # Clean up thread and worker
        if self.worker_thread:
            self.worker_thread.quit() # Ask thread to quit
            self.worker_thread.wait() # Wait for it to finish
            self.worker_thread = None
        self.conversion_worker = None # Worker is managed by thread or deleted when thread finishes normally

    def open_output_directory(self):
        if hasattr(self, 'output_file_path_cache') and self.output_file_path_cache:
            output_dir = os.path.dirname(self.output_file_path_cache)
            if os.path.exists(output_dir):
                # Use QDesktopServices to open the folder in a platform-independent way
                from PyQt6.QtGui import QDesktopServices
                import webbrowser # Fallback

                url = QUrl.fromLocalFile(output_dir)
                if not QDesktopServices.openUrl(url):
                    self.status_text_edit.append(f"Could not open folder via QDesktopServices. Trying webbrowser...")
                    try: # Fallback for systems where QDesktopServices might not work as expected for local dirs
                        webbrowser.open(output_dir)
                    except Exception as e:
                        self.status_text_edit.append(f"Failed to open output folder {output_dir}: {e}")
            else:
                self.status_text_edit.append(f"Output directory {output_dir} does not exist.")
        else:
            self.status_text_edit.append("No output file path cached to open directory.")


    def start_conversion(self):
        if self.worker_thread and self.worker_thread.isRunning():
            # If already running, try to cancel
            if self.conversion_worker:
                self.conversion_worker.cancel()
            self.status_text_edit.append("Attempting to cancel current conversion...")
            # Button text/state will be handled by conversion_finished or a new "cancelled" signal
            return

        # --- Input Validation ---
        self.status_text_edit.clear() # Clear previous logs for new validation messages
        error_messages = []

        input_video = self.input_video_path_edit.text()
        if not input_video:
            error_messages.append("Input video path is required.")
        elif not os.path.exists(input_video): # Check if input video exists
            error_messages.append(f"Input video file not found: {input_video}")

        output_file = self.output_file_path_edit.text()
        selected_out_format = self.out_format_combo.currentText().split(" ")[0]
        if selected_out_format != "none" and not output_file:
            error_messages.append(f"Output file path is required for '{selected_out_format}' format.")
        elif output_file:
            # Check if output directory is writable (basic check)
            output_dir_check = os.path.dirname(output_file)
            if not output_dir_check: # If output_file is just a filename, dir is current dir
                output_dir_check = "."
            if not os.access(output_dir_check, os.W_OK):
                error_messages.append(f"Output directory is not writable: {output_dir_check}")


        if not self.char_ramp_edit.text().strip():
            error_messages.append("ASCII character ramp cannot be empty.")

        if self.ascii_width_spinbox.value() < 10: # Example range check, though spinbox handles it
             error_messages.append("ASCII width seems too small.")

        if selected_out_format == "mp4":
            font_path_val = self.font_path_edit.text()
            if not font_path_val:
                error_messages.append("Font path is required for MP4 output.")
            # elif not os.path.exists(font_path_val): # This check might be too strict if font is in system paths
            #     error_messages.append(f"Font file not found: {font_path_val}")
            if self.font_size_spinbox.value() < 6:
                error_messages.append("Font size seems too small for MP4 output.")

        if error_messages:
            self.status_text_edit.setText("<b>Input Errors:</b>\n" + "\n".join(f"- {msg}" for msg in error_messages))
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Validation Failed")
            return
        # --- End Input Validation ---

        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.status_text_edit.append("Starting conversion...")

        params = {
            "input_video": input_video,
            "output_file": output_file,
            "width": self.ascii_width_spinbox.value(),
            "char_aspect_ratio": self.char_ar_dspinbox.value(),
            "ramp": self.char_ramp_edit.text(),
            "fps": self.fps_dspinbox.value() if self.fps_dspinbox.value() > 0 else None,
            "out_format": self.out_format_combo.currentText().split(" ")[0],
            "audio": self.audio_action_combo.currentText(),
            "font_path": self.font_path_edit.text() if self.font_path_edit.isVisible() else "DejaVuSansMono.ttf", # Default if hidden
            "font_size": self.font_size_spinbox.value() if self.font_size_spinbox.isVisible() else 10, # Default if hidden
        }
        self.status_text_edit.append(f"Parameters: {params}")

        # Create thread and worker
        self.worker_thread = QThread()
        self.conversion_worker = ConversionWorker(params)
        self.conversion_worker.moveToThread(self.worker_thread)

        # Connect signals from worker to GUI slots
        self.conversion_worker.progress_updated.connect(self.update_status_message)
        self.conversion_worker.percentage_updated.connect(self.update_progress_bar_value)
        self.conversion_worker.conversion_finished.connect(self.handle_conversion_finished)

        # Connect thread signals
        self.worker_thread.started.connect(self.conversion_worker.run_conversion)
        # Clean up after thread finishes (important!)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.conversion_worker.conversion_finished.connect(self.worker_thread.quit) # Ensure thread quits after worker is done
        # self.conversion_worker.finished.connect(self.conversion_worker.deleteLater) # If worker also emits finished

        self.worker_thread.start()

        self.start_button.setText("Cancel Conversion")
        # self.start_button.setEnabled(False) # Or change to "Cancel"
        self.status_text_edit.append("Conversion process started in background...")

def main_gui():
    app = QApplication(sys.argv)
    window = AsciiVideoGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # This allows running the GUI directly for testing,
    # but eventually it might be launched via a command or integrated differently.
    main_gui()
