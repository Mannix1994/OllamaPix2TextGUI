import sys
import pyperclip
import io
import base64
import requests
import subprocess
import os
import json
import locale
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit,
                             QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPainter, QColor, QPen, QKeyEvent, QIcon
from PIL import ImageGrab
from pynput import keyboard

# --- 配置管理逻辑 ---
CONFIG_DIR = os.path.expanduser("~/.glm-ocr")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def get_wsl_ip():
    try:
        system_encoding = locale.getpreferredencoding()
        result = subprocess.run(['wsl', 'hostname', '-I'], capture_output=True, text=True,
                                timeout=5, encoding=system_encoding, errors='replace')
        if result.returncode == 0:
            return result.stdout.split()[0]
    except Exception:
        pass
    return "127.0.0.1"


def load_config():
    default_config = {
        "api_url": f"http://{get_wsl_ip()}:11434/api/generate",
        "model": "glm-ocr",
        "prompt": "Identify all text and tables in the image and output them "
                  "in standard Markdown format. Formulas should be in LaTeX format."
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            print(f"加载配置失败: {e}")
    return default_config


def save_to_disk(api_url, model, prompt):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    config_data = {"api_url": api_url, "model": model, "prompt": prompt}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)


# --- OCR 线程 ---
class OCRWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pil_img, api_url, model_name, prompt_text):
        super().__init__()
        self.pil_img = pil_img
        self.api_url = api_url
        self.model_name = model_name
        self.prompt_text = prompt_text

    def run(self):
        try:
            buffered = io.BytesIO()
            self.pil_img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            payload = {
                "model": self.model_name,
                "prompt": self.prompt_text,
                "stream": False,
                "images": [img_base64]
            }

            response = requests.post(self.api_url, json=payload, timeout=360)
            response.raise_for_status()
            raw_result = response.json().get('response', '')
            self.finished.emit(raw_result)
        except Exception as e:
            self.error.emit(str(e))


class HotkeySignal(QObject):
    signal = pyqtSignal()


class ScreenShotTool(QWidget):
    def __init__(self, callback, on_cancel):
        super().__init__()
        self.callback = callback
        self.on_cancel = on_cancel
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        total_rect = QRect()
        for screen in QApplication.screens():
            total_rect = total_rect.united(screen.geometry())
        self.setGeometry(total_rect)
        self.setWindowOpacity(0.3)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.start_pos = None
        self.end_pos = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.on_cancel()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        self.end_pos = event.globalPosition().toPoint()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.start_pos and self.end_pos:
            self.hide()
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            try:
                screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
                self.callback(screenshot)
            except:
                self.on_cancel()
        else:
            self.on_cancel()
        self.close()

    def paintEvent(self, event):
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawRect(self.mapFromGlobal(rect.topLeft()).x(),
                             self.mapFromGlobal(rect.topLeft()).y(),
                             rect.width(), rect.height())


def get_resource_path(relative_path):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama-OCR助手")
        icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(850, 650)
        self.config = load_config()
        self.last_screenshot = None
        self.is_running = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)

        # 1. 配置行
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("API URL:"))
        self.url_input = QLineEdit(self.config["api_url"])
        config_layout.addWidget(self.url_input)

        config_layout.addWidget(QLabel("模型:"))
        self.model_input = QLineEdit(self.config["model"])
        self.model_input.setFixedWidth(100)
        config_layout.addWidget(self.model_input)

        self.save_btn = QPushButton("💾 保存设置")
        self.save_btn.clicked.connect(self.manual_save_config)
        config_layout.addWidget(self.save_btn)
        main_layout.addLayout(config_layout)

        # 2. Prompt
        main_layout.addWidget(QLabel("自定义 Prompt:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setFixedHeight(70)
        self.prompt_input.setText(self.config["prompt"])
        main_layout.addWidget(self.prompt_input)

        # 3. 动作按钮行
        btn_layout = QHBoxLayout()
        self.capture_btn = QPushButton("📷 截图识别 (Alt + A)/按ESC退出截图")
        self.capture_btn.setFixedHeight(45)
        self.capture_btn.setStyleSheet("font-weight: bold; background-color: #e8f5e9;")
        self.capture_btn.clicked.connect(self.start_capture)

        self.reparse_btn = QPushButton("🔄 重新解析")
        self.reparse_btn.setFixedHeight(45)
        self.reparse_btn.setStyleSheet("font-weight: bold; background-color: #e3f2fd;")
        self.reparse_btn.clicked.connect(self.reparse_last_image)

        btn_layout.addWidget(self.capture_btn, stretch=2)
        btn_layout.addWidget(self.reparse_btn, stretch=1)
        main_layout.addLayout(btn_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # 4. 结果
        main_layout.addWidget(QLabel("识别结果:"))
        self.result_area = QTextEdit()
        main_layout.addWidget(self.result_area, stretch=1)

        self.status_label = QLabel("状态: 就绪")
        main_layout.addWidget(self.status_label)

        # --- 热键监听 (pynput 方案) ---
        self.hotkey_helper = HotkeySignal()
        self.hotkey_helper.signal.connect(self.start_capture)

        # 启动后台非阻塞监听
        self.listener = keyboard.GlobalHotKeys({
            '<alt>+a': self.hotkey_helper.signal.emit
        })
        self.listener.start()

    def set_ui_loading(self, loading: bool):
        self.is_running = loading
        self.capture_btn.setEnabled(not loading)
        self.reparse_btn.setEnabled(not loading)
        self.save_btn.setEnabled(not loading)

        if loading:
            self.capture_btn.setText("⏳ 正在请求中...")
            self.reparse_btn.setText("请稍候...")
        else:
            self.capture_btn.setText("📷 截图识别 (Alt + A)")
            self.reparse_btn.setText("🔄 重新解析")

    def manual_save_config(self):
        save_to_disk(self.url_input.text().strip(), self.model_input.text().strip(),
                     self.prompt_input.toPlainText().strip())
        QMessageBox.information(self, "保存成功", f"设置已保存。{CONFIG_FILE}")

    def start_capture(self):
        if self.is_running: return

        self.hide()
        QApplication.processEvents()
        self.shot_window = ScreenShotTool(self.process_image, self.show)
        self.shot_window.show()
        self.shot_window.activateWindow()
        self.shot_window.setFocus()

    def process_image(self, pil_img):
        self.show()
        self.last_screenshot = pil_img
        self.run_ocr(pil_img)

    def reparse_last_image(self):
        if self.is_running: return
        if self.last_screenshot is None:
            QMessageBox.warning(self, "无缓存", "尚未进行过截图。")
            return
        self.run_ocr(self.last_screenshot)

    def run_ocr(self, pil_img):
        self.set_ui_loading(True)
        url = self.url_input.text().strip()
        model = self.model_input.text().strip()
        prompt = self.prompt_input.toPlainText().strip()

        self.status_label.setText(f"状态: 正在识别 ({model})...")
        self.worker = OCRWorker(pil_img, url, model, prompt)
        self.worker.finished.connect(self.on_ocr_success)
        self.worker.error.connect(self.on_ocr_error)
        self.worker.start()

    def on_ocr_success(self, raw_text):
        self.set_ui_loading(False)
        self.result_area.setText(raw_text)
        pyperclip.copy(raw_text)
        self.status_label.setText("状态: 识别完成")

    def on_ocr_error(self, err):
        self.set_ui_loading(False)
        self.status_label.setText("状态: 识别失败")
        self.result_area.setText(f"错误信息:\n{err}")

    def closeEvent(self, event):
        # 退出时停止监听器
        if hasattr(self, 'listener'):
            self.listener.stop()
        save_to_disk(self.url_input.text().strip(), self.model_input.text().strip(),
                     self.prompt_input.toPlainText().strip())
        super().closeEvent(event)


def main():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("my_company.glm_ocr.gui.v1")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()