LIGHT_STYLESHEET = """
QWidget {
    background-color: #F0F0F0;
    color: #333333;
    font-family: "Segoe UI", "Cantarell", "sans-serif";
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #1E88E5;
}
QLineEdit, QComboBox, QTextEdit {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 8px;
    background-color: #FFFFFF;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #1E88E5;
}
QTableWidget {
    border: 1px solid #D0D0D0;
    gridline-color: #E0E0E0;
    background-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #EAEAEA;
    padding: 4px;
    border: 1px solid #D0D0D0;
    font-weight: bold;
}
QPushButton {
    border: 1px solid #C0C0C0;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #FDFDFD;
}
QPushButton:hover {
    background-color: #E8E8E8;
}
QPushButton:pressed {
    background-color: #D8D8D8;
}
QPushButton[primary="true"] {
    background-color: #1E88E5;
    color: white;
    border: 1px solid #1A75C4;
}
QPushButton[primary="true"]:hover {
    background-color: #1A75C4;
}
QPushButton[primary="true"]:pressed {
    background-color: #1663A3;
}
QProgressBar {
    border: 1px solid #C0C0C0;
    border-radius: 4px;
    text-align: center;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #1E88E5;
    border-radius: 3px;
}
QTabBar::tab {
    background-color: #E1E1E1;
    color: #555555;
    padding: 10px 20px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1E88E5;
    color: white;
}
"""

DARK_STYLESHEET = """
QWidget {
    background-color: #2D2D2D;
    color: #EAEAEA;
    font-family: "Segoe UI", "Cantarell", "sans-serif";
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #454545;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #42A5F5;
}
QLineEdit, QComboBox, QTextEdit {
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 8px;
    background-color: #383838;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #42A5F5;
}
QTableWidget {
    border: 1px solid #454545;
    gridline-color: #404040;
    background-color: #383838;
}
QHeaderView::section {
    background-color: #3A3A3A;
    padding: 4px;
    border: 1px solid #454545;
    font-weight: bold;
}
QPushButton {
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #404040;
}
QPushButton:hover {
    background-color: #4A4A4A;
}
QPushButton:pressed {
    background-color: #505050;
}
QPushButton[primary="true"] {
    background-color: #42A5F5;
    color: #1D1D1D;
    border: 1px solid #3B92D4;
    font-weight: bold;
}
QPushButton[primary="true"]:hover {
    background-color: #3B92D4;
}
QPushButton[primary="true"]:pressed {
    background-color: #3580B8;
}
QProgressBar {
    border: 1px solid #555555;
    border-radius: 4px;
    text-align: center;
    color: #EAEAEA;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #42A5F5;
    border-radius: 3px;
}
QTabBar::tab {
    background-color: #3A3A3A;
    color: #CCCCCC;
    padding: 10px 20px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #42A5F5;
    color: #1D1D1D;
    font-weight: bold;
}
"""
