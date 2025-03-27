import sys
import os
import subprocess
import webbrowser
import requests
import json
from packaging import version
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QCheckBox, QFrame, QHBoxLayout, QMessageBox, 
                            QComboBox, QLineEdit)
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

MODULES_DIR = BASE_DIR / "modules"
BOT_FILE = BASE_DIR / "bot.exe"
ON_OFF_FILE = MODULES_DIR / "on_off_modules.py"
LANGUAGES_DIR = BASE_DIR / "languages"
THEMES_DIR = BASE_DIR / "themes"
SETTINGS_FILE = BASE_DIR / "settings.json"
MODULES_LIST_URL = "https://raw.githubusercontent.com/csgocs/Bot-Creator-BC/main/modules_list.json"
VERSION_URL = "https://raw.githubusercontent.com/csgocs/Bot-Creator-BC/main/version.json"
CURRENT_VERSION = "2.1"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BC-Bot_Creator")
        self.setGeometry(100, 100, 700, 500)
        self.bot_process = None
        self.modules_vars = {}
        self.settings = self.load_settings()
        self.language = self.settings.get("language", "en")
        self.theme = self.settings.get("theme", "dark")
        self.translations = self.load_language(self.language)
        self.init_ui()
        self.apply_theme(self.theme)
        self.setup_timer()
        self.setWindowIcon(QIcon(str(BASE_DIR / "icon.ico")))

    def load_settings(self):
        if not SETTINGS_FILE.exists():
            default_settings = {
                "language": "en",
                "theme": "dark",
                "bot_token": "",
                "bot_prefix": "$",
                "log_level": "INFO"
            }
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)
            return default_settings
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_settings(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def load_language(self, lang):
        lang_file = LANGUAGES_DIR / f"{lang}.json"
        if not lang_file.exists():
            return {
                "title": "Bot Hub", "bot_control": "Bot Control", "start_bot": "Start Bot", "stop_bot": "Stop Bot",
                "bot_stopped": "Bot Stopped", "bot_running": "Bot Running",
                "modules_market": "Modules Market", "refresh_market": "Refresh Market", "installed_modules": "Installed Modules",
                "save_changes": "Save Changes", "settings": "Settings", "language": "Language", "theme": "Theme",
                "check_updates": "Check for Updates", "restart_prompt": "Please restart the application to apply the new language.",
                "download": "Download", "new_version": "New version {version} available! Download now?",
                "latest_version": "You have the latest version: {version}",
                "bot_token": "Bot Token", "bot_prefix": "Bot Prefix", "log_level": "Log Level",
                "bot_settings": "Bot Settings", "bc_settings": "BC Settings"
            }
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_theme(self, theme_name):
        theme_file = THEMES_DIR / f"{theme_name}.json"
        if not theme_file.exists():
            return {
                "name": "Dark",
                "window": [53, 53, 53],
                "text": [255, 255, 255],
                "button": [53, 53, 53],
                "button_text": [255, 255, 255],
                "highlight": [42, 130, 218]
            }
        with open(theme_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def apply_theme(self, theme_name):
        theme = self.load_theme(theme_name)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(*theme["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(*theme["text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(*theme["window"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(*theme["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(*theme["button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(*theme["button_text"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(*theme["highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        QApplication.instance().setPalette(palette)

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self.create_bot_tab(), self.translations["bot_control"])
        self.tabs.addTab(self.create_market_tab(), self.translations["modules_market"])
        self.tabs.addTab(self.create_modules_tab(), self.translations["installed_modules"])
        self.tabs.addTab(self.create_settings_tab(), self.translations["settings"])

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_modules_list)
        self.timer.start(30000)

    def create_bot_tab(self):
        bot_tab = QWidget()
        layout = QVBoxLayout()
        bot_tab.setLayout(layout)
        layout.addWidget(QLabel(self.translations["bot_control"]))
        self.start_button = QPushButton(self.translations["start_bot"])
        self.start_button.clicked.connect(self.start_bot)
        layout.addWidget(self.start_button)
        self.stop_button = QPushButton(self.translations["stop_bot"])
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)
        self.status_label = QLabel(self.translations["bot_stopped"])
        self.status_label.setStyleSheet("color: red")
        layout.addWidget(self.status_label)
        layout.addStretch()
        return bot_tab

    def create_market_tab(self):
        market_tab = QWidget()
        layout = QVBoxLayout()
        market_tab.setLayout(layout)
        layout.addWidget(QLabel(self.translations["modules_market"]))
        refresh_button = QPushButton(self.translations["refresh_market"])
        refresh_button.clicked.connect(self.refresh_market)
        layout.addWidget(refresh_button)
        self.market_container = QWidget()
        self.market_layout = QVBoxLayout()
        self.market_container.setLayout(self.market_layout)
        layout.addWidget(self.market_container)
        self.refresh_market()
        layout.addStretch()
        return market_tab

    def create_modules_tab(self):
        modules_tab = QWidget()
        layout = QVBoxLayout()
        modules_tab.setLayout(layout)
        layout.addWidget(QLabel(self.translations["installed_modules"]))
        self.modules_container = QWidget()
        self.modules_layout = QVBoxLayout()
        self.modules_container.setLayout(self.modules_layout)
        layout.addWidget(self.modules_container)
        save_button = QPushButton(self.translations["save_changes"])
        save_button.clicked.connect(self.save_modules_state)
        layout.addWidget(save_button)
        self.update_modules_list()
        layout.addStretch()
        return modules_tab

    def create_settings_tab(self):
        settings_tab = QWidget()
        layout = QVBoxLayout()
        settings_tab.setLayout(layout)

        self.bot_settings_button = QPushButton(f"> {self.translations['bot_settings']}")
        self.bot_settings_button.clicked.connect(self.toggle_bot_settings)
        layout.addWidget(self.bot_settings_button)
        self.bot_settings_widget = QWidget()
        self.bot_settings_layout = QVBoxLayout()
        self.bot_settings_widget.setLayout(self.bot_settings_layout)
        self.bot_settings_widget.setVisible(False)

        self.bot_settings_layout.addWidget(QLabel(self.translations["bot_token"]))
        self.token_input = QLineEdit(self.settings.get("bot_token", ""))
        self.token_input.textChanged.connect(self.update_token)
        self.bot_settings_layout.addWidget(self.token_input)

        self.bot_settings_layout.addWidget(QLabel(self.translations["bot_prefix"]))
        self.prefix_input = QLineEdit(self.settings.get("bot_prefix", "$"))
        self.prefix_input.textChanged.connect(self.update_prefix)
        self.bot_settings_layout.addWidget(self.prefix_input)

        self.bot_settings_layout.addWidget(QLabel(self.translations["log_level"]))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["INFO", "DEBUG", "ERROR"])
        self.log_level_combo.setCurrentText(self.settings.get("log_level", "INFO"))
        self.log_level_combo.currentTextChanged.connect(self.update_log_level)
        self.bot_settings_layout.addWidget(self.log_level_combo)

        layout.addWidget(self.bot_settings_widget)

        self.bc_settings_button = QPushButton(f"> {self.translations['bc_settings']}")
        self.bc_settings_button.clicked.connect(self.toggle_bc_settings)
        layout.addWidget(self.bc_settings_button)
        self.bc_settings_widget = QWidget()
        self.bc_settings_layout = QVBoxLayout()
        self.bc_settings_widget.setLayout(self.bc_settings_layout)
        self.bc_settings_widget.setVisible(False)

        self.bc_settings_layout.addWidget(QLabel(self.translations["language"]))
        self.language_combo = QComboBox()
        self.load_languages()
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.bc_settings_layout.addWidget(self.language_combo)

        self.bc_settings_layout.addWidget(QLabel(self.translations["theme"]))
        self.theme_combo = QComboBox()
        self.load_themes()
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.bc_settings_layout.addWidget(self.theme_combo)

        self.bc_settings_layout.addWidget(QLabel(self.translations["check_updates"]))
        update_button = QPushButton(self.translations["check_updates"])
        update_button.clicked.connect(self.check_for_updates)
        self.bc_settings_layout.addWidget(update_button)

        layout.addWidget(self.bc_settings_widget)
        layout.addStretch()
        return settings_tab

    def toggle_bot_settings(self):
        is_visible = self.bot_settings_widget.isVisible()
        self.bot_settings_widget.setVisible(not is_visible)
        self.bot_settings_button.setText(f"{'v' if not is_visible else '>'} {self.translations['bot_settings']}")

    def toggle_bc_settings(self):
        is_visible = self.bc_settings_widget.isVisible()
        self.bc_settings_widget.setVisible(not is_visible)
        self.bc_settings_button.setText(f"{'v' if not is_visible else '>'} {self.translations['bc_settings']}")

    def load_languages(self):
        if not LANGUAGES_DIR.exists():
            LANGUAGES_DIR.mkdir()
        for lang_file in LANGUAGES_DIR.glob("*.json"):
            lang_name = lang_file.stem
            self.language_combo.addItem(lang_name)
        if self.language_combo.findText(self.language) != -1:
            self.language_combo.setCurrentText(self.language)

    def load_themes(self):
        if not THEMES_DIR.exists():
            THEMES_DIR.mkdir()
        for theme_file in THEMES_DIR.glob("*.json"):
            theme_name = theme_file.stem
            self.theme_combo.addItem(theme_file.stem)
        if self.theme_combo.findText(self.theme) != -1:
            self.theme_combo.setCurrentText(self.theme)

    def change_language(self, lang):
        self.settings["language"] = lang
        self.save_settings()
        QMessageBox.information(self, "Restart Required", self.translations["restart_prompt"])
        self.translations = self.load_language(lang)

    def change_theme(self, theme):
        self.settings["theme"] = theme
        self.save_settings()
        self.apply_theme(theme)

    def update_token(self, text):
        self.settings["bot_token"] = text
        self.save_settings()
        if self.bot_process:
            QMessageBox.warning(self, "Restart Required", "Please restart the bot to apply the new token.")

    def update_prefix(self, text):
        self.settings["bot_prefix"] = text
        self.save_settings()
        if self.bot_process:
            QMessageBox.warning(self, "Restart Required", "Please restart the bot to apply the new prefix.")

    def update_log_level(self, level):
        self.settings["log_level"] = level
        self.save_settings()
        if self.bot_process:
            QMessageBox.warning(self, "Restart Required", "Please restart the bot to apply the new log level.")

    def check_for_updates(self):
        try:
            response = requests.get(VERSION_URL)
            response.raise_for_status()
            data = response.json()
            latest_version = data["version"]
            download_url = data["download_url"]
            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                reply = QMessageBox.question(self, "Update Available", 
                                            self.translations["new_version"].format(version=latest_version),
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    webbrowser.open(download_url)
            else:
                QMessageBox.information(self, "Update Checker", 
                self.translations["latest_version"].format(version=CURRENT_VERSION))
        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to check updates: {e}")

    def start_bot(self):
        if not BOT_FILE.exists():
            QMessageBox.critical(self, "Error", f"Bot executable not found at {BOT_FILE}")
            return
        if self.bot_process is None:
            try:
                self.bot_process = subprocess.Popen([BOT_FILE])
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.status_label.setText(self.translations["bot_running"])
                self.status_label.setStyleSheet("color: green")
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to start bot: {e}")
        else:
            QMessageBox.warning(self, "Warning", "Bot is already running!")

    def stop_bot(self):
        if self.bot_process is not None:
            self.bot_process.terminate()
            self.bot_process = None
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText(self.translations["bot_stopped"])
            self.status_label.setStyleSheet("color: red")
        else:
            QMessageBox.warning(self, "Warning", "Bot is not running!")

    def get_available_modules(self):
        try:
            response = requests.get(MODULES_LIST_URL)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to fetch module list: {e}")
            return []

    def download_module(self, module_name, download_url):
        try:
            response = requests.get(download_url)
            response.raise_for_status()
            if not MODULES_DIR.exists():
                MODULES_DIR.mkdir()
            module_path = MODULES_DIR / f"{module_name}.py"
            with open(module_path, "wb") as f:
                f.write(response.content)
            self.update_modules_list()
            return True
        except requests.RequestException as e:
            print(f"Failed to download {module_name}: {e}")
            return False
        except OSError as e:
            print(f"Failed to write {module_name} to {module_path}: {e}")
            return False

    def refresh_market(self):
        for i in reversed(range(self.market_layout.count())):
            self.market_layout.itemAt(i).widget().setParent(None)
        modules = self.get_available_modules()
        if not modules:
            self.market_layout.addWidget(QLabel("No modules available or connection error"))
            return
        for module in modules:
            frame = QFrame()
            h_layout = QHBoxLayout()
            frame.setLayout(h_layout)
            name_button = QPushButton(f"{module['name']} - {module['description']}")
            name_button.clicked.connect(lambda _, url=module["readme_url"]: webbrowser.open(url))
            h_layout.addWidget(name_button)
            download_button = QPushButton(self.translations["download"])
            download_button.clicked.connect(lambda _, m=module["name"], url=module["download_url"]: self.download_module(m, url))
            h_layout.addWidget(download_button)
            self.market_layout.addWidget(frame)

    def load_modules_state(self):
        if not os.path.exists(ON_OFF_FILE):
            with open(ON_OFF_FILE, "w", encoding="utf-8") as f:
                f.write("enabled_modules = {}\n")
        with open(ON_OFF_FILE, "r", encoding="utf-8") as f:
            exec(f.read(), globals())
        return globals().get("enabled_modules", {})

    def save_modules_state(self):
        enabled_modules = {name: cb.isChecked() for name, cb in self.modules_vars.items()}
        with open(ON_OFF_FILE, "w", encoding="utf-8") as f:
            f.write(f"enabled_modules = {enabled_modules}\n")
        QMessageBox.information(self, "Success", "Modules state saved!")

    def update_modules_list(self):
        for i in reversed(range(self.modules_layout.count())):
            self.modules_layout.itemAt(i).widget().setParent(None)
        enabled_modules = self.load_modules_state()
        self.modules_vars.clear()
        for module_file in list(MODULES_DIR.glob("*.py")):
            module_name = module_file.stem
            if module_name == "on_off_modules":
                continue
            cb = QCheckBox(module_name)
            cb.setChecked(enabled_modules.get(module_name, False))
            self.modules_vars[module_name] = cb
            self.modules_layout.addWidget(cb)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())