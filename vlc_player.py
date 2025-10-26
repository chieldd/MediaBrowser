import sys
import os
import json
import sqlite3
import subprocess
from PyQt5 import QtWidgets, QtGui, QtCore
import vlc
import requests

CONFIG_PATH = os.path.join(os.getcwd(), 'video_config.json')
METADATA_PATH = os.path.join(os.getcwd(), 'media_metadata.db')

def get_metadata(video_path):
    conn = sqlite3.connect(METADATA_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, release_date, duration, description, director, genre, rating, resolution, thumbnail FROM media WHERE file_path=?", (video_path,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'title': row[0],
            'release_date': row[1],
            'duration': row[2],
            'description': row[3],
            'director': row[4],
            'genre': row[5],
            'rating': row[6],
            'resolution': row[7],
            'thumbnail': row[8]
        }
    return {}

class ImageLoader(QtCore.QThread):
    imageLoaded = QtCore.pyqtSignal(QtGui.QPixmap, object)
    def __init__(self, url, tile):
        super().__init__()
        self.url = url
        self.tile = tile
    def run(self):
        try:
            img_data = requests.get(self.url, timeout=10).content
            image = QtGui.QImage()
            image.loadFromData(img_data)
            pixmap = QtGui.QPixmap(image).scaled(200, 260, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.imageLoaded.emit(pixmap, self.tile)
        except Exception:
            self.imageLoaded.emit(QtGui.QPixmap(), self.tile)

class TileButton(QtWidgets.QPushButton):
    def __init__(self, title, image_path, video_path, metadata_url, parent=None, tile_width=220, tile_height=320, horizontal=False, show_title=True):
        super().__init__(parent)
        self.video_path = video_path
        self.metadata_url = metadata_url
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.horizontal = horizontal
        self.setFixedSize(tile_width, tile_height)
        self.setStyleSheet('background: #222; border-radius: 18px;')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.img_label = QtWidgets.QLabel(self)
        self.img_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        self.img_label.setFixedSize(tile_width, tile_height)
        self.img_label.setStyleSheet('border-radius: 18px;')
        if image_path:
            if image_path.startswith('http://') or image_path.startswith('https://'):
                self.loader = ImageLoader(image_path, self)
                self.loader.imageLoaded.connect(self.set_pixmap)
                self.loader.start()
            elif os.path.exists(image_path):
                pixmap = QtGui.QPixmap(image_path).scaled(tile_width, tile_height, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
                rounded = QtGui.QPixmap(tile_width, tile_height)
                rounded.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(rounded)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                path = QtGui.QPainterPath()
                path.addRoundedRect(0, 0, tile_width, tile_height, 18, 18)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                self.img_label.setPixmap(rounded)
            layout.addWidget(self.img_label)
        else:
            layout.addWidget(self.img_label)
        if show_title:
            title_label = QtWidgets.QLabel(title, self)
            title_label.setFixedWidth(tile_width)
            title_label.setWordWrap(True)
            title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            title_label.setStyleSheet('background: #222; color: #fff; font-size: 1.1em; font-weight: 600; margin-top: 8px; padding-left: 12px; padding-right: 12px; border-radius: 8px;')
            layout.addWidget(title_label)
        self.setLayout(layout)
    
    def set_pixmap(self, pixmap, tile):
        if tile == self:
            rounded = QtGui.QPixmap(self.tile_width, self.tile_height)
            rounded.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(rounded)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            path = QtGui.QPainterPath()
            path.addRoundedRect(0, 0, self.tile_width, self.tile_height, 18, 18)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap.scaled(self.tile_width, self.tile_height, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
            painter.end()
            self.img_label.setPixmap(rounded)

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Media Browser')
        self.setStyleSheet('background-color: #111; color: #fff; font-family: Segoe UI, Arial, sans-serif;')

        # Main vertical layout
        self.root_layout = QtWidgets.QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Navigation bar
        nav_bar = QtWidgets.QWidget()
        nav_bar.setFixedHeight(60)
        nav_bar_layout = QtWidgets.QHBoxLayout(nav_bar)
        nav_bar_layout.setContentsMargins(20, 10, 20, 10)
        nav_bar_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.home_button = QtWidgets.QPushButton("Home")
        self.home_button.setStyleSheet("font-size: 1.2em; padding: 10px 20px; background: #333; border-radius: 10px;")
        self.home_button.clicked.connect(self.back_to_grid)
        nav_bar_layout.addWidget(self.home_button)

        self.back_button = QtWidgets.QPushButton("Back")
        self.back_button.setStyleSheet("font-size: 1.2em; padding: 10px 20px; background: #333; border-radius: 10px;")
        self.back_button.clicked.connect(self.back_to_grid)
        self.back_button.hide()
        nav_bar_layout.addWidget(self.back_button)

        self.root_layout.addWidget(nav_bar)

        # Stacked layout for different screens
        self.stacked = QtWidgets.QStackedLayout()
        self.root_layout.addLayout(self.stacked)

        # Scroll Area for the main grid
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.grid_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout(self.grid_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(30)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.scroll_area.setWidget(self.grid_widget)
        self.stacked.addWidget(self.scroll_area)

        self.setLayout(self.root_layout)

        with open(CONFIG_PATH, 'r') as f:
            self.config = json.load(f)

        self.showFullScreen()
        self.load_tiles()
    
    def resizeEvent(self, event):
        if self.stacked.currentWidget() == self.grid_widget:
            self.load_tiles()
        event.accept()
    
    def load_tiles(self):
        # Clear layout
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # If the item is a layout, clear its widgets
                layout = item.layout()
                while layout.count():
                    child_item = layout.takeAt(0)
                    if child_item.widget():
                        child_item.widget().deleteLater()
                
        video_dir = os.path.join(os.getcwd(), "/home/cdedood/Videos/2. Films")
        row_width = self.width() - 400
        tile_w = max(220, row_width // 7)
        tile_h = int(tile_w * 1.5)

        # Services label
        services_label = QtWidgets.QLabel("Services", self.grid_widget)
        services_label.setStyleSheet('font-size: 2.2em; font-weight: 700; color: #fff; margin-left: 24px; margin-bottom: 12px;')
        self.main_layout.addWidget(services_label, alignment=QtCore.Qt.AlignLeft)
        # Services row
        services_layout = QtWidgets.QHBoxLayout()
        services_layout.setContentsMargins(24,0,24,0)
        services_layout.setSpacing(50)
        services_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.netflix_button = QtWidgets.QPushButton("Netflix")
        self.netflix_button.setStyleSheet("font-size: 1.2em; padding: 10px 20px; background: #E50914; color: white; border-radius: 10px;")
        self.netflix_button.setFixedSize(200, 80)
        services_layout.addWidget(self.netflix_button)
        self.netflix_button.clicked.connect(lambda: self.launch_browser("https://www.netflix.com"))

        self.youtube_button = QtWidgets.QPushButton("YouTube")
        self.youtube_button.setStyleSheet("font-size: 1.2em; padding: 10px 20px; background: #FF0000; color: white; border-radius: 10px;")
        self.youtube_button.setFixedSize(200, 80)
        services_layout.addWidget(self.youtube_button)
        self.youtube_button.clicked.connect(lambda: self.launch_browser("https://www.youtube.com"))

        self.main_layout.addLayout(services_layout)

        # Movies label
        movies_label = QtWidgets.QLabel("Movies", self.grid_widget)
        movies_label.setStyleSheet('font-size: 2.2em; font-weight: 700; color: #fff; margin-left: 24px; margin-bottom: 12px;')
        self.main_layout.addWidget(movies_label, alignment=QtCore.Qt.AlignLeft)
        # Movies rows
        video_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if os.path.isfile(os.path.join(video_dir, f)) and f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))]

        # Responsive grid for movies
        max_cols = max(1, self.grid_widget.width() // (tile_w + 30))
        m_row_tiles = []
        for idx, video_path in enumerate(video_files):
            meta = get_metadata(video_path)
            title = meta.get('title', os.path.basename(video_path))
            image_path = meta.get('thumbnail', '')
            metadata_url = None
            btn = TileButton(title, image_path, video_path, metadata_url, parent=self.grid_widget, tile_width=tile_w, tile_height=tile_h, show_title=False)
            btn.clicked.connect(lambda checked, vp=video_path, mu=metadata_url: self.open_player(vp, mu))
            m_row_tiles.append(btn)
        for i in range(0, len(m_row_tiles), max_cols):
            row_layout = QtWidgets.QHBoxLayout()
            row_layout.setContentsMargins(24,0,24,0)
            row_layout.setSpacing(50)
            row_layout.setAlignment(QtCore.Qt.AlignLeft)
            for btn in m_row_tiles[i:i+max_cols]:
                row_layout.addWidget(btn)
            self.main_layout.addLayout(row_layout)
        # Shows label
        shows_label = QtWidgets.QLabel("Shows", self.grid_widget)
        shows_label.setStyleSheet('font-size: 2.2em; font-weight: 700; color: #fff; margin-left: 24px; margin-bottom: 12px; margin-top: 32px;')
        self.main_layout.addWidget(shows_label, alignment=QtCore.Qt.AlignLeft)
        # Shows rows
        show_dirs = [os.path.join(video_dir, d) for d in os.listdir(video_dir) if os.path.isdir(os.path.join(video_dir, d))]
        s_row_tiles = []
        for idx, show_path in enumerate(show_dirs):
            conn = sqlite3.connect(METADATA_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT title, poster FROM shows WHERE folder=?", (os.path.basename(show_path),))
            show_row = cursor.fetchone()
            conn.close()
            if show_row:
                title = show_row[0]
                image_path = show_row[1]
                btn = TileButton(title, image_path, show_path, None, parent=self.grid_widget, tile_width=tile_w, tile_height=tile_h, show_title=False)
                btn.clicked.connect(lambda checked, sp=show_path, ip=image_path, t=title: self.show_overview(sp, ip, t))
                s_row_tiles.append(btn)
        for i in range(0, len(s_row_tiles), max_cols):
            row_layout = QtWidgets.QHBoxLayout()
            row_layout.setContentsMargins(24,0,24,0)
            row_layout.setSpacing(50)
            row_layout.setAlignment(QtCore.Qt.AlignLeft)
            for btn in s_row_tiles[i:i+max_cols]:
                row_layout.addWidget(btn)
            self.main_layout.addLayout(row_layout)
    def open_player(self, video_path, metadata_url):
        self.player_window = VLCPlayer(video_path, metadata_url)
        self.player_window.show()
    def show_overview(self, show_folder, poster_url, show_title):
        overview_widget = QtWidgets.QWidget(self)
        overview_widget.setStyleSheet('background: #111;')
        overview_widget.setFixedSize(self.width(), self.height())
        bg_label = QtWidgets.QLabel(overview_widget)
        bg_label.setFixedSize(self.width(), self.height())
        bg_label.move(0, 0)
        bg_label.lower()
        def set_bg(pixmap, _):
            img = pixmap.toImage()
            img = img.convertToFormat(QtGui.QImage.Format_ARGB32)
            for y in range(img.height()):
                for x in range(img.width()):
                    c = QtGui.QColor(img.pixel(x, y))
                    c = c.darker(180)
                    img.setPixelColor(x, y, c)
            bg_label.setPixmap(QtGui.QPixmap(img).scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
        if poster_url:
            loader = ImageLoader(poster_url, self)
            loader.imageLoaded.connect(set_bg)
            loader.start()
        panel_w = int(self.width() * 0.8)
        panel_h = int(self.height() * 0.85)
        panel_x = int((self.width() - panel_w) / 2)
        panel_y = int((self.height() - panel_h) / 2)
        panel = QtWidgets.QWidget(overview_widget)
        panel.setFixedSize(panel_w, panel_h)
        panel.move(panel_x, panel_y)
        panel.setStyleSheet('background: rgba(30,30,30,0.8); border-radius: 24px;')
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(32,32,32,32)
        # Title frame (transparent)
        title_frame = QtWidgets.QWidget(panel)
        title_frame.setStyleSheet('background: transparent;')
        title_layout = QtWidgets.QVBoxLayout(title_frame)
        title_layout.setContentsMargins(16,8,16,8)
        title_label = QtWidgets.QLabel(show_title, title_frame)
        title_label.setStyleSheet('font-size: 2em; font-weight: 600; color: #fff;')
        title_label.setFixedHeight(60)
        title_layout.addWidget(title_label)
        # Dropdown not full width
        season_dropdown = QtWidgets.QComboBox(title_frame)
        season_dropdown.setStyleSheet('font-size: 1.2em; background: rgba(30,30,30,0.5); border-radius: 8px; color: #fff;')
        season_dropdown.setFixedWidth(220)
        season_dropdown.setFixedHeight(40)
        title_layout.addWidget(season_dropdown, alignment=QtCore.Qt.AlignLeft)
        panel_layout.addWidget(title_frame)
        # Episode grid frame (transparent)
        episode_grid_container = QtWidgets.QWidget(panel)
        episode_grid_container.setStyleSheet('background: transparent;')
        episode_grid_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        episode_grid = QtWidgets.QGridLayout(episode_grid_container)
        episode_grid.setContentsMargins(16,16,16,16)
        panel_layout.addWidget(episode_grid_container)
        seasons = [d for d in os.listdir(show_folder) if os.path.isdir(os.path.join(show_folder, d)) and d.lower().startswith('season')]
        seasons.sort()
        for season in seasons:
            season_dropdown.addItem(season)
        def load_episodes(idx):
            for i in reversed(range(episode_grid.count())):
                episode_grid.itemAt(i).widget().setParent(None)
            season_name = season_dropdown.currentText()
            season_path = os.path.join(show_folder, season_name)
            episodes = [f for f in os.listdir(season_path) if os.path.isfile(os.path.join(season_path, f)) and f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))]
            episodes.sort()
            erow, ecol = 0, 0
            ep_w = max(180, (panel_w - 150) // 6)
            ep_h = max(200, (panel_h - 150) // 4)
            for ep in episodes:
                ep_path = os.path.join(season_path, ep)
                meta = get_metadata(ep_path)
                title = meta.get('title', os.path.basename(ep_path))
                image_path = meta.get('thumbnail', '')
                btn = TileButton(title, image_path, ep_path, None, parent=episode_grid_container, tile_width=ep_w, tile_height=ep_h, horizontal=True)
                btn.clicked.connect(lambda checked, vp=ep_path: self.open_player(vp, None))
                episode_grid.addWidget(btn, erow, ecol)
                ecol += 1
                if ecol >= 6:
                    ecol = 0
                    erow += 1
        season_dropdown.currentIndexChanged.connect(load_episodes)
        if seasons:
            load_episodes(0)
        self.stacked.addWidget(overview_widget)
        self.stacked.setCurrentWidget(overview_widget)
        self.back_button.show()

    def back_to_grid(self):
        self.stacked.setCurrentWidget(self.scroll_area)
        self.back_button.hide()

    def launch_browser(self, url):
        browser_executable = self.config.get("browser_executable", "chromium")
        self.browser_process = subprocess.Popen([browser_executable, "--kiosk", url])
        self.control_bar = BrowserControlBar(self.browser_process)
        self.control_bar.show()

        self.check_timer = QtCore.QTimer(self)
        self.check_timer.timeout.connect(self.check_browser_status)
        self.check_timer.start(500)  # Check every 500ms

    def check_browser_status(self):
        if self.browser_process.poll() is not None:  # Process has terminated
            self.check_timer.stop()
            self.control_bar.close()
            self.activateWindow()
            self.back_to_grid()

class VLCPlayer(QtWidgets.QWidget):
    def __init__(self, video_path, metadata_url):
        super().__init__()
        self.setWindowTitle('Play Video')
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet('background-color: #111; color: #fff; font-family: Segoe UI, Arial, sans-serif;')
        self.info_panel = QtWidgets.QWidget(self)
        self.info_panel.setStyleSheet('background: rgba(0,0,0,0.7); border-radius: 16px; padding: 24px 32px;')
        self.info_panel.setGeometry(100, 40, 1000, 180)
        self.title_label = QtWidgets.QLabel('', self.info_panel)
        self.title_label.setStyleSheet('font-size: 1.8em; font-weight: 600; color: #fff;')
        self.meta_label = QtWidgets.QLabel('', self.info_panel)
        self.meta_label.setStyleSheet('font-size: 1em; color: #ccc;')
        self.desc_label = QtWidgets.QLabel('', self.info_panel)
        self.desc_label.setStyleSheet('font-size: 1em; color: #eee;')
        self.rating_label = QtWidgets.QLabel('', self.info_panel)
        self.rating_label.setStyleSheet('font-size: 1em; color: #FFD700;')
        vbox = QtWidgets.QVBoxLayout(self.info_panel)
        vbox.addWidget(self.title_label)
        vbox.addWidget(self.meta_label)
        vbox.addWidget(self.desc_label)
        vbox.addWidget(self.rating_label)
        self.info_panel.setLayout(vbox)
        self.instance = vlc.Instance()
        self.mediaplayer = self.instance.media_player_new()
        self.videoframe = QtWidgets.QFrame(self)
        self.videoframe.setGeometry(100, 240, 1000, 560)
        self.videoframe.setStyleSheet('background: #000; border-radius: 12px;')
        if sys.platform == "linux":
            self.mediaplayer.set_xwindow(int(self.videoframe.winId()))
        elif sys.platform == "win32":
            self.mediaplayer.set_hwnd(int(self.videoframe.winId()))
        elif sys.platform == "darwin":
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))
        self.load_metadata(video_path)
        self.play_video(video_path)
    
    def load_metadata(self, video_path):
        meta = get_metadata(video_path)
        self.title_label.setText(meta.get('title', ''))
        meta_text = ''
        if meta.get('release_date'):
            meta_text += f"Release: {meta.get('release_date')}"
        self.meta_label.setText(meta_text)
        self.desc_label.setText(meta.get('description', ''))
        rating = meta.get('rating', meta.get('vote_average', ''))
        if rating:
            stars = '★' * int(round(float(rating))) + '☆' * (10 - int(round(float(rating))))
            self.rating_label.setText(f'Rating: {stars} ({rating}/10)')
    def play_video(self, path):
        if os.path.exists(path):
            media = self.instance.media_new(path)
            self.mediaplayer.set_media(media)
            self.mediaplayer.play()

class BrowserControlBar(QtWidgets.QWidget):
    def __init__(self, browser_process):
        super().__init__()
        self.browser_process = browser_process
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(80, 80)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.back_button = QtWidgets.QPushButton("←")
        self.back_button.setFixedSize(60, 60)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 30px;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.7);
            }
        """)
        self.back_button.clicked.connect(self.close_browser)
        layout.addWidget(self.back_button)
        self.setLayout(layout)
        self.setGeometry(20, 20, 80, 80)

        self.fade_timer = QtCore.QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.hide)
        self.fade_timer.start(10000)

        self.check_mouse_timer = QtCore.QTimer(self)
        self.check_mouse_timer.timeout.connect(self.check_mouse_pos)
        self.check_mouse_timer.start(100) # Check every 100ms

    def check_mouse_pos(self):
        pos = QtGui.QCursor.pos()
        if pos.x() < 100 and pos.y() < 100:
            if self.isHidden():
                self.show()
                self.fade_timer.start(10000)

    def close_browser(self):
        self.browser_process.kill()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
