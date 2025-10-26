import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt

# URL of your home page
HOME_URL = "http://localhost:3000"

class BarApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #222; color: #fff;")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)

        home_btn = QPushButton("Home")
        home_btn.setStyleSheet("font-size: 20px; padding: 10px 30px; background: #444; color: #fff; border-radius: 10px;")
        home_btn.clicked.connect(self.go_home)
        layout.addWidget(home_btn)

        self.setLayout(layout)
        self.setGeometry(0, 0, QApplication.desktop().screenGeometry().width(), 60)

    def go_home(self):
        # Kill all Chromium processes
        subprocess.call(["pkill", "chromium"])
        # Start Chromium in kiosk mode with the home URL
        subprocess.Popen(["chromium-browser", "--kiosk", HOME_URL])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    bar = BarApp()
    bar.show()
    sys.exit(app.exec_())
