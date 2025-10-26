from PyQt5 import QtWidgets, QtGui, QtCore
import requests
from io import BytesIO
from PIL import Image
import os
import sys

class MediaTile(QtWidgets.QWidget, QtWidgets.QPushButton):
    def __init__(self, media_path, width=220, parent=None):
        SQLiteDB = parent.SQLiteDB  # Assuming parent has an attribute SQLiteDB
        self.width = width
        self.height = int(width * 1.5)
        self.setFixedSize(self.width, self.height)
        self.setStyleSheet('border-radius: 18px; background: #222;')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.img_label = QtWidgets.QLabel(self)
        self.img_label.setFixedSize(self.width, self.height)
        self.img_label.setAlignment(QtCore.Qt.AlignCenter)
        self.img_label.setStyleSheet('border-radius: 18px;')
        self.title, poster_path = SQLiteDB.fetch_tile_data(media_path)
        
        if poster_path:
            response = requests.get(poster_path)
            img = Image.open(BytesIO(response.content))
            if img.height > img.width:
                # Vertical: fill whole tile, rounded corners
                qimg = QtGui.QImage()
                qimg.loadFromData(response.content)
                pixmap = QtGui.QPixmap.fromImage(qimg).scaled(self.width, self.height, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
                rounded = QtGui.QPixmap(self.width, self.height)
                rounded.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(rounded)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                path = QtGui.QPainterPath()
                path.addRoundedRect(0, 0, self.width, self.height, 18, 18)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                self.img_label.setPixmap(rounded)
            else:
                # Square or horizontal: fill width, rounded only top, bottom dark gray with title
                qimg = QtGui.QImage()
                qimg.loadFromData(response.content)
                img_pixmap = QtGui.QPixmap.fromImage(qimg).scaled(self.width, int(self.width * img.height / img.width), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                total_pixmap = QtGui.QPixmap(self.width, self.height)
                total_pixmap.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(total_pixmap)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                # Rounded only top
                path = QtGui.QPainterPath()
                path.moveTo(0, self.height)
                path.lineTo(0, 18)
                path.quadTo(0, 0, 18, 0)
                path.lineTo(self.width-18, 0)
                path.quadTo(self.width, 0, self.width, 18)
                path.lineTo(self.width, self.height)
                path.lineTo(0, self.height)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, img_pixmap)
                painter.setClipping(False)
                # Draw dark gray bottom
                bottom_rect = QtCore.QRect(0, img_pixmap.height(), self.width, self.height - img_pixmap.height())
                painter.fillRect(bottom_rect, QtGui.QColor(34,34,34))
                # Draw title
                painter.setPen(QtGui.QColor('#fff'))
                font = QtGui.QFont()
                font.setPointSize(13)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(bottom_rect, QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, self.title)
                painter.end()
                self.img_label.setPixmap(total_pixmap)
        layout.addWidget(self.img_label)
        self.setLayout(layout)

        if __name__ == "__main__":

            class DummyParent(QtWidgets.QWidget):
                def __init__(self):
                    super().__init__()
                    # Dummy SQLiteDB with fetch_tile_data method
                    class DummyDB:
                        def fetch_tile_data(self, media_path):
                            # Example: return title and poster URL
                            return ("Deepwater Horizon", "https://upload.wikimedia.org/wikipedia/en/2/2e/Deepwater_Horizon_poster.png")
                    self.SQLiteDB = DummyDB()

            app = QtWidgets.QApplication(sys.argv)
            parent = DummyParent()
            media_path = os.path.expanduser("~/Videos/2. Films/Deepwater Horizon.mkv")
            tile = MediaTile(media_path, parent=parent)
            window = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(window)
            layout.addWidget(tile)
            window.setWindowTitle("Media Tile Demo")
            window.show()
            sys.exit(app.exec_())