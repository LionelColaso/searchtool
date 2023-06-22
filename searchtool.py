import os
import sys

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QCheckBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTextEdit,
    QProgressBar,
)


class SearchThread(QThread):
    search_result = Signal(str)
    search_progress = Signal(int)

    def __init__(self, search_text, search_options):
        super().__init__()
        self.search_text = search_text
        self.search_options = search_options
        self.stop_search = False

    def run(self):
        folder = self.search_options["folder"]
        search_type = self.search_options["search_type"]
        case_sensitive = self.search_options["case_sensitive"]
        include_git = self.search_options["include_git"]
        include_languages = self.search_options["include_languages"]
        include_source = self.search_options["include_source"]

        if not case_sensitive:
            search_text = self.search_text.lower()
        else:
            search_text = self.search_text

        git_folders = [] if include_git else [".git"]
        language_folders = [] if include_languages else ["Languages", "languages"]
        source_folders = [] if include_source else ["Source", "source"]

        # Calculate total_files here
        total_files = len([file for root, _, files in os.walk(folder) for file in files])

        count = 0
        processed_files = 0

        for root, dirs, files in os.walk(folder):
            for git_folder in git_folders:
                if git_folder in dirs:
                    dirs.remove(git_folder)

            for language_folder in language_folders:
                if language_folder in dirs:
                    dirs.remove(language_folder)

            for source_folder in source_folders:
                if source_folder in dirs:
                    dirs.remove(source_folder)

            for file in files:
                if self.stop_search:
                    return

                if search_type == "File and Folder Names" and (
                    (not case_sensitive and search_text in file.lower()) or
                    (case_sensitive and search_text in file)
                ):
                    count += 1
                    self.search_result.emit(os.path.join(root, file))

                processed_files += 1
                progress = (processed_files / total_files) * 100
                self.search_progress.emit(int(progress))

                if search_type == "File and Folder Names" and ((not case_sensitive and search_text in file.lower()) or (
                        case_sensitive and search_text in file)):
                    count += 1
                    self.search_result.emit(os.path.join(root, file))
                elif search_type == "Inside All Files":
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            file_contents = f.read()
                            if (not case_sensitive and search_text in file_contents.lower()) or (
                                    case_sensitive and search_text in file_contents):
                                count += 1
                                self.search_result.emit(file_path)
                    except FileNotFoundError:
                        pass  # Handle the case where the file doesn't exist
                elif search_type == ".xml Extensions Only" and file.endswith(".xml"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            file_contents = f.read()
                            if (not case_sensitive and search_text in file_contents.lower()) or (
                                    case_sensitive and search_text in file_contents):
                                count += 1
                                self.search_result.emit(file_path)
                    except FileNotFoundError:
                        pass  # Handle the case where the file doesn't exist

                    processed_files += 1
                    progress = (processed_files / total_files) * 100
                    self.search_progress.emit(int(progress))

        self.search_result.emit(f"Total Results: {count}")


class SearchTool(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_folder = ""
        self.search_thread = None

        self.setWindowTitle("File Search")
        self.setMinimumSize(800, 600)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # Folder Selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Selected Folder: ")
        self.folder_path_label = QLabel()
        folder_button = QPushButton("Browse")
        folder_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path_label)
        folder_layout.addWidget(folder_button)
        layout.addLayout(folder_layout)

        # Search Text Input
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Enter text to search")
        layout.addWidget(self.search_text)

        # Connect the returnPressed signal of search_text to start_search
        self.search_text.returnPressed.connect(self.start_search)

        # Search Options
        options_layout = QVBoxLayout()
        options_layout.addWidget(QLabel("Search Filter:"))

        self.case_sensitive_check = QCheckBox("Case Sensitive")
        options_layout.addWidget(self.case_sensitive_check)

        self.include_git_check = QCheckBox("Include .git Folders")
        options_layout.addWidget(self.include_git_check)

        self.include_languages_check = QCheckBox("Include Languages Folders")
        options_layout.addWidget(self.include_languages_check)

        self.include_source_check = QCheckBox("Include Source Folders")
        options_layout.addWidget(self.include_source_check)

        options_layout.addWidget(QLabel("Search Type:"))

        # Search Type Combo Box
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["File and Folder Names", "Inside All Files", ".xml Extensions Only"])
        # Set the default selection to ".xml Extensions Only"
        self.search_type_combo.setCurrentIndex(2)
        options_layout.addWidget(self.search_type_combo)

        layout.addLayout(options_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Search and Stop Buttons
        search_buttons_layout = QHBoxLayout()
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.start_search)
        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_search)
        search_buttons_layout.addWidget(search_button)
        search_buttons_layout.addWidget(stop_button)
        layout.addLayout(search_buttons_layout)

        # Search Results
        self.search_results_text = QTextEdit()
        layout.addWidget(self.search_results_text)

        # List Extensions Buttons
        extensions_layout = QHBoxLayout()
        list_extensions_buttons = [("List .xml Extensions", "xml"), ("List .dll Extensions", "dll"),
                                   ("List .png Extensions", "png"), ("List .dds Extensions", "dds"), ]
        for button_label, extension in list_extensions_buttons:
            button = QPushButton(button_label)
            button.clicked.connect(lambda clicked=False, ext=extension: self.list_extensions(ext))
            extensions_layout.addWidget(button)

        layout.addLayout(extensions_layout)

        # Save Results Button
        save_results_button = QPushButton("Save Results to .txt")
        save_results_button.clicked.connect(self.save_results)
        layout.addWidget(save_results_button)

        # Clear Button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_results)
        layout.addWidget(clear_button)

        self.setCentralWidget(main_widget)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.selected_folder = folder
            self.folder_path_label.setText(folder)

    def start_search(self, search_text=None):
        if search_text is not None:
            search_text = str(search_text)  # Ensure search_text is a string
            self.search_text.setText(search_text)  # Set the search text from the argument

        if not self.selected_folder:
            return

        self.clear_results()  # Remove extra parentheses

        # Retrieve the search text from the QLineEdit widget
        search_text = self.search_text.text()

        search_options = {"folder": self.selected_folder, "search_type": self.search_type_combo.currentText(),
                          "case_sensitive": self.case_sensitive_check.isChecked(),
                          "include_git": self.include_git_check.isChecked(),
                          "include_languages": self.include_languages_check.isChecked(),
                          "include_source": self.include_source_check.isChecked(), }

        # Create a new SearchThread instance
        self.search_thread = SearchThread(search_text, search_options)

        # Connect the signals
        self.search_thread.search_result.connect(self.display_search_result)
        self.search_thread.search_progress.connect(self.update_progress)

        # Connect the finished signal
        self.search_thread.finished.connect(self.search_finished)

        # Start the new thread
        self.search_thread.start()

    def display_search_result(self, result):
        self.search_results_text.append(result)

    def search_finished(self):
        self.search_thread = None
        self.progress_bar.setValue(0)

    def stop_search(self):
        if self.search_thread:
            self.search_thread.stop_search = True

    def save_results(self):
        if not self.search_results_text.toPlainText():
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "Text Files (*.txt)")
        if save_path:
            with open(save_path, "w") as f:
                f.write(self.search_results_text.toPlainText())

    def clear_results(self):
        self.search_results_text.clear()

    def list_extensions(self, extension):
        if not self.selected_folder:
            return

        if not isinstance(extension, str):
            return

        extensions = set()
        total_files = sum(1 for root, dirs, files in os.walk(self.selected_folder) for file in files if
                          file.endswith("." + extension))
        processed_files = 0

        # Clear the search results text before listing extensions
        self.clear_results()

        for root, dirs, files in os.walk(self.selected_folder):
            for file in files:
                if file.endswith("." + extension):
                    extensions.add(file)

                processed_files += 1
                progress = (processed_files / total_files) * 100
                self.update_progress(int(progress))

        self.search_results_text.append(f"List of .{extension} Extensions:")
        self.search_results_text.append("\n".join(extensions))

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SearchTool()
    window.show()
    sys.exit(app.exec())
