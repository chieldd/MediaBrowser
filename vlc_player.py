import sys
import os
import json
import sqlite3
import subprocess
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaService
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtSvg import QSvgRenderer
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
        self.nav_bar = QtWidgets.QWidget()
        self.nav_bar.setFixedHeight(60)
        nav_bar_layout = QtWidgets.QHBoxLayout(self.nav_bar)
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

        self.root_layout.addWidget(self.nav_bar)

        # Stacked layout for different screens
        self.stacked = QtWidgets.QStackedLayout()
        self.root_layout.addLayout(self.stacked)

        # Scroll Area for the main grid
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

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
        if self.stacked.currentWidget() == self.scroll_area:
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
        tile_w = 220
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
        max_cols = max(1, self.scroll_area.viewport().width() // (tile_w + 30))
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
        for i in range(0, len(s_row_tiles), max(1, self.scroll_area.viewport().width() // (tile_w + 30))):
            row_layout = QtWidgets.QHBoxLayout()
            row_layout.setContentsMargins(24,0,24,0)
            row_layout.setSpacing(50)
            row_layout.setAlignment(QtCore.Qt.AlignLeft)
            for btn in s_row_tiles[i:i+max_cols]:
                row_layout.addWidget(btn)
            self.main_layout.addLayout(row_layout)
    def open_player(self, video_path, metadata_url=None):
        self.player_widget = MediaPlayer(video_path, self, self)
        self.stacked.addWidget(self.player_widget)
        self.stacked.setCurrentWidget(self.player_widget)
        self.back_button.show()
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
        if hasattr(self, 'player_widget') and self.player_widget:
            self.player_widget.media_player.stop()
            self.player_widget.deleteLater()
            self.player_widget = None
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

class ClickableSlider(QtWidgets.QSlider):
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            value = self.minimum() + (self.maximum() - self.minimum()) * event.x() / self.width()
            self.setValue(int(value))
            event.accept()
            self.sliderMoved.emit(self.value())
        super().mousePressEvent(event)

def create_colored_icon(icon_path, color):
    renderer = QSvgRenderer(icon_path)
    pixmap = QtGui.QPixmap(renderer.defaultSize())
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return QtGui.QIcon(pixmap)

class MediaPlayer(QtWidgets.QWidget):
    def __init__(self, video_path, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_fullscreen = False
        self.setStyleSheet('background-color: #000; color: #fff; font-family: Segoe UI, Arial, sans-serif;')
        self.icon_color = QtGui.QColor(255, 255, 255, 153) # White with 60% opacity

        # Main layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        # Center Panel
        self.panel = QtWidgets.QWidget()
        self.panel.setFixedWidth(int(self.main_window.width() * 0.6))
        self.panel_layout = QtWidgets.QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(20, 20, 20, 20)
        self.video_layout = layout
        layout.addWidget(self.panel)

        # --- Metadata Section ---
        self.metadata_widget = QtWidgets.QWidget()
        metadata_layout = QtWidgets.QVBoxLayout(self.metadata_widget)
        metadata_layout.setContentsMargins(0, 0, 0, 15)

        meta = get_metadata(video_path)
        title = meta.get('title', os.path.basename(video_path))
        description = meta.get('description', 'No description available.')
        rating = meta.get('rating', 'N/A')
        release_date = meta.get('release_date', '')
        duration = meta.get('duration', '')

        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet('font-size: 2.5em; font-weight: 700;')
        metadata_layout.addWidget(self.title_label)

        details_text = f"Rating: {rating} | Released: {release_date} | Duration: {duration} mins"
        self.details_label = QtWidgets.QLabel(details_text)
        self.details_label.setStyleSheet('font-size: 1.1em; color: #aaa; margin-top: 5px;')
        metadata_layout.addWidget(self.details_label)

        self.description_label = QtWidgets.QLabel(description)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet('font-size: 1.2em; margin-top: 15px;')
        metadata_layout.addWidget(self.description_label)

        self.panel_layout.addWidget(self.metadata_widget)

        # --- Video Player Section ---
        player_container = QtWidgets.QWidget()
        player_layout = QtWidgets.QGridLayout(player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)

        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("background-color: black;")
        player_layout.addWidget(self.video_widget, 0, 0)

        # Ensure the video respects the aspect ratio
        self.video_widget.setAspectRatioMode(QtCore.Qt.KeepAspectRatio)

        # --- Controls Overlay ---
        self.controls_widget = QtWidgets.QWidget()
        self.controls_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0.6);")
        self.controls_layout = QtWidgets.QHBoxLayout(self.controls_widget)
        self.controls_layout.setContentsMargins(10, 5, 10, 5)
        player_layout.addWidget(self.controls_widget, 0, 0, QtCore.Qt.AlignBottom)

        self.panel_layout.addWidget(player_container, stretch=1)

        self.play_pause_button = QtWidgets.QPushButton()
        self.play_pause_button.setIconSize(QtCore.QSize(32, 32))
        self.play_pause_button.setStyleSheet("background: transparent; border: none;")
        self.play_pause_button.setIcon(create_colored_icon("icons/play.svg", self.icon_color))
        self.play_pause_button.clicked.connect(self.toggle_playback)
        self.controls_layout.addWidget(self.play_pause_button)

        self.skip_backward_button = QtWidgets.QPushButton()
        self.skip_backward_button.setIconSize(QtCore.QSize(32, 32))
        self.skip_backward_button.setStyleSheet("background: transparent; border: none;")
        self.skip_backward_button.setIcon(create_colored_icon("icons/skip-backward.svg", self.icon_color))
        self.skip_backward_button.clicked.connect(self.skip_backward)
        self.controls_layout.addWidget(self.skip_backward_button)

        self.skip_forward_button = QtWidgets.QPushButton()
        self.skip_forward_button.setIconSize(QtCore.QSize(32, 32))
        self.skip_forward_button.setStyleSheet("background: transparent; border: none;")
        self.skip_forward_button.setIcon(create_colored_icon("icons/skip-forward.svg", self.icon_color))
        self.skip_forward_button.clicked.connect(self.skip_forward)
        self.controls_layout.addWidget(self.skip_forward_button)

        self.seek_slider = ClickableSlider(QtCore.Qt.Horizontal)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #555;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #E50914;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                border: 2px solid #fff;
                width: 18px;
                height: 18px;
                margin-top: -7px;
                margin-bottom: -7px;
                border-radius: 0px;
            }
        """)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_slider.sliderPressed.connect(self.start_seek)
        self.seek_slider.sliderReleased.connect(self.end_seek)
        self.seek_slider.setMouseTracking(True)
        self.seek_slider.installEventFilter(self)
        self.controls_layout.addWidget(self.seek_slider)

        self.remaining_time_label = QtWidgets.QLabel("--:--")
        self.remaining_time_label.setFixedWidth(100)
        self.remaining_time_label.setStyleSheet("color: #fff; margin-left: 10px; font-size: 1.1em;")
        self.controls_layout.addWidget(self.remaining_time_label)

        self.fullscreen_button = QtWidgets.QPushButton()
        self.fullscreen_button.setIconSize(QtCore.QSize(32, 32))
        self.fullscreen_button.setStyleSheet("background: transparent; border: none;")
        self.fullscreen_button.setIcon(create_colored_icon("icons/fullscreen.svg", self.icon_color))
        self.fullscreen_button.clicked.connect(self.toggle_full_screen)
        self.controls_layout.addWidget(self.fullscreen_button)

        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(video_path)))

        # Auto-hide controls
        self.hide_controls_timer = QtCore.QTimer(self)
        self.hide_controls_timer.setSingleShot(True)
        self.hide_controls_timer.timeout.connect(self.hide_controls)
        self.video_widget.setMouseTracking(True)
        self.video_widget.installEventFilter(self)
        self.controls_widget.installEventFilter(self)

        # Connect signals
        self.media_player.stateChanged.connect(self.update_play_pause_button)
        self.is_seeking = False
        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.durationChanged.connect(self.set_slider_range)

    def start_seek(self):
        self.is_seeking = True

    def end_seek(self):
        self.is_seeking = False
        self.set_position(self.seek_slider.value())

    def skip_forward(self):
        self.media_player.setPosition(self.media_player.position() + 10000)

    def skip_backward(self):
        self.media_player.setPosition(self.media_player.position() - 10000)

    def toggle_playback(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_pause_button(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_pause_button.setIcon(create_colored_icon("icons/pause.svg", self.icon_color))
        else:
            self.play_pause_button.setIcon(create_colored_icon("icons/play.svg", self.icon_color))

    def update_slider_position(self, position):
        if not self.is_seeking:
            self.seek_slider.setValue(position)
        self.update_time_label(position)

    def update_time_label(self, position):
        duration = self.media_player.duration()
        remaining = duration - position
        if remaining < 0:
            remaining = 0

        hours = remaining // 3600000
        minutes = (remaining % 3600000) // 60000
        seconds = (remaining % 60000) // 1000

        if hours > 0:
            self.remaining_time_label.setText(f"{hours}:{minutes:02}:{seconds:02}")
        else:
            self.remaining_time_label.setText(f"{minutes:02}:{seconds:02}")

    def set_slider_range(self, duration):
        self.seek_slider.setRange(0, duration)
        self.update_time_label(0)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == QtCore.Qt.Key_Escape and self.is_fullscreen:
            self.toggle_full_screen()
        else:
            super().keyPressEvent(event)

    def toggle_full_screen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.main_window.showFullScreen()
            self.main_window.nav_bar.hide()
            self.metadata_widget.hide()
            self.panel.setFixedWidth(self.main_window.width())
            self.video_layout.setContentsMargins(0, 0, 0, 0)
            self.controls_widget.setParent(self.video_widget)
            self.controls_widget.show()
            self.fullscreen_button.setIcon(create_colored_icon("icons/exitfullscreen.svg", self.icon_color))
            self.panel_layout.setContentsMargins(0, 0, 0, 0)
        else:
            self.controls_widget.setParent(self.panel)
            self.panel_layout.addWidget(self.controls_widget)
            self.main_window.showFullScreen()
            self.main_window.nav_bar.show()
            self.metadata_widget.show()
            self.panel.setFixedWidth(int(self.main_window.width() * 0.6))
            self.video_layout.setContentsMargins(10, 10, 10, 10)
            self.fullscreen_button.setIcon(create_colored_icon("icons/fullscreen.svg", self.icon_color))
            self.panel_layout.setContentsMargins(20, 20, 20, 20)

    def eventFilter(self, source, event):
        if source in [self.video_widget, self.controls_widget]:
            if event.type() == QtCore.QEvent.MouseMove:
                self.show_controls()
                self.hide_controls_timer.start(5000)
            elif event.type() == QtCore.QEvent.Enter:
                self.show_controls()

        return super().eventFilter(source, event)

    def show_controls(self):
        self.controls_widget.show()
        self.fade_in_animation()

    def hide_controls(self):
        self.fade_out_animation()

    def fade_in_animation(self):
        fade_in = QtWidgets.QGraphicsOpacityEffect()
        self.controls_widget.setGraphicsEffect(fade_in)
        self.animation = QtCore.QPropertyAnimation(fade_in, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

    def fade_out_animation(self):
        fade_out = QtWidgets.QGraphicsOpacityEffect()
        self.controls_widget.setGraphicsEffect(fade_out)
        self.animation = QtCore.QPropertyAnimation(fade_out, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.controls_widget.hide)
        self.animation.start()

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
        if pos.x() < 200 and pos.y() < 200:
            if self.isHidden():
                self.show()
                self.fade_timer.start(10000)

    def closeEvent(self, event):
        self.fade_timer.stop()
        self.check_mouse_timer.stop()
        event.accept()

    def close_browser(self):
        self.browser_process.kill()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
