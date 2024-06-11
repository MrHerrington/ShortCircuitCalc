# -*- coding: utf-8 -*-
"""
The module contains GUI windows templates, using PyQt5 and Matplotlib.
Classes are based on ui files, developed by QtDesigner and customized.

"""


from collections import namedtuple
from decimal import Decimal
import typing as ty
from dataclasses import asdict

import logging
import matplotlib
# Need for figure matplotlib annotation
# noinspection PyUnresolvedReferences
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigCanvas,
    NavigationToolbar2QT as NavToolbar,
)
from PyQt5 import QtWidgets, QtCore, QtGui, uic

# Need for correctly loading icons
# noinspection PyUnresolvedReferences
import shortcircuitcalc.gui.resources
from shortcircuitcalc.gui.figures import ResultsFigure, CatalogFigure
from shortcircuitcalc.database import (
    Transformer, Cable, CurrentBreaker, OtherContact,
    db_install,

    InsertTrans, UpdateTransOldSource, UpdateTransNewSource, UpdateTransRow, DeleteTrans,
    InsertCable, UpdateCableOldSource, UpdateCableNewSource, UpdateCableRow, DeleteCable,
    InsertContact, UpdateContactOldSource, UpdateContactNewSource, UpdateContactRow, DeleteContact,
    InsertResist, UpdateResistOldSource, UpdateResistNewSource, UpdateResistRow, DeleteResist
)
from shortcircuitcalc.tools import config_manager, logging_error, ChainsSystem
from shortcircuitcalc.config import GUI_DIR


__all__ = ('MainWindow', 'DatabaseBrowser', 'CustomGraphicView', 'ConfirmWindow')


# Select the backend used for rendering and GUI integration.
matplotlib.use('Qt5Agg')


logger = logging.getLogger(__name__)
GW = ty.TypeVar('GW', bound=ty.Union[QtWidgets.QMainWindow, QtWidgets.QWidget])


#######################
# Inner functionality #
#######################

class CustomGraphicView(QtWidgets.QGraphicsView):
    """Initializes a CustomGraphicView object.

    Args:
        parent (Optional[QtWdgets.QWidget], optional): The parent widget for the CustomGraphicView.
        Defaults to None.

    Initializes the following instance variables:
        - _scene (QtWidgets.QGraphicsScene): The graphics scene for the CustomGraphicView.
        - _canvas (FigCanvas): The Matplotlib figure canvas for the CustomGraphicView.
        - _zoom (int): The current zoom level of the CustomGraphicView.
        - _mousePressed (bool): Flag indicating whether the mouse is currently pressed.
        - _drag_pos (Optional[QtCore.QPoint]): The position of the mouse during a drag operation.

    Sets the graphics scene, canvas, transformation anchor, and resize anchor for the CustomGraphicView.

    """

    def __init__(self,
                 parent: QtWidgets = None,
                 figure: matplotlib.figure.Figure = None,
                 title: str = 'Viewer') -> None:
        super(CustomGraphicView, self).__init__(parent)
        self._title = title

        self._figure = figure
        self._canvas = FigCanvas(self._figure)
        self._scene = QtWidgets.QGraphicsScene()

        self._zoom = 0
        self._mousePressed = False
        self._drag_pos = None

        self.save_model_action = QtWidgets.QAction(QtGui.QIcon(':/icons/resources/icons/file_save.svg'),
                                                   'Save model as ...', self)
        self.save_fragment_action = QtWidgets.QAction(QtGui.QIcon(':/icons/resources/icons/save_part.svg'),
                                                      'Save fragment as ...', self)

        self.init_gui()

    def init_gui(self):
        # Set title
        self.setWindowTitle(self._title)

        # Scene settings
        self._scene.addWidget(self._canvas)
        self.setScene(self._scene)

        # Anchor settings
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        # Context menu actions settings
        self.save_model_action.setIconVisibleInMenu(True)
        # noinspection PyUnresolvedReferences
        self.save_model_action.triggered.connect(self.save_model)

        self.save_fragment_action.setIconVisibleInMenu(True)
        # noinspection PyUnresolvedReferences
        self.save_fragment_action.triggered.connect(self.save_fragment)

    def set_figure(self, figure):
        self._figure = figure
        self._canvas = FigCanvas(self._figure)
        self._scene = QtWidgets.QGraphicsScene()
        self._scene.addWidget(self._canvas)
        self.setScene(self._scene)

        # Start viewing position
        self.horizontalScrollBar().setSliderPosition(1)
        self.verticalScrollBar().setSliderPosition(1)

        if self.objectName() not in (
                'resultsView',
        ):
            self.setStyleSheet('QGraphicsView {background-color: transparent;}')

        # self.zoom_initialize()

    # Need if fig dpi > default
    # def zoom_initialize(self) -> None:
    #     fig_size_x_inches, fig_size_y_inches = self._figure.get_size_inches()
    #     start_scale = int(min((self.width() / fig_size_x_inches, self.height() / fig_size_y_inches))) * 0.9
    #     self.scale(1 / start_scale, 1 / start_scale)

    def mousePressEvent(self, event: QtCore.Qt.MouseButton.LeftButton) -> None:
        """Handle the mouse press event.

        Args:
            event (QtCore.Qt.MouseButton.LeftButton): The mouse press event.

        """
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._mousePressed = True
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
            self._drag_pos = event.pos()
            event.accept()

        else:
            super(CustomGraphicView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event: QtCore.Qt.MouseButton.LeftButton) -> None:
        """Handle the mouse move event.

        Args:
            event (QtCore.Qt.MouseButton.LeftButton): The mouse move event.


        This function is called when the mouse is moved while the left button is pressed.
        It calculates the difference between the current mouse position and the previous
        mouse position and updates the scrollbars accordingly.

        """
        if self._mousePressed:
            new_pos = event.pos()
            diff = new_pos - self._drag_pos
            self._drag_pos = new_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))

        else:
            super(CustomGraphicView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtCore.Qt.MouseButton.LeftButton) -> None:
        """Handle the mouse release event.

        Args:
            event (QtCore.Qt.MouseButton.LeftButton): The mouse release event.

        This function is called when the mouse button is released. It checks if the released
        button is the left button. If it is, it sets the '_mousePressed' flag to 'False' and
        changes the cursor to an arrow cursor. Finally, it calls the 'mouseReleaseEvent' method
        of the parent class with the given event.

        """
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._mousePressed = False
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))

        super(CustomGraphicView, self).mouseReleaseEvent(event)

    def wheelEvent(self, event: QtCore.Qt.KeyboardModifier.ControlModifier) -> None:
        """Handle the wheel event.

        Args:
            event (QtCore.Qt.KeyboardModifier.ControlModifier): The wheel event.

        This function is called when the user scrolls the mouse wheel. It checks if the Control
        modifier key is pressed and adjusts the zoom level accordingly. If the zoom level is
        greater than 0, it scales the view by a factor of 1.25 or 0.8 depending on the scroll
        direction. If the zoom level is 0, it resets the view transformation. If the Control
        modifier key is not pressed, it calls the parent class's wheelEvent method with the
        given event.

        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:

            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1

            if self._zoom > -1:
                self.scale(factor, factor)
            else:
                self._zoom = 0
                # self.resetTransform()

            # Alternative variant
            # angle = event.angleDelta().y()
            # factor = 1 + (angle / 1000)
            # self.scale(factor, factor)

        else:
            super(CustomGraphicView, self).wheelEvent(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """Handle the context menu event.

        Args:
            event (QtGui.QContextMenuEvent): The context menu event.

        This function is called when a context menu event is triggered. It creates a context menu
        with actions to save model and save fragment. It then executes the menu at the global position
        specified by the event.

        """
        # Creating context menu
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.save_model_action)

        # Creating / adding separator
        separator = QtWidgets.QAction(self)
        separator.setSeparator(True)
        menu.addAction(separator)

        menu.addAction(self.save_fragment_action)
        menu.exec(event.globalPos())

    def save_model(self):
        """Saves the current figure as an any graphical file."""
        if self.parent() is None:
            NavToolbar.save_figure(self._figure)
        else:
            viewers = self.parent().findChildren(QtWidgets.QGraphicsView)
            for viewer in viewers:
                if viewer == self:
                    # noinspection PyUnresolvedReferences
                    # noinspection PyProtectedMember
                    NavToolbar.save_figure(viewer._figure)

    def save_fragment(self):
        """Saves the current visible area widget as an image.

        Note:
            Saves the current visible area as an image without the scrollbars.

        """
        rect_region = QtCore.QRect(0, 0,
                                   self.width() - self.verticalScrollBar().width(),
                                   self.height() - self.horizontalScrollBar().height())
        pixmap = self.grab(rect_region)
        fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Save fragment as ...', 'image.png',
                                                      'Portable Network Graphics (*.png);;'
                                                      'Joint Photographic Experts Group (*.jpeg *.jpg)')[0]
        if fname:
            pixmap.save(fname)


class QPlainTextEditLogger(QtWidgets.QPlainTextEdit, logging.Handler):
    append_plain_text = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super(QPlainTextEditLogger, self).__init__(parent)
        self.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)

        if "DEBUG" in msg or "INFO" in msg:
            msg = f"""<span style='color:#000000;'>{msg}</span>"""
        elif "WARNING" in msg:
            msg = f"""<span style='color:#ffffff;'>{msg}</span>"""
        elif "ERROR" in msg or "CRITICAL" in msg:
            msg = f"""<span style='color:#ff0000;'>{msg}</span>"""

        self.append_plain_text.emit(self.appendHtml(msg))


class ConfirmWindow(QtWidgets.QDialog):
    """Initializes a ConfirmWindow object."""

    def __init__(self, parent=None):
        super(ConfirmWindow, self).__init__(parent)
        uic.loadUi(GUI_DIR / 'confirm.ui', self)
        # noinspection PyUnresolvedReferences
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)


class CustomWindow:
    def __init__(self):
        super().__init__()

    def window_center_position(self: GW,
                               shift_x: int = 0,
                               shift_y: int = 0,
                               relative: ty.Tuple[int, int] = None) -> None:
        """Centers the window on the screen.

        Args:
            shift_x (int, optional): The shift on the X axis in percentage. Defaults to 0.
            shift_y (int, optional): The shift on the Y axis in percentage. Defaults to 0.
            relative (ty.Tuple[int], optional): Relative position of one window relative to another.

        """
        desktop = QtWidgets.QDesktopWidget().screenGeometry()
        screen_width = desktop.width()
        screen_height = desktop.height()
        x = int((screen_width - self.width()) / 2)
        y = int((screen_height - self.height()) / 2)
        if not relative:
            self.move(
                int(x + self.width() * shift_x / 100),
                int(y - self.height() * shift_y / 100)
            )
        else:
            self.move(
                int(relative[0] + self.width() * shift_x / 100),
                int(relative[1] - self.height() * shift_y / 100)
            )


##################
# Custom threads #
##################

class GraphicsDataThread(QtCore.QThread):
    save_data = QtCore.pyqtSignal(object)
    read_data = QtCore.pyqtSignal(object)
    load_complete = QtCore.pyqtSignal(str)
    load_failure = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, outer_fn=None, inner_fn=None, *args):
        super(GraphicsDataThread, self).__init__(parent)
        self.outer_fn = outer_fn
        self.inner_fn = inner_fn
        self.args = (*args,)

    def run(self):
        try:
            if self.inner_fn:
                data = self.outer_fn(self.inner_fn(*self.args))
            else:
                data = self.outer_fn(*self.args)

            only_fig = data.fig

            self.save_data.emit(data)
            self.read_data.emit(only_fig)
            self.load_complete.emit(
                f"Graphics '{self.outer_fn.LOGS_NAME}' successfully loaded."
            )

        except (Exception,):
            self.load_failure.emit(
                f"Problems with graphics initialization. '{self.outer_fn.LOGS_NAME}' not loaded."
            )


class TableDataThread(QtCore.QThread):
    load_data = QtCore.pyqtSignal(object)
    load_complete = QtCore.pyqtSignal(str)
    load_failure = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, table=None):
        super(TableDataThread, self).__init__(parent)
        self.table = table

    def run(self):
        try:
            if 'JoinedMixin' in map(lambda x: x.__name__, self.table.__mro__):
                data = self.table.show_table(self.table.read_joined_table())
            else:
                data = self.table.show_table(self.table.read_table())

            self.load_data.emit(data)
            self.load_complete.emit(
                f"Table '{self.table.__tablename__}' successfully loaded."
            )

        except (Exception,):
            self.load_failure.emit(
                f"Problems with table '{self.table.__tablename__}'. Try to reinstall database."
            )


####################
# App main windows #
####################

class MainWindow(QtWidgets.QMainWindow, CustomWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi(GUI_DIR / 'main_window.ui', self)

        # Saved instances
        self.results_figure = None
        self.db_browser = None

        self.init_gui()

    def init_gui(self):
        #########################
        # Logger frame settings #
        #########################

        self.logsOutput.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
        logging.getLogger().addHandler(self.logsOutput)
        logging.getLogger().setLevel(logging.INFO)

        ###########################
        # Initial start interface #
        ###########################
        self.switchButton.setChecked(True)
        self.logsButton.setChecked(False)

        # Hiding tab bar for QTabWidget
        self.findChild(QtWidgets.QTabBar).hide()

        # Set window position in the center of the screen
        self.window_center_position()

        ###########################
        # Main bar buttons config #
        ###########################

        self.switchButton.setToolTip('Switch side panel view')

        self.dbmanagerButton.setToolTip('Open database manage client in separate window')
        self.dbmanagerButton.clicked.connect(self.open_db_browser)

        #############################
        # Side panel buttons config #
        #############################

        self.inputButton.setToolTip('Show input console')
        self.inputButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(0))

        self.resultButton.setToolTip('Show calculation results')
        self.resultButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(1))

        self.catalogButton.setToolTip('Show electrical catalog')
        self.catalogButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(2))

        self.logsButton.setToolTip('Show logs terminal')

        self.settingsButton.setToolTip('Show settings')
        self.settingsButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(3))

        self.infoButton.setToolTip('Show info')
        self.infoButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(4))

        ######################
        # Input tab settings #
        ######################

        self.consoleInput.installEventFilter(self)

        #######################
        # Result tab settings #
        #######################

        pass

        ########################
        # Catalog tab settings #
        ########################

        self.set_catalog()

        ###########################
        # "Settings" tab settings #
        ###########################

        BoxParams = namedtuple('BoxParams', ('editable', 'values', 'default', 'update'))

        box_config = {

            # Database settings
            self.settingsBox: BoxParams(
                True, [config_manager('SQLITE_DB_NAME')], config_manager('SQLITE_DB_NAME'),
                lambda x: config_manager('SQLITE_DB_NAME', x)
            ),

            self.settingsBox2: BoxParams(
                False, [False, 'MySQL', 'SQLite'], config_manager('DB_EXISTING_CONNECTION'),
                lambda x: config_manager('DB_EXISTING_CONNECTION', x)
            ),

            self.settingsBox3: BoxParams(
                False, [True, False], config_manager('DB_TABLES_CLEAR_INSTALL'),
                lambda x: config_manager('DB_TABLES_CLEAR_INSTALL', x)
            ),

            self.settingsBox4: BoxParams(
                False, [True, False], config_manager('ENGINE_ECHO'),
                lambda x: config_manager('ENGINE_ECHO', x)
            ),

            # Calculations settings
            self.settingsBox5: BoxParams(
                False, [3, 1], config_manager('SYSTEM_PHASES'),
                lambda x: config_manager('SYSTEM_PHASES', x)
            ),

            self.settingsBox6: BoxParams(
                False, [Decimal('0.4')], config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS'),
                lambda x: config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS', x)
            ),

            self.settingsBox7: BoxParams(
                True, [config_manager('CALCULATIONS_ACCURACY')], config_manager('CALCULATIONS_ACCURACY'),
                lambda x: config_manager('CALCULATIONS_ACCURACY', x)
            )
        }

        for box in box_config:
            # Creating combo box options list
            default = box_config[box].default
            others = box_config[box].values
            others.remove(default)
            default = [default]
            default.extend(others)
            for i in range(len(default)):
                default[i] = str(default[i])

            # Creating GUI for combo box options list
            box.addItems(default)
            box.setEditable(True)
            line_edit = box.lineEdit()
            line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            line_edit.setReadOnly(not box_config[box].editable)
            if box_config[box].editable:
                box.setStyleSheet('font: italic bold 11pt')
            else:
                box.setStyleSheet('font: italic bold 11pt; background-color: lightgray')

        # Actions if combo boxes changed
        self.settingsBox.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox].update(self.settingsBox.currentText())
        )
        self.settingsBox2.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox2].update(self.settingsBox2.currentText())
        )
        self.settingsBox3.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox3].update(self.settingsBox3.currentText())
        )
        self.settingsBox4.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox4].update(self.settingsBox4.currentText())
        )
        self.settingsBox5.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox5].update(self.settingsBox5.currentText())
        )
        self.settingsBox6.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox6].update(self.settingsBox6.currentText())
        )
        self.settingsBox7.currentIndexChanged.connect(
            lambda: box_config[self.settingsBox7].update(self.settingsBox7.currentText())
        )

    def set_catalog(self):
        catalog_thread = GraphicsDataThread(self, CatalogFigure)

        catalog_thread.read_data.connect(self.catalogView.set_figure)
        catalog_thread.load_complete.connect(logger.info)
        catalog_thread.load_failure.connect(logger.error)

        catalog_thread.start()

    def open_db_browser(self):
        if self.db_browser is None:
            self.db_browser = DatabaseBrowser()
            self.db_browser.window_center_position(
                shift_x=5, shift_y=-5, relative=(self.x(), self.y())
            )
        self.db_browser.show()

    def save_interactive_stmt(self, figure_obj):
        self.results_figure = figure_obj

    # noinspection PyUnresolvedReferences
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress and obj is self.consoleInput:
            if event.modifiers() == QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_Return:
                text = self.consoleInput.toPlainText()
                results_thread = GraphicsDataThread(
                    self, ResultsFigure, ChainsSystem, text
                )

                results_thread.save_data.connect(self.save_interactive_stmt)
                results_thread.read_data.connect(self.resultsView.set_figure)
                results_thread.load_complete.connect(logger.info)
                results_thread.load_failure.connect(logger.error)

                results_thread.start()

        return super().eventFilter(obj, event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle the close event of the window.

        Args:
            event (QtGui.QCloseEvent): The close event object.

        This function is called when the user tries to close the window. It creates a confirmation window
        and displays it to the user. If the user confirms the close action, the event is accepted and the
        window is closed. Otherwise, the event is ignored and the window remains open.

        """
        app = QtWidgets.QApplication.instance()
        confirm_window = ConfirmWindow(self)
        confirm_window.exec_()
        if confirm_window.result() == QtWidgets.QDialog.Accepted:
            event.accept()
            # noinspection PyUnresolvedReferences
            for window in app.topLevelWidgets():
                window.close()
        else:
            event.ignore()


class DatabaseBrowser(QtWidgets.QWidget, CustomWindow):
    def __init__(self):
        super(DatabaseBrowser, self).__init__()
        uic.loadUi(GUI_DIR / 'db_browser.ui', self)

        self.init_gui()
        self.main_menu = next(widget for widget in QtWidgets.QApplication.topLevelWidgets()
                              if isinstance(widget, MainWindow))
        self.show_database()
        self.crud_operations()

    def init_gui(self):
        ###########################
        # Initial start interface #
        ###########################
        self.viewerWidget.setCurrentIndex(0)
        self.optionsWidget.setCurrentIndex(0)
        self.manageButton.setChecked(True)

        # Set DB name and logo
        db_key = config_manager('DB_EXISTING_CONNECTION')

        names = {
            'MySQL': 'MySQL Browser',
            'SQLite': 'SQLite Browser',
            False: 'Database Browser'
        }

        logos = {
            'MySQL': QtGui.QPixmap(':/logos/resources/logos/db_mysql_rectangle.svg'),
            'SQLite': QtGui.QPixmap(':/logos/resources/logos/db_sqlite_rectangle.svg'),
            False: QtGui.QPixmap(':/logos/resources/logos/db_no_connections.svg')
        }

        self.setWindowTitle(names[db_key])
        self.iconLabel.setPixmap(logos[db_key])
        self.iconLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        #############################
        # Main keys actions binding #
        #############################
        self.installButton.clicked.connect(self.reinstall_database)

    def show_database(self):
        tables = Transformer, Cable, CurrentBreaker, OtherContact
        views = self.transformersView, self.cablesView, self.contactsView, self.resistancesView

        threads = []

        for table, view in zip(tables, views):
            table_data_thread = TableDataThread(self, table)

            table_data_thread.load_data.connect(view.set_figure)
            table_data_thread.load_complete.connect(logger.info)
            table_data_thread.load_failure.connect(logger.error)

            threads.append(table_data_thread)
            table_data_thread.start()

    def reinstall_database(self):
        confirm_window = ConfirmWindow(self)
        confirm_window.exec_()

        if confirm_window.result() == QtWidgets.QDialog.Accepted:
            db_install(clear=config_manager('DB_TABLES_CLEAR_INSTALL'))
            self.show_database()
            self.main_menu.set_catalog()

    def crud_operations(self):
        ##############################
        # Insert operations settings #
        ##############################
        self.insertButton.clicked.connect(lambda: self.crud_event(self.get_insert_tools))

        ##############################
        # Update operations settings #
        ##############################
        self.updateButton.clicked.connect(lambda: self.crud_event(self.get_update_tools))

        ##############################
        # Delete operations settings #
        ##############################
        self.rowButton.clicked.connect(lambda: self.crud_event(self.get_delete_tools, False))
        self.sourceButton.clicked.connect(lambda: self.crud_event(self.get_delete_tools, True))

    @logging_error
    def crud_event(self, get_tools, *args, **kwargs) -> None:
        tools = get_tools()
        tools.operation(*args, **kwargs)

        if 'JoinedMixin' in map(lambda x: x.__name__, tools.table.__mro__):
            tools.view.set_figure(
                tools.table.show_table(tools.table.read_joined_table())
            )
        else:
            tools.view.set_figure(
                tools.table.show_table(tools.table.read_table())
            )

        self.main_menu.set_catalog()

    def get_insert_tools(self):
        InsertTuple = namedtuple('InsertTuple', ('table', 'view', 'operation'))

        insert_operations = {
            'insertTransPage': InsertTuple(
                Transformer, self.transformersView, lambda: Transformer.insert_joined_table(
                    data=[
                        asdict(
                            InsertTrans(
                                self.insertTransEdit.text(),
                                self.insertTransEdit2.text(),
                                self.insertTransEdit3.text(),
                                self.insertTransEdit4.text(),
                                self.insertTransEdit5.text(),
                                self.insertTransEdit6.text(),
                                self.insertTransEdit7.text(),
                                self.insertTransEdit8.text(),
                                self.insertTransEdit9.text()
                            )
                        )
                    ]
                )
            ),

            'insertCablePage': InsertTuple(
                Cable, self.cablesView, lambda: Cable.insert_joined_table(
                    data=[
                        asdict(
                            InsertCable(
                                self.insertCableEdit.text(),
                                self.insertCableEdit2.text(),
                                self.insertCableEdit3.text(),
                                self.insertCableEdit4.text(),
                                self.insertCableEdit5.text(),
                                self.insertCableEdit6.text(),
                                self.insertCableEdit7.text(),
                                self.insertCableEdit8.text()
                            )
                        )
                    ]
                )
            ),

            'insertContactPage': InsertTuple(
                CurrentBreaker, self.contactsView, lambda: CurrentBreaker.insert_joined_table(
                    data=[
                        asdict(
                            InsertContact(
                                self.insertContactEdit.text(),
                                self.insertContactEdit2.text(),
                                self.insertContactEdit3.text(),
                                self.insertContactEdit4.text(),
                                self.insertContactEdit5.text(),
                                self.insertContactEdit6.text()
                            )
                        )
                    ]
                )
            ),

            'insertResistPage': InsertTuple(
                OtherContact, self.resistancesView, lambda: OtherContact.insert_table(
                    data=[
                        asdict(
                            InsertResist(
                                self.insertResistEdit.text(),
                                self.insertResistEdit2.text(),
                                self.insertResistEdit3.text(),
                                self.insertResistEdit4.text(),
                                self.insertResistEdit5.text()
                            )
                        )
                    ]
                )
            )
        }

        return insert_operations[self.insertWidget.currentWidget().objectName()]

    def get_update_tools(self):
        UpdateTuple = namedtuple('UpdateTuple', ('table', 'view', 'operation'))

        update_operations = {
            'updateTransPage': UpdateTuple(
                Transformer, self.transformersView, lambda: Transformer.update_joined_table(
                    old_source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateTransOldSource(
                            self.updateTransEdit.text(),
                            self.updateTransEdit2.text(),
                            self.updateTransEdit3.text()
                        )
                    ),
                    new_source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateTransNewSource(
                            self.updateTransEdit4.text(),
                            self.updateTransEdit5.text(),
                            self.updateTransEdit6.text()
                        )
                    ),
                    target_row_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateTransRow(
                            self.updateTransEdit7.text(),
                            self.updateTransEdit8.text(),
                            self.updateTransEdit9.text(),
                            self.updateTransEdit10.text(),
                            self.updateTransEdit11.text(),
                            self.updateTransEdit12.text()
                        )
                    )
                )
            ),

            'updateCablePage': UpdateTuple(
                Cable, self.cablesView, lambda: Cable.update_joined_table(
                    old_source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateCableOldSource(
                            self.updateCableEdit.text(),
                            self.updateCableEdit2.text(),
                            self.updateCableEdit3.text()
                        )
                    ),
                    new_source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateCableNewSource(
                            self.updateCableEdit4.text(),
                            self.updateCableEdit5.text(),
                            self.updateCableEdit6.text()
                        )
                    ),
                    target_row_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateCableRow(
                            self.updateCableEdit7.text(),
                            self.updateCableEdit8.text(),
                            self.updateCableEdit9.text(),
                            self.updateCableEdit10.text(),
                            self.updateCableEdit11.text()
                        )
                    )
                )
            ),

            'updateContactPage': UpdateTuple(
                CurrentBreaker, self.contactsView, lambda: CurrentBreaker.update_joined_table(
                    old_source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateContactOldSource(
                            self.updateContactEdit.text(),
                            self.updateContactEdit2.text()
                        )
                    ),
                    new_source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateContactNewSource(
                            self.updateContactEdit3.text(),
                            self.updateContactEdit4.text()
                        )
                    ),
                    target_row_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=UpdateContactRow(
                            self.updateContactEdit5.text(),
                            self.updateContactEdit6.text(),
                            self.updateContactEdit7.text(),
                            self.updateContactEdit8.text()
                        )
                    )
                )
            ),

            'updateResistPage': UpdateTuple(
                OtherContact, self.resistancesView, lambda: OtherContact.update_table(
                    {
                        **asdict(
                            dict_factory=self.__dict_factory,
                            obj=UpdateResistNewSource(
                                self.updateResistEdit2.text()
                            )
                        ),
                        **asdict(
                            dict_factory=self.__dict_factory,
                            obj=UpdateResistRow(
                                self.updateResistEdit3.text(),
                                self.updateResistEdit4.text(),
                                self.updateResistEdit5.text(),
                                self.updateResistEdit6.text()
                            )
                        )
                    },
                    options='where_condition',
                    attr='contact_type',
                    criteria=(
                        asdict(
                            dict_factory=self.__dict_factory,
                            obj=UpdateResistOldSource(
                                self.updateResistEdit.text()
                            )
                        )['contact_type'],
                    )
                )
            )
        }

        return update_operations[self.updateWidget.currentWidget().objectName()]

    def get_delete_tools(self):
        DeleteTuple = namedtuple('DeleteTuple', ('table', 'view', 'operation'))

        delete_operations = {
            'deleteTransPage': DeleteTuple(
                Transformer, self.transformersView, lambda x: Transformer.delete_joined_table(
                    from_source=x,
                    source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=DeleteTrans(
                            self.deleteTransEdit.text(),
                            self.deleteTransEdit2.text(),
                            self.deleteTransEdit3.text()
                        )
                    )
                )
            ),

            'deleteCablePage': DeleteTuple(
                Cable, self.cablesView, lambda x: Cable.delete_joined_table(
                    from_source=x,
                    source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=DeleteCable(
                            self.deleteCableEdit.text(),
                            self.deleteCableEdit2.text(),
                            self.deleteCableEdit3.text()
                        )
                    )
                )
            ),

            'deleteContactPage': DeleteTuple(
                CurrentBreaker, self.contactsView, lambda x: CurrentBreaker.delete_joined_table(
                    from_source=x,
                    source_data=asdict(
                        dict_factory=self.__dict_factory,
                        obj=DeleteContact(
                            self.deleteContactEdit.text(),
                            self.deleteContactEdit2.text()
                        )
                    )
                )
            ),
            'deleteResistPage': DeleteTuple(
                OtherContact, self.resistancesView, lambda x: OtherContact.delete_table(
                    filtrate=next(
                        map(
                            lambda pair: f"{pair[0]} = '{pair[1]}'",
                            tuple(
                                asdict(
                                    dict_factory=self.__dict_factory,
                                    obj=DeleteResist(
                                        self.deleteResistEdit.text()
                                    )
                                ).items()
                            )
                        )
                    )
                )
            )
        }

        return delete_operations[self.deleteWidget.currentWidget().objectName()]

    @property
    def __dict_factory(self):
        return lambda x: {k: v for (k, v) in x if v is not None}


########################
# Others functionality #
########################

# class ViewerWidget(QtWidgets.QWidget):
#     """Initializes a ViewerWidget object.
#
#     ViewerWidget is a QWidget that displays a matplotlib figure in a QGraphicsView widget.
#     Also allows saving the figure as any graphical format or saving part of the figure as an image.
#
#     Args:
#         title (str): The title of the viewer widget.
#
#     """
#
#     def __init__(self, title: str = 'Viewer Window') -> None:
#         super(ViewerWidget, self).__init__()
#         # self._figure definition before loadUi is necessarily!
#         uic.loadUi(GUI_DIR / 'viewer.ui', self)
#         self.setWindowTitle(title)
#
#         self.allButton.setToolTip('Save whole page')
#         self.allButton.clicked.connect(self.save_model)
#
#         self.partButton.setToolTip('Save part of page')
#         self.partButton.clicked.connect(self.save_fragment)
