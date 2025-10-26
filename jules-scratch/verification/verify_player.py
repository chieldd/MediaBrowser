
import sys
import os
from PyQt5 import QtWidgets, QtCore
from pytestqt.qtbot import QtBot
from vlc_player import MainWindow, TileButton, MediaPlayer

# Add the current directory to the python path to allow imports
sys.path.insert(0, os.getcwd())

def test_media_player_screenshot(qtbot):
    """
    Tests that the media player opens and takes a screenshot.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Find the first movie tile and click it
    movie_tile = window.findChild(TileButton)
    assert movie_tile is not None
    qtbot.mouseClick(movie_tile, QtCore.Qt.LeftButton)

    # Wait for the player to appear
    qtbot.waitUntil(lambda: isinstance(window.stacked.currentWidget(), MediaPlayer), timeout=5000)
    player = window.stacked.currentWidget()
    assert player is not None

    # Take a screenshot
    screenshot = window.grab()
    screenshot.save("jules-scratch/verification/verification.png", "png")
