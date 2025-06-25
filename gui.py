import sys
# Single, unambiguous line for all QtWidgets imports
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit, QProgressBar, QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox, QComboBox, QMainWindow, QMessageBox
from PyQt6.QtCore import Qt, QThread, QUrl
from PyQt6.QtGui import QDesktopServices, QAction
import os
import webbrowser

from asciivideo.process_controller import ConversionWorker


class AsciiVideoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AsciiVideo Tool")
        self.setGeometry(100, 100, 750, 650)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self._create_menu_bar()

        self.input_video_label = QLabel("Input Video:")
        self.input_video_path_edit = QLineEdit()
        self.input_video_path_edit.setPlaceholderText("Select input video file...")
        self.input_video_path_edit.setReadOnly(True)
        self.browse_input_button = QPushButton("Browse...")
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_video_label)
        input_layout.addWidget(self.input_video_path_edit)
        input_layout.addWidget(self.browse_input_button)
        self.layout.addLayout(input_layout)

        self.output_file_label = QLabel("Output File:")
        self.output_file_path_edit = QLineEdit()
        self.output_file_path_edit.setPlaceholderText("Select output file path...")
        self.output_file_path_edit.setReadOnly(True)
        self.browse_output_button = QPushButton("Browse...")
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_file_label)
        output_layout.addWidget(self.output_file_path_edit)
        output_layout.addWidget(self.browse_output_button)
        self.layout.addLayout(output_layout)

        self.params_group_box = QGroupBox("Conversion Parameters")
        self.params_layout = QGridLayout()

        self.params_layout.addWidget(QLabel("ASCII Width (chars):"), 0, 0)
        self.ascii_width_spinbox = QSpinBox()
        self.ascii_width_spinbox.setRange(10, 1000)
        self.ascii_width_spinbox.setValue(100)
        self.ascii_width_spinbox.setToolTip("Width of the ASCII output in characters.")
        self.params_layout.addWidget(self.ascii_width_spinbox, 0, 1)

        self.params_layout.addWidget(QLabel("Char Display AR (H/W):"), 0, 2)
        self.char_ar_dspinbox = QDoubleSpinBox()
        self.char_ar_dspinbox.setRange(0.1, 5.0)
        self.char_ar_dspinbox.setSingleStep(0.1)
        self.char_ar_dspinbox.setValue(2.0)
        self.char_ar_dspinbox.setToolTip("Display aspect ratio of a single character (Height/Width).\n"
                                       "Typical console fonts ~2.0. Square cells = 1.0.")
        self.params_layout.addWidget(self.char_ar_dspinbox, 0, 3)

        self.params_layout.addWidget(QLabel("ASCII Ramp:"), 1, 0)
        self.char_ramp_edit = QLineEdit("@%#*+=-:. ")
        self.char_ramp_edit.setToolTip("Characters from darkest to lightest.")
        self.params_layout.addWidget(self.char_ramp_edit, 1, 1, 1, 3)

        self.params_layout.addWidget(QLabel("Target FPS:"), 2, 0)
        self.fps_dspinbox = QDoubleSpinBox()
        self.fps_dspinbox.setRange(0, 300)
        self.fps_dspinbox.setDecimals(1)
        self.fps_dspinbox.setValue(15.0)
        self.fps_dspinbox.setSpecialValueText("Original (0.0)")
        self.fps_dspinbox.setToolTip("Target frames per second for processing. Set to 0.0 for original FPS.")
        self.params_layout.addWidget(self.fps_dspinbox, 2, 1)

        self.params_layout.addWidget(QLabel("Output Format:"), 2, 2)
        self.out_format_combo = QComboBox()
        self.out_format_combo.addItems(["asvid", "mp4", "none (debug)"])
        self.out_format_combo.setToolTip("Select the output format.")
        self.params_layout.addWidget(self.out_format_combo, 2, 3)

        self.params_layout.addWidget(QLabel("Audio:"), 3, 0)
        self.audio_action_combo = QComboBox()
        self.audio_action_combo.addItems(["keep", "discard"])
        self.audio_action_combo.setToolTip("Keep or discard audio track.")
        self.params_layout.addWidget(self.audio_action_combo, 3, 1)

        self.font_path_label = QLabel("Font Path (.ttf):")
        self.params_layout.addWidget(self.font_path_label, 4, 0)
        self.font_path_edit = QLineEdit("DejaVuSansMono.ttf")
        self.font_path_edit.setToolTip("Path to .ttf font file for MP4 rendering.")
        self.browse_font_button = QPushButton("Browse...")
        font_path_layout = QHBoxLayout()
        font_path_layout.addWidget(self.font_path_edit)
        font_path_layout.addWidget(self.browse_font_button)
        self.params_layout.addLayout(font_path_layout, 4, 1, 1, 3)

        self.font_size_label = QLabel("Font Size (px):")
        self.params_layout.addWidget(self.font_size_label, 5, 0)
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(6, 72)
        self.font_size_spinbox.setValue(10)
        self.font_size_spinbox.setToolTip("Font size in pixels for MP4 rendering.")
        self.params_layout.addWidget(self.font_size_spinbox, 5, 1)

        self.params_group_box.setLayout(self.params_layout)
        self.layout.addWidget(self.params_group_box)

        self.start_button = QPushButton("Start Conversion")
        self.layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Status:")
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setFixedHeight(150)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.status_text_edit)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.progress_bar)

        self.open_output_folder_button = QPushButton("Open Output Folder")
        self.open_output_folder_button.setEnabled(False)
        self.layout.addWidget(self.open_output_folder_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.worker_thread = None
        self.conversion_worker = None

        self.browse_input_button.clicked.connect(self.browse_input_video)
        self.browse_output_button.clicked.connect(self.browse_output_file)
        self.browse_font_button.clicked.connect(self.browse_font_file)
        self.out_format_combo.currentTextChanged.connect(self.update_ui_for_format)
        self.start_button.clicked.connect(self.start_conversion)
        self.open_output_folder_button.clicked.connect(self.open_output_directory)

        self.update_ui_for_format(self.out_format_combo.currentText())

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_input_action = QAction("&Open Input Video...", self)
        open_input_action.triggered.connect(self.browse_input_video)
        file_menu.addAction(open_input_action)
        set_output_action = QAction("&Set Output File...", self)
        set_output_action.triggered.connect(self.browse_output_file)
        file_menu.addAction(set_output_action)
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
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

    def browse_input_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input Video", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv);;All Files (*)"
        )
        if file_path:
            self.input_video_path_edit.setText(file_path)
            self.status_text_edit.append(f"Input video selected: {file_path}")

    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", "",
            "ASVID Files (*.asvid);;MP4 Video Files (*.mp4);;All Files (*)"
        )
        if file_path:
            self.output_file_path_edit.setText(file_path)
            self.status_text_edit.append(f"Output file set to: {file_path}")

    def browse_font_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Font File", "", "Font Files (*.ttf *.otf);;All Files (*)"
        )
        if file_path:
            self.font_path_edit.setText(file_path)
            self.status_text_edit.append(f"Font file selected: {file_path}")

    def update_ui_for_format(self, selected_format_text):
        is_mp4 = "mp4" in selected_format_text
        self.font_path_label.setVisible(is_mp4)
        self.font_path_edit.setVisible(is_mp4)
        self.browse_font_button.setVisible(is_mp4)
        self.font_size_label.setVisible(is_mp4)
        self.font_size_spinbox.setVisible(is_mp4)

    def update_status_message(self, message):
        self.status_text_edit.append(message)

    def update_progress_bar_value(self, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"{percentage}%")

    def handle_conversion_finished(self, success, message_or_path):
        self.progress_bar.setValue(100 if success else 0)
        if success:
            self.output_file_path_cache = message_or_path
            self.status_text_edit.append(f"<b>Conversion successful!</b>")
            self.status_text_edit.append(f"Output: <a href=\"file:///{message_or_path}\">{message_or_path}</a>")
            self.status_text_edit.append("<i>Note: Link might not be clickable depending on OS/setup. Use 'Open Folder'.</i>")
            self.open_output_folder_button.setEnabled(True)
        else:
            self.status_text_edit.append(f"<b>Conversion failed:</b> {message_or_path}")
            self.open_output_folder_button.setEnabled(False)

        self.start_button.setText("Start Conversion")
        self.start_button.setEnabled(True)

        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
        self.conversion_worker = None

    def open_output_directory(self):
        if hasattr(self, 'output_file_path_cache') and self.output_file_path_cache:
            output_dir = os.path.dirname(self.output_file_path_cache)
            if os.path.exists(output_dir):
                url = QUrl.fromLocalFile(output_dir)
                if not QDesktopServices.openUrl(url):
                    self.status_text_edit.append(f"Could not open folder via QDesktopServices. Trying webbrowser...")
                    try:
                        webbrowser.open(output_dir)
                    except Exception as e:
                        self.status_text_edit.append(f"Failed to open output folder {output_dir}: {e}")
            else:
                self.status_text_edit.append(f"Output directory {output_dir} does not exist.")
        else:
            self.status_text_edit.append("No output file path cached to open directory.")

    def start_conversion(self):
        if self.worker_thread and self.worker_thread.isRunning():
            if self.conversion_worker:
                self.conversion_worker.cancel()
            self.status_text_edit.append("Attempting to cancel current conversion...")
            return

        self.status_text_edit.clear()
        error_messages = []

        input_video = self.input_video_path_edit.text()
        if not input_video:
            error_messages.append("Input video path is required.")
        elif not os.path.exists(input_video):
            error_messages.append(f"Input video file not found: {input_video}")

        output_file = self.output_file_path_edit.text()
        selected_out_format = self.out_format_combo.currentText().split(" ")[0]
        if selected_out_format != "none" and not output_file:
            error_messages.append(f"Output file path is required for '{selected_out_format}' format.")
        elif output_file:
            output_dir_check = os.path.dirname(output_file)
            if not output_dir_check:
                output_dir_check = "."
            if not os.access(output_dir_check, os.W_OK):
                error_messages.append(f"Output directory is not writable: {output_dir_check}")

        if not self.char_ramp_edit.text().strip():
            error_messages.append("ASCII character ramp cannot be empty.")

        if self.ascii_width_spinbox.value() < 10:
             error_messages.append("ASCII width seems too small.")

        if selected_out_format == "mp4":
            font_path_val = self.font_path_edit.text()
            if not font_path_val:
                error_messages.append("Font path is required for MP4 output.")
            if self.font_size_spinbox.value() < 6:
                error_messages.append("Font size seems too small for MP4 output.")

        if error_messages:
            self.status_text_edit.setText("<b>Input Errors:</b>\n" + "\n".join(f"- {msg}" for msg in error_messages))
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Validation Failed")
            return

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
            "font_path": self.font_path_edit.text() if self.font_path_edit.isVisible() else "DejaVuSansMono.ttf",
            "font_size": self.font_size_spinbox.value() if self.font_size_spinbox.isVisible() else 10,
        }
        self.status_text_edit.append(f"Parameters: {params}")

        self.worker_thread = QThread()
        self.conversion_worker = ConversionWorker(params)
        self.conversion_worker.moveToThread(self.worker_thread)

        self.conversion_worker.progress_updated.connect(self.update_status_message)
        self.conversion_worker.percentage_updated.connect(self.update_progress_bar_value)
        self.conversion_worker.conversion_finished.connect(self.handle_conversion_finished)

        self.worker_thread.started.connect(self.conversion_worker.run_conversion)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.conversion_worker.conversion_finished.connect(self.worker_thread.quit)

        self.worker_thread.start()

        self.start_button.setText("Cancel Conversion")
        self.status_text_edit.append("Conversion process started in background...")

def main_gui():
    app = QApplication(sys.argv)
    window = AsciiVideoGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main_gui()
