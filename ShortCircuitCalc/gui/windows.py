# -*- coding: utf-8 -*-
"""The module contains at the moment the ScrollableWindow class, which is
used to display figures in a scrollable window using PyQt5 and Matplotlib.
The class provides methods for initializing the GUI, setting basic window
information, and displaying the window."""


import sys
import typing as ty
import matplotlib


from PyQt5.QtWidgets import (
                        QWidget,
                        QApplication,
                        QMainWindow,
                        QVBoxLayout,
                        QScrollArea,
                        QDesktopWidget,
                    )

from matplotlib.backends.backend_qt5agg import (
                        FigureCanvasQTAgg as FigCanvas,
                        NavigationToolbar2QT as NabToolbar,
                    )


__all__ = ('ScrollableWindow',)


# Select the backend used for rendering and GUI integration.
matplotlib.use('Qt5Agg')


class ScrollableWindow(QWidget):
    """Class for displaying figure in a scrollable window"""

    def __init__(self, figure: matplotlib.figure.Figure, title: ty.Union[str, ty.Callable],
                 window_x: int = 800, window_y: int = 640) -> None:
        """Initialize a ScrollableWindow object.

        Args:
            figure (matplotlib.figure.Figure): The figure to display in the window.
            title (str): The title of the window.
            window_x (int, optional): The width of the window in pixels. Defaults to 800.
            window_y (int, optional): The height of the window in pixels. Defaults to 640.

        """
        super().__init__()
        self.title = title
        self.windowSize = (window_x, window_y)
        self.posXY = ScrollableWindow.window_auto_center(self.windowSize)
        self.figure = figure
        self.init_gui()
        self.show_window()

    def init_gui(self):
        """Initializes the GUI components for displaying the figure."""
        QMainWindow().setCentralWidget(QWidget())

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        canvas = FigCanvas(self.figure)
        canvas.draw()

        scroll = QScrollArea(self)
        scroll.setWidget(canvas)

        nav = NabToolbar(canvas, self)
        self.layout().addWidget(nav)
        self.layout().addWidget(scroll)

        self.show_basic()

    def show_basic(self):
        """Sets the window title, geometry, and shows the window.

        This method sets the window title to the value of the 'title' attribute
        of the 'ScrollableWindow' object. It then sets the geometry of the window
        using the 'posXY' and 'windowSize' attributes. Finally, it shows the window.

        Parameters:
            self (ScrollableWindow): The 'ScrollableWindow' object.

        """
        self.setWindowTitle(self.title)
        self.setGeometry(*self.posXY, *self.windowSize)
        self.show()

    @staticmethod
    def show_window():
        """Main method that creates a QApplication instance and runs the event loop.

        This method creates a QApplication instance using the command line arguments
        and runs the event loop using the app.exec_() method. The program will exit
        after the event loop is finished.

        """
        app = QApplication(sys.argv)
        sys.exit(app.exec_())

    @staticmethod
    def window_auto_center(window_size):
        """Centers the window on the screen.

        Args:
            window_size (tuple): A tuple containing the width and height of the window.

        Returns:
            tuple: A tuple containing the x and y coordinates of the window's top-left corner.

        """
        window_width, window_height = window_size
        desktop = QDesktopWidget().screenGeometry()
        screen_width = desktop.width()
        screen_height = desktop.height()
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        return x, y