__author__ = """Lisa Scholtens"""
__email__ = "l.m.scholtens@student.tudelft.nl"
__version__ = "1.0.0"

if __name__ == "__main__":

    # Import PyQt modules
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    import sys

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    app.setApplicationVersion(__version__)

    # Import GUI
    from ui.main import MainWindow

    # Create main window
    ex = MainWindow(app)

    # Open project
    if len(sys.argv) > 1:
        ex.project.open(fname=sys.argv[1])
        ex.setCursorNormal()

    sys.exit(app.exec_())