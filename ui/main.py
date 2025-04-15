import subprocess
import traceback
import logging
import sys

from __main__ import __version__
from core.project import Project
from core.models import Node
from ui.graph import EstimateGraph, GraphWidget, PaybackGraph
from ui.matrix import MatrixWidget
from ui.nodeedge import NodeEdgeWidget
from ui.widgets import InputForm, SimulationBreakdown, TabWidget, AirportCharges, HLayout
from ui.logging import initialize_logger
from ui.dialogs import NotificationDialog
from PyQt5.QtGui import QIcon, QKeySequence, QCursor
from PyQt5.QtCore import QObject, pyqtSignal, QSettings, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QShortcut, QSplitter, QAction, QStyle, QApplication, QMenuBar
from pathlib import Path

logger = logging.getLogger(__name__)

# TODO: Square icon


class Signals(QObject):

    lists_about_to_change = pyqtSignal()
    lists_changed = pyqtSignal()

    node_about_to_be_added = pyqtSignal()
    node_coordinate_selected = pyqtSignal(tuple)
    node_added = pyqtSignal(tuple, Node)

    node_about_to_be_removed = pyqtSignal(str)
    node_removed = pyqtSignal(str)

    node_order_about_to_change = pyqtSignal(int, int)
    node_order_changed = pyqtSignal()

    parent_order_about_to_change = pyqtSignal(int, int)
    parent_order_changed = pyqtSignal()

    name_about_to_change = pyqtSignal(str, str)
    name_changed = pyqtSignal()

    dist_about_to_change = pyqtSignal(str, str)
    dist_changed = pyqtSignal()

    dist_param_small_about_to_change = pyqtSignal(str, str)
    dist_param_small_changed = pyqtSignal()

    dist_param_large_about_to_change = pyqtSignal(str, str)
    dist_param_large_changed = pyqtSignal()

    cond_val_about_to_change = pyqtSignal(str, str)
    cond_val_changed = pyqtSignal()

    edge_about_to_be_added = pyqtSignal()
    edge_nodes_selected = pyqtSignal(object)
    edge_added = pyqtSignal(str, str)

    edge_about_to_be_removed = pyqtSignal(str, str)
    edge_removed = pyqtSignal(str, str)

    edge_about_to_be_reversed = pyqtSignal(str, str)
    edge_reversed = pyqtSignal(str, str)

    observed_correlation_about_to_change = pyqtSignal(str, str, str)
    correlation_about_to_change = pyqtSignal(str, str, str)
    correlation_changed = pyqtSignal()

    simdata_about_to_be_updated = pyqtSignal(object)
    sim_data_updated = pyqtSignal()

    on_click_delete_about_to_happen = pyqtSignal()
    stop_running_click_threads = pyqtSignal()

    set_graph_message = pyqtSignal(str)

    font_changed = pyqtSignal()

    set_window_modified = pyqtSignal(bool)

    selected = pyqtSignal(object)
    nodeview_row_changed = pyqtSignal(str, str)
    edgeview_row_changed = pyqtSignal(tuple, tuple)

    airportcharges_about_to_change = pyqtSignal(object)
    airportcharges_changed = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.mainwindow = parent

    def connect(self) -> None:

        # Change edge labels
        self.edge_added.connect(self.mainwindow.graph_widget.change_edge_labels)
        self.node_removed.connect(self.mainwindow.graph_widget.change_edge_labels)
        self.edge_removed.connect(self.mainwindow.graph_widget.change_edge_labels)
        self.edge_reversed.connect(self.mainwindow.graph_widget.change_edge_labels)
        self.node_order_changed.connect(self.mainwindow.graph_widget.change_edge_labels)
        self.parent_order_changed.connect(self.mainwindow.graph_widget.change_edge_labels)



        # Connect window modified signals here
        # Connect node related
        self.node_added.connect(lambda: self.set_window_modified.emit(True))
        self.node_removed.connect(lambda: self.set_window_modified.emit(True))
        self.name_changed.connect(lambda: self.set_window_modified.emit(True))
        self.dist_changed.connect(lambda: self.set_window_modified.emit(True))
        self.dist_param_small_changed.connect(lambda: self.set_window_modified.emit(True))
        self.dist_param_large_changed.connect(lambda: self.set_window_modified.emit(True))
        self.cond_val_changed.connect(lambda: self.set_window_modified.emit(True))
        self.node_order_changed.connect(lambda: self.set_window_modified.emit(True))
        self.sim_data_updated.connect(lambda: self.set_window_modified.emit(True))



        # Connect edge related
        self.edge_added.connect(lambda: self.set_window_modified.emit(True))
        self.edge_removed.connect(lambda: self.set_window_modified.emit(True))
        self.edge_reversed.connect(lambda: self.set_window_modified.emit(True))
        self.correlation_changed.connect(lambda: self.set_window_modified.emit(True))
        self.parent_order_changed.connect(lambda: self.set_window_modified.emit(True))


        # Connect print signals
        self.selected.connect(lambda s: logger.info(f"Clicked {'edge' if isinstance(s, tuple) == 1 else 'node'} {s}."))

class MainWindow(QMainWindow):
    """
    Main UI widget of Anduryl.
    """

    def __init__(self, app):
        """
        Constructer. Adds project and sets general settings.
        """
        super().__init__()

        self.app = app

        self.appsettings = QSettings("DAiCE")

        self.setAcceptDrops(True)

        self.setWindowTitle("DAiCE")

        initialize_logger(console=True)

        self.profiling = False

        self.data_path = self.get_data_path()

        self.icon = QIcon(str(self.data_path / "icon.png"))
        self.setWindowIcon(self.icon)

        # Add signals
        self.signals = Signals(self)
        self.signals.set_window_modified.connect(self.setWindowModified)

        # Add keyboard shortcuts
        self.shortcut_add_node = QShortcut(QKeySequence("Ctrl+1"), self)
        self.shortcut_add_node.activated.connect(self.signals.node_about_to_be_added)

        self.shortcut_add_edge = QShortcut(QKeySequence("Ctrl+2"), self)
        self.shortcut_add_edge.activated.connect(self.signals.edge_about_to_be_added)

        # Add project
        self.project = Project(self)
        self.update_projectname()


        self.setCursor(Qt.ArrowCursor)

        self.bordercolor = "lightgrey"

        self.secondwindow = None
        self.thirdwindow = None


        # Construct user interface
        self.init_ui()
        self.signals.connect()

        # Keep track of font size increment, for opening new windows
        self.font_increment = 0

        def test_exception_hook(exctype, value, tback):
            """
            Function that catches errors and gives a Notification
            instead of a crashing application.
            """
            sys.__excepthook__(exctype, value, tback)
            self.setCursorNormal()
            NotificationDialog(
                text="\n".join(traceback.format_exception_only(exctype, value)),
                severity="critical",
                details="\n".join(traceback.format_tb(tback)),
            )

        sys.excepthook = test_exception_hook

    def get_data_path(self) -> Path:
        # In case of PyInstaller exe
        if getattr(sys, "frozen", False):
            application_path = Path(sys._MEIPASS)
            data_path = application_path / "data"

        # In case of regular python
        else:
            application_path = Path(__file__).resolve().parent
            data_path = application_path / ".." / "data"

        return data_path

    def setCursorNormal(self):
        """
        Changes cursor (back) to normal cursor.
        """
        QApplication.restoreOverrideCursor()

    def setCursorWait(self):
        """
        Changes cursor to waiting cursor.
        """
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def init_ui(self):
        """
        Construct UI, by splitting the main window and adding the
        different widgets with tables.
        """
        mainsplitter = QSplitter(Qt.Horizontal)

        self.setCentralWidget(mainsplitter)

        # InputForm
        self.input_form = InputForm(self)

        # GraphWidget
        self.graph_widget = GraphWidget(self)

        # MatrixWidget
        self.matrix_widget = MatrixWidget(self)

        # EstimateGraph
        self.cost_widget = EstimateGraph(self)

        # Buttons for element/cost breakdown
        self.variables_widget = SimulationBreakdown(self)

        # Lists of Nodes and Edges
        self.nodes_edges_widget = NodeEdgeWidget(self)

        rightsplitter = TabWidget(
            [self.cost_widget, self.variables_widget], "Financial Information", ["Simulated Cost", "Simulation Breakdown"]
        )
        # self.rightsplitter.setSizes([200, 200])

        mainsplitter.addWidget(self.input_form)
        mainsplitter.addWidget(rightsplitter)
        mainsplitter.setSizes([500, 500])

        self.init_menubar()

        mainsplitter.setStyleSheet("QSplitter::handle{background:white}")
        rightsplitter.setStyleSheet("QSplitter::handle{background:white}")

        self.setGeometry(0, 0, 1200, 650)

        self.show()

    def change_font_size(self, increment):

        self.nodes_edges_widget.nodemodel.layoutAboutToBeChanged.emit()
        self.nodes_edges_widget.edgemodel.layoutAboutToBeChanged.emit()

        sizes = []
        for w in self.app.allWidgets():
            font = w.font()
            size = font.pointSize() + increment
            font.setPointSize(max(1, size))
            sizes.append(size)
            w.setFont(font)

        # Keep track of font increment for opening new windows in the right scale
        # Only if the smallest item has a >= 1 size, the increment is added, to prevent the value getting out of bounds
        if min(sizes) >= 1:
            self.font_increment += increment

        self.signals.font_changed.emit()

        self.nodes_edges_widget.nodemodel.layoutChanged.emit()
        self.nodes_edges_widget.edgemodel.layoutChanged.emit()

    def update_projectname(self, name=None):
        """
        Updates window title after a project has been loaded

        Parameters
        ----------
        name : str, optional
            Project name, by default None
        """
        if name is None:
            self.setWindowTitle("DAiCE [*]")
            self.appsettings.setValue("currentproject", "")
        else:
            self.setWindowTitle(f"DAiCE - {name} [*]")
            self.appsettings.setValue("currentproject", name)

    def init_menubar(self):
        """
        Constructs the menu bar.
        """

        menubar = self.menuBar()

        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.setStatusTip("Create a new project")
        new_action.triggered.connect(self.project.new)

        openAction = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "Open", self)
        openAction.setStatusTip("Open project")
        openAction.setShortcut(QKeySequence.Open)
        openAction.triggered.connect(self.project.open)

        saveAction = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        saveAction.setStatusTip("Save project")
        saveAction.setShortcut(QKeySequence.Save)
        saveAction.triggered.connect(self.project.save)

        saveAsAction = QAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save as", self
        )
        saveAsAction.setStatusTip("Save project as...")
        saveAsAction.setShortcut("Ctrl+Shift+S")
        saveAsAction.triggered.connect(self.project.save_as)

        exitAction = QAction(
            self.style().standardIcon(QStyle.SP_TitleBarCloseButton), "Exit", self
        )
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Close DAiCE")
        exitAction.triggered.connect(self.close)

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(new_action)
        file_menu.addAction(openAction)
        file_menu.addSeparator()
        file_menu.addAction(saveAction)
        file_menu.addAction(saveAsAction)
        file_menu.addSeparator()
        file_menu.addAction(exitAction)

        bn_menu = menubar.addMenu("&BN")
        bn_menu.addAction("Edit BN", lambda: self.open_bnwindow(self.graph_widget, self.matrix_widget, self.nodes_edges_widget, self.app))

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Increase UI font", lambda: self.change_font_size(1), QKeySequence("Ctrl+="))
        view_menu.addAction("Decrease UI font", lambda: self.change_font_size(-1), QKeySequence("Ctrl+-"))
        view_menu.addSeparator()

        def _increase_dpi():
            self.graph_widget.increase_dpi(factor=1.2)
            self.matrix_widget.increase_dpi(factor=1.2)

        def _decrease_dpi():
            self.graph_widget.decrease_dpi(factor=1.2)
            self.matrix_widget.decrease_dpi(factor=1.2)

        view_menu.addAction("Increase graph scale", _increase_dpi, QKeySequence("Ctrl+Shift+="))
        view_menu.addAction("Decrease graph scale", _decrease_dpi, QKeySequence("Ctrl+Shift+-"))

        # export_menu = menubar.addMenu("&Export")
        # export_R_menu = export_menu.addMenu("&Correlation Matrix")
        # export_R_menu.addAction("To CSV", lambda: self.project.export("correlation_matrix", "csv"))
        # export_R_menu.addAction("To clipboard", lambda: self.project.export("correlation_matrix", "clipboard"))
        #
        # export_nodes_menu = export_menu.addMenu("&Nodes")
        # export_nodes_menu.addAction("To CSV", lambda: self.project.export("nodes", "csv"))
        # export_nodes_menu.addAction("To clipboard", lambda: self.project.export("nodes", "clipboard"))
        #
        # export_nodes_menu = export_menu.addMenu("&Edges")
        # export_nodes_menu.addAction("To CSV", lambda: self.project.export("edges", "csv"))
        # export_nodes_menu.addAction("To clipboard", lambda: self.project.export("edges", "clipboard"))
        #
        # help_menu = menubar.addMenu("&Help")
        # doc_action = QAction(
        #     self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Documentation", self
        # )
        # doc_action.setStatusTip("Open Anduryl documentation")
        # doc_action.triggered.connect(self.open_documentation)
        # help_menu.addAction(doc_action)
        #
        # about_action = QAction(QIcon(), "Version", self)
        # about_action.triggered.connect(self.open_about)
        # help_menu.addAction(about_action)

        finance_menu = menubar.addMenu("&Finance")
        finance_menu.addAction("View financial details", lambda: self.open_financewindow())

    def open_about(self):
        text = f"Version: {__version__}"
        Qt.QMessageBox.about(self, "DAiCE version", text)

    def open_documentation(self):

        # In case of PyInstaller exe
        if getattr(sys, "frozen", False):
            application_path = Path(sys._MEIPASS)
            indexpath = application_path / "doc" / "index.html"

        # In case of regular python
        else:
            application_path = Path(__file__).resolve().parent
            indexpath = application_path / '..' / '..' / "doc" / 'build' / 'html' / "index.html"

        # Open index html
        subprocess.Popen(str(indexpath), shell=True)

    def open_bnwindow(self, graphwidget, matrixwidget, nodesedges, app):
        if self.secondwindow is None:
            self.secondwindow = BNWindow(self, graphwidget, matrixwidget, nodesedges, app)
        self.secondwindow.show()

    def open_financewindow(self):
        try:
            len(self.input_form.conditions) > 0
        except:
            NotificationDialog(
                text="No cost estimates have been found.",
                severity="critical")
            return
        if self.thirdwindow is None:
            self.thirdwindow = FinanceWindow(self)
        self.thirdwindow.show()

class BNWindow(QWidget):
    """
    Window for viewing and editing the BN
    """
    def __init__(self, mainwindow, graphwidget, matrixwidget, nodesedges, app):
        super().__init__()
        self.mainwindow = mainwindow
        self.project = self.mainwindow.project
        self.app = app

        self.appsettings = QSettings("DAiCE")

        self.setAcceptDrops(True)

        self.setWindowTitle("DAiCE - BN Dashboard")

        self.profiling = False

        self.data_path = self.get_data_path()

        self.icon = QIcon(str(self.data_path / "icon.png"))
        self.setWindowIcon(self.icon)

        self.graph_widget = graphwidget
        self.matrix_widget = matrixwidget
        self.nodes_edges_widget = nodesedges

        # Add signals
        self.signals = Signals(self)
        self.signals.set_window_modified.connect(self.setWindowModified)

        # Add keyboard shortcuts
        self.shortcut_add_node = QShortcut(QKeySequence("Ctrl+1"), self)
        self.shortcut_add_node.activated.connect(self.signals.node_about_to_be_added)

        self.shortcut_add_edge = QShortcut(QKeySequence("Ctrl+2"), self)
        self.shortcut_add_edge.activated.connect(self.signals.edge_about_to_be_added)

        self.setCursor(Qt.ArrowCursor)

        self.bordercolor = "lightgrey"

        self.signals.connect()

        self.menubar = self.init_menubar()
        self.menubar.setFixedHeight(25)

        leftsplitter = TabWidget(
            [self.graph_widget], "Graph"
        )
        rightsplitter = TabWidget(
            [self.matrix_widget, self.nodes_edges_widget], "Data", ["Correlation Matrix", "List of nodes and edges"]
        )

        bnwindow_layout = HLayout([leftsplitter, rightsplitter])
        bnwindow_layout.setMenuBar(self.menubar)

        self.setLayout(bnwindow_layout)
        # self.setGeometry(300, 200, 1200, 650)

        def test_exception_hook(exctype, value, tback):
            """
            Function that catches errors and gives a Notification
            instead of a crashing application.
            """
            sys.__excepthook__(exctype, value, tback)
            self.setCursorNormal()
            NotificationDialog(
                text="\n".join(traceback.format_exception_only(exctype, value)),
                severity="critical",
                details="\n".join(traceback.format_tb(tback)),
            )

        sys.excepthook = test_exception_hook

    def get_data_path(self) -> Path:
        # In case of PyInstaller exe
        if getattr(sys, "frozen", False):
            application_path = Path(sys._MEIPASS)
            data_path = application_path / "data"

        # In case of regular python
        else:
            application_path = Path(__file__).resolve().parent
            data_path = application_path / ".." / "data"

        return data_path

    def setCursorNormal(self):
        """
        Changes cursor (back) to normal cursor.
        """
        QApplication.restoreOverrideCursor()

    def setCursorWait(self):
        """
        Changes cursor to waiting cursor.
        """
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def change_font_size(self, increment):

        self.nodes_edges_widget.nodemodel.layoutAboutToBeChanged.emit()
        self.nodes_edges_widget.edgemodel.layoutAboutToBeChanged.emit()

        sizes = []
        for w in self.app.allWidgets():
            font = w.font()
            size = font.pointSize() + increment
            font.setPointSize(max(1, size))
            sizes.append(size)
            w.setFont(font)

        # Keep track of font increment for opening new windows in the right scale
        # Only if the smallest item has a >= 1 size, the increment is added, to prevent the value getting out of bounds
        if min(sizes) >= 1:
            self.font_increment += increment

        self.signals.font_changed.emit()

        self.nodes_edges_widget.nodemodel.layoutChanged.emit()
        self.nodes_edges_widget.edgemodel.layoutChanged.emit()

    def update_projectname(self, name=None):
        """
        Updates window title after a project has been loaded

        Parameters
        ----------
        name : str, optional
            Project name, by default None
        """
        if name is None:
            self.setWindowTitle("DAiCE [*]")
            self.appsettings.setValue("currentproject", "")
        else:
            self.setWindowTitle(f"DAiCE - {name} [*]")
            self.appsettings.setValue("currentproject", name)

    def open_about(self):
        text = f"Version: {__version__}"
        Qt.QMessageBox.about(self, "DAiCE version", text)

    def open_documentation(self):

        # In case of PyInstaller exe
        if getattr(sys, "frozen", False):
            application_path = Path(sys._MEIPASS)
            indexpath = application_path / "doc" / "index.html"

        # In case of regular python
        else:
            application_path = Path(__file__).resolve().parent
            indexpath = application_path / '..' / '..' / "doc" / 'build' / 'html' / "index.html"

        # Open index html
        subprocess.Popen(str(indexpath), shell=True)

    def init_menubar(self):
        """
        Constructs the menu bar.
        """

        menubar = QMenuBar()

        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.setStatusTip("Create a new project")
        new_action.triggered.connect(self.project.new)

        openAction = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "Open", self)
        openAction.setStatusTip("Open project")
        openAction.setShortcut(QKeySequence.Open)
        openAction.triggered.connect(self.project.open)

        saveAction = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        saveAction.setStatusTip("Save project")
        saveAction.setShortcut(QKeySequence.Save)
        saveAction.triggered.connect(self.project.save)

        saveAsAction = QAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save as", self
        )
        saveAsAction.setStatusTip("Save project as...")
        saveAsAction.setShortcut("Ctrl+Shift+S")
        saveAsAction.triggered.connect(self.project.save_as)

        exitAction = QAction(
            self.style().standardIcon(QStyle.SP_TitleBarCloseButton), "Exit", self
        )
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Close DAiCE")
        exitAction.triggered.connect(self.close)

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(new_action)
        file_menu.addAction(openAction)
        file_menu.addSeparator()
        file_menu.addAction(saveAction)
        file_menu.addAction(saveAsAction)
        file_menu.addSeparator()
        file_menu.addAction(exitAction)

        bn_menu = menubar.addMenu("&BN")
        bn_menu.addAction("Edit BN",
                          lambda: self.open_bnwindow(self.graph_widget, self.matrix_widget, self.nodes_edges_widget,
                                                     self.app))

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Increase UI font", lambda: self.change_font_size(1), QKeySequence("Ctrl+="))
        view_menu.addAction("Decrease UI font", lambda: self.change_font_size(-1), QKeySequence("Ctrl+-"))
        view_menu.addSeparator()

        def _increase_dpi():
            self.graph_widget.increase_dpi(factor=1.2)
            self.matrix_widget.increase_dpi(factor=1.2)

        def _decrease_dpi():
            self.graph_widget.decrease_dpi(factor=1.2)
            self.matrix_widget.decrease_dpi(factor=1.2)

        view_menu.addAction("Increase graph scale", _increase_dpi, QKeySequence("Ctrl+Shift+="))
        view_menu.addAction("Decrease graph scale", _decrease_dpi, QKeySequence("Ctrl+Shift+-"))

        export_menu = menubar.addMenu("&Export")
        export_R_menu = export_menu.addMenu("&Correlation Matrix")
        export_R_menu.addAction("To CSV", lambda: self.project.export("correlation_matrix", "csv"))
        export_R_menu.addAction("To clipboard", lambda: self.project.export("correlation_matrix", "clipboard"))

        export_nodes_menu = export_menu.addMenu("&Nodes")
        export_nodes_menu.addAction("To CSV", lambda: self.project.export("nodes", "csv"))
        export_nodes_menu.addAction("To clipboard", lambda: self.project.export("nodes", "clipboard"))

        export_nodes_menu = export_menu.addMenu("&Edges")
        export_nodes_menu.addAction("To CSV", lambda: self.project.export("edges", "csv"))
        export_nodes_menu.addAction("To clipboard", lambda: self.project.export("edges", "clipboard"))

        help_menu = menubar.addMenu("&Help")
        doc_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Documentation", self
        )
        doc_action.setStatusTip("Open Anduryl documentation")
        doc_action.triggered.connect(self.open_documentation)
        help_menu.addAction(doc_action)

        about_action = QAction(QIcon(), "Version", self)
        about_action.triggered.connect(self.open_about)
        help_menu.addAction(about_action)

        return menubar

class FinanceWindow(QWidget):
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.project = self.mainwindow.project
        self.bn = self.project.bn
        self.app = self.mainwindow.app
        self.input_form = self.mainwindow.input_form
        self.signals = None

        self.no_mvts = int(self.input_form.inputs["Projected annual operations"].text())
        self.no_pax = int(self.input_form.inputs["Projected annual passengers"].text())

        self.appsettings = QSettings("DAiCE")

        self.setAcceptDrops(True)

        self.profiling = False

        self.data_path = self.get_data_path()

        self.icon = QIcon(str(self.data_path / "icon.png"))
        self.setWindowIcon(self.icon)
        self.setWindowTitle("DAiCE - Finance Dashboard")

        # Add signals
        self.signals = Signals(self)
        self.signals.set_window_modified.connect(self.setWindowModified)

        self.setCursor(Qt.ArrowCursor)

        self.bordercolor = "lightgrey"

        # self.signals.connect()

        self.menubar = self.init_menubar()
        self.menubar.setFixedHeight(25)

        mainsplitter = QSplitter(Qt.Horizontal)

        self.charge_widget = AirportCharges(self)
        self.payback_widget = PaybackGraph(self)

        leftsplitter = TabWidget(
            [self.charge_widget], "Airport Charges"
        )
        rightsplitter = TabWidget(
            [self.payback_widget], "Estimated Payback Period"
        )

        mainsplitter.addWidget(leftsplitter)
        mainsplitter.addWidget(rightsplitter)
        mainsplitter.setSizes([150,300])

        finance_layout = HLayout([mainsplitter])
        finance_layout.setMenuBar(self.menubar)

        self.setLayout(finance_layout)

        self.setGeometry(0, 0, 1200, 650)

    def get_data_path(self) -> Path:
        # In case of PyInstaller exe
        if getattr(sys, "frozen", False):
            application_path = Path(sys._MEIPASS)
            data_path = application_path / "data"

        # In case of regular python
        else:
            application_path = Path(__file__).resolve().parent
            data_path = application_path / ".." / "data"

        return data_path

    def setCursorNormal(self):
        """
        Changes cursor (back) to normal cursor.
        """
        QApplication.restoreOverrideCursor()

    def setCursorWait(self):
        """
        Changes cursor to waiting cursor.
        """
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def change_font_size(self, increment):

        self.nodes_edges_widget.nodemodel.layoutAboutToBeChanged.emit()
        self.nodes_edges_widget.edgemodel.layoutAboutToBeChanged.emit()

        sizes = []
        for w in self.app.allWidgets():
            font = w.font()
            size = font.pointSize() + increment
            font.setPointSize(max(1, size))
            sizes.append(size)
            w.setFont(font)

        # Keep track of font increment for opening new windows in the right scale
        # Only if the smallest item has a >= 1 size, the increment is added, to prevent the value getting out of bounds
        if min(sizes) >= 1:
            self.font_increment += increment

        self.signals.font_changed.emit()

        self.nodes_edges_widget.nodemodel.layoutChanged.emit()
        self.nodes_edges_widget.edgemodel.layoutChanged.emit()

    def update_projectname(self, name=None):
        """
        Updates window title after a project has been loaded

        Parameters
        ----------
        name : str, optional
            Project name, by default None
        """
        if name is None:
            self.setWindowTitle("DAiCE [*]")
            self.appsettings.setValue("currentproject", "")
        else:
            self.setWindowTitle(f"DAiCE - {name} [*]")
            self.appsettings.setValue("currentproject", name)

    def open_about(self):
        text = f"Version: {__version__}"
        Qt.QMessageBox.about(self, "DAiCE version", text)

    def open_documentation(self):

        # In case of PyInstaller exe
        if getattr(sys, "frozen", False):
            application_path = Path(sys._MEIPASS)
            indexpath = application_path / "doc" / "index.html"

        # In case of regular python
        else:
            application_path = Path(__file__).resolve().parent
            indexpath = application_path / '..' / '..' / "doc" / 'build' / 'html' / "index.html"

        # Open index html
        subprocess.Popen(str(indexpath), shell=True)

    def init_menubar(self):
        """
        Constructs the menu bar.
        """

        menubar = QMenuBar()

        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.setStatusTip("Create a new project")
        new_action.triggered.connect(self.project.new)

        openAction = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "Open", self)
        openAction.setStatusTip("Open project")
        openAction.setShortcut(QKeySequence.Open)
        openAction.triggered.connect(self.project.open)

        saveAction = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        saveAction.setStatusTip("Save project")
        saveAction.setShortcut(QKeySequence.Save)
        saveAction.triggered.connect(self.project.save)

        saveAsAction = QAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save as", self
        )
        saveAsAction.setStatusTip("Save project as...")
        saveAsAction.setShortcut("Ctrl+Shift+S")
        saveAsAction.triggered.connect(self.project.save_as)

        exitAction = QAction(
            self.style().standardIcon(QStyle.SP_TitleBarCloseButton), "Exit", self
        )
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Close DAiCE")
        exitAction.triggered.connect(self.close)

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(new_action)
        file_menu.addAction(openAction)
        file_menu.addSeparator()
        file_menu.addAction(saveAction)
        file_menu.addAction(saveAsAction)
        file_menu.addSeparator()
        file_menu.addAction(exitAction)

        bn_menu = menubar.addMenu("&BN")
        bn_menu.addAction("Edit BN",
                          lambda: self.open_bnwindow(self.graph_widget, self.matrix_widget, self.nodes_edges_widget,
                                                     self.app))

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Increase UI font", lambda: self.change_font_size(1), QKeySequence("Ctrl+="))
        view_menu.addAction("Decrease UI font", lambda: self.change_font_size(-1), QKeySequence("Ctrl+-"))
        view_menu.addSeparator()

        def _increase_dpi():
            self.graph_widget.increase_dpi(factor=1.2)
            self.matrix_widget.increase_dpi(factor=1.2)

        def _decrease_dpi():
            self.graph_widget.decrease_dpi(factor=1.2)
            self.matrix_widget.decrease_dpi(factor=1.2)

        view_menu.addAction("Increase graph scale", _increase_dpi, QKeySequence("Ctrl+Shift+="))
        view_menu.addAction("Decrease graph scale", _decrease_dpi, QKeySequence("Ctrl+Shift+-"))

        export_menu = menubar.addMenu("&Export")
        export_R_menu = export_menu.addMenu("&Correlation Matrix")
        export_R_menu.addAction("To CSV", lambda: self.project.export("correlation_matrix", "csv"))
        export_R_menu.addAction("To clipboard", lambda: self.project.export("correlation_matrix", "clipboard"))

        export_nodes_menu = export_menu.addMenu("&Nodes")
        export_nodes_menu.addAction("To CSV", lambda: self.project.export("nodes", "csv"))
        export_nodes_menu.addAction("To clipboard", lambda: self.project.export("nodes", "clipboard"))

        export_nodes_menu = export_menu.addMenu("&Edges")
        export_nodes_menu.addAction("To CSV", lambda: self.project.export("edges", "csv"))
        export_nodes_menu.addAction("To clipboard", lambda: self.project.export("edges", "clipboard"))

        help_menu = menubar.addMenu("&Help")
        doc_action = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Documentation", self
        )
        doc_action.setStatusTip("Open Anduryl documentation")
        doc_action.triggered.connect(self.open_documentation)
        help_menu.addAction(doc_action)

        about_action = QAction(QIcon(), "Version", self)
        about_action.triggered.connect(self.open_about)
        help_menu.addAction(about_action)

        return menubar