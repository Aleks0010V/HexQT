# hexqt.py -- HexQT a pretty QT hext editor.
import enum
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QAction, QMainWindow, QFileDialog, QTextEdit, QDesktopWidget
# QT5 Python Binding
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout
from PyQt5.QtWidgets import QInputDialog, QLineEdit


class Mode(enum.Enum):
    READ = 0  # Purely read the hex.
    ADDITION = 1  # Add to the hex.
    OVERRIDE = 2  # Override the current text.


class FileSelector(QFileDialog):
    def __init__(self):
        super(FileSelector, self).__init__()
        self.file_name = None
        self.selectFile()
        self.show()

    def selectFile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Directory View", "", "All Files (*)", options=options)

        self.file_name = file_name


class InputDialogue(QInputDialog):
    def __init__(self, title, text):
        super(InputDialogue, self).__init__()

        # Dialogue options.
        self.dialog_title: str = title
        self.dialog_text: str = text
        self.dialog_response = None

        self.init_ui()

    # initUI ... Initialize the main view of the dialogue.
    def init_ui(self):
        dialogue_response, dialogue_complete = QInputDialog.getText(self, self.dialog_title, self.dialog_text,
                                                                    QLineEdit.Normal, '')
        if dialogue_complete and dialogue_response:
            self.dialog_response = dialogue_response
        else:
            self.dialog_response = ''


class App(QMainWindow):
    def __init__(self):
        super(App, self).__init__()

        # Window options!
        self.title: str = 'HexQT'
        self.left: int = 0
        self.top: int = 0
        self.width: int = 1280
        self.height: int = 840

        self.row_spacing: int = 4  # How many bytes before a double space.
        self.row_length: int = 16  # How many bytes in a row.
        self.byte_width: int = 2  # How many bits to include in a byte.
        self.mode = Mode.READ

        self.initUI()

    def read_file(self, file_name):
        file_data = ''

        if file_name:
            with open(file_name, 'rb') as fileObj:
                file_data = fileObj.read()

        self.generate_view(file_data)

    def generate_view(self, text):
        """generates hex text"""
        space = ' '

        row_spacing = self.row_spacing
        row_length = self.row_length

        offset = 1

        offset_text = ''
        main_text = ''
        ascii_text = ''

        for index, b in enumerate(text):
            char = chr(b)

            if char in (' ', '', '\n', '\t', '\r', '\b'):
                ascii_text += '.'
            else:
                ascii_text += char

            main_text += format(b, '0' + str(self.byte_width) + 'x')

            if (index + 1) % row_length == 0:
                offset_text += format(offset, '04x') + '\n'
                main_text += '\n'
                ascii_text += '\n'
            elif (index + 1) % row_spacing == 0:
                main_text += space * 2
            else:
                main_text += space

            offset += len(char)

        self.offset_text_area.setText(offset_text)
        self.main_text_area.setText(main_text)
        self.ascii_text_area.setText(ascii_text)

    def open_file(self):
        file_select = FileSelector()
        file_name = file_select.file_name

        self.read_file(file_name)

    def save_file(self):
        print('Saved!')

    def highlight_main(self) -> None:
        """Bidirectional highlighting from main"""

        # Create and get cursors for getting and setting selections.
        highlight_cursor = QTextCursor(self.ascii_text_area.document())
        cursor = self.main_text_area.textCursor()

        # Clear any current selections and reset text color.
        highlight_cursor.select(QTextCursor.Document)
        highlight_cursor.setCharFormat(QTextCharFormat())
        highlight_cursor.clearSelection()

        # Information about where selections and rows start.
        selected_text = cursor.selectedText()  # The actual text selected.
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()

        total_bytes = self.__get_valuable_positions_length(selected_text)  # get all valuable positions
        # \n and word length compensation
        total_bytes = self.__negative_compensation(total_bytes)

        main_text = self.main_text_area.toPlainText().replace('\n', ' ')
        ascii_start = self.__get_valuable_positions_length(main_text[:selection_start])  # get all valuable positions
        # \n and word length compensation
        ascii_start = self.__negative_compensation(ascii_start)
        ascii_end = ascii_start + total_bytes

        # Select text and highlight it.
        highlight_cursor.setPosition(ascii_start, QTextCursor.MoveAnchor)
        highlight_cursor.setPosition(ascii_end, QTextCursor.KeepAnchor)

        highlight = QTextCharFormat()
        highlight.setBackground(Qt.red)
        highlight_cursor.setCharFormat(highlight)
        highlight_cursor.clearSelection()

    def highlight_ascii(self) -> None:
        """Bidirectional highlighting from ascii"""

        # Create and get cursors for getting and setting selections.
        highlight_cursor = QTextCursor(self.main_text_area.document())
        cursor = self.ascii_text_area.textCursor()

        # Clear any current selections and reset text color.
        highlight_cursor.select(QTextCursor.Document)
        highlight_cursor.setCharFormat(QTextCharFormat())
        highlight_cursor.clearSelection()

        # Information about where selections and rows start.
        selected_text = cursor.selectedText()  # The actual text selected.
        selection_start = cursor.selectionStart()

        ascii_text = self.ascii_text_area.toPlainText().replace('\n', '')
        main_start = self.__get_valuable_positions_length(ascii_text[:selection_start])
        main_start = self.__positive_compensation(main_start)

        total_bytes = self.__get_valuable_positions_length(selected_text)  # get all valuable positions
        # \n and word length compensation
        total_bytes = self.__positive_compensation(total_bytes)
        selection_end = main_start + total_bytes

        # Select text and highlight it.
        highlight_cursor.setPosition(main_start, QTextCursor.MoveAnchor)
        highlight_cursor.setPosition(selection_end, QTextCursor.KeepAnchor)

        highlight = QTextCharFormat()
        highlight.setBackground(Qt.red)
        highlight_cursor.setCharFormat(highlight)
        highlight_cursor.clearSelection()

    @staticmethod
    def __get_valuable_positions_length(array):
        return len(list(filter(lambda x: x not in ('', ' '), array)))

    def __positive_compensation(self, value):
        return self.byte_width * value + value

    def __negative_compensation(self, value):
        return (value + value // self.row_length) // self.byte_width

    # Creates a dialogue and gets the offset to jump to and then jumps to that offset.
    def offset_jump(self):
        jump_text = InputDialogue('Jump to Offset', 'Offset').dialog_response
        jump_offset = 0xF

        main_text = self.main_text_area.toPlainText()
        main_text = main_text.strip().replace('  ', ' ')

        text_cursor = self.main_text_area.textCursor()

    # createMainView ... Creates the primary view and look of the application (3-text areas.)
    def create_main_view(self) -> QHBoxLayout:
        qh_box = QHBoxLayout()

        self.main_text_area = QTextEdit()
        self.offset_text_area = QTextEdit()
        self.ascii_text_area = QTextEdit()

        # Initialize them all to read only.
        self.main_text_area.setReadOnly(True)
        self.ascii_text_area.setReadOnly(True)
        self.offset_text_area.setReadOnly(True)

        # Create the fonts and styles to be used and then apply them.
        font = QFont("Courier New", 12, QFont.Normal, False)

        self.main_text_area.setFont(font)
        self.ascii_text_area.setFont(font)
        self.offset_text_area.setFont(font)

        self.offset_text_area.setTextColor(Qt.red)

        # Syncing scrolls.
        self.sync_scrolls(self.main_text_area, self.ascii_text_area, self.offset_text_area)

        # Highlight linking. BUG-GY
        self.main_text_area.selectionChanged.connect(self.highlight_main)
        self.ascii_text_area.selectionChanged.connect(self.highlight_ascii)

        qh_box.addWidget(self.offset_text_area, 1)
        qh_box.addWidget(self.main_text_area, 6)
        qh_box.addWidget(self.ascii_text_area, 2)

        return qh_box

    def initUI(self):
        # Initialize basic window options.
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Center the window.
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

        # Creates a menu bar, (file, edit, options, etc...)
        mainMenu = self.menuBar()

        # Menus for window.
        file_menu = mainMenu.addMenu('File')
        edit_menu = mainMenu.addMenu('Edit')
        view_menu = mainMenu.addMenu('View')
        help_menu = mainMenu.addMenu('Help')

        # FILE MENU ---------------------------------------

        # Open button.
        open_button = QAction(QIcon(), 'Open', self)
        open_button.setShortcut('Ctrl+O')
        open_button.setStatusTip('Open file')
        open_button.triggered.connect(self.open_file)

        # Save button.
        save_button = QAction(QIcon(), 'Save', self)
        save_button.setShortcut('Ctrl+S')
        save_button.setStatusTip('Open file')
        save_button.triggered.connect(self.save_file)

        # Optional exit stuff.
        exit_button = QAction(QIcon(), 'Exit', self)
        exit_button.setShortcut('Ctrl+Q')
        exit_button.setStatusTip('Exit application')
        exit_button.triggered.connect(self.close)

        file_menu.addAction(open_button)
        file_menu.addAction(save_button)
        file_menu.addAction(exit_button)

        # EDIT MENU ---------------------------------------

        # Jump to Offset
        offset_button = QAction(QIcon(), 'Jump to Offset', self)
        offset_button.setShortcut('Ctrl+J')
        offset_button.setStatusTip('Jump to Offset')
        offset_button.triggered.connect(self.offset_jump)

        edit_menu.addAction(offset_button)

        # Creating a widget for the central widget thingy.
        central_widget = QWidget()
        central_widget.setLayout(self.create_main_view())

        self.setCentralWidget(central_widget)

        # Show our masterpiece.
        self.show()

    # Syncs the horizontal scrollbars of multiple qTextEdit objects. Rather clunky but it works.
    @staticmethod
    def sync_scrolls(q_text_obj0, q_text_obj1, q_text_obj2):
        scroll0 = q_text_obj0.verticalScrollBar()
        scroll1 = q_text_obj1.verticalScrollBar()
        scroll2 = q_text_obj2.verticalScrollBar()

        # There seems to be no better way of doing this at present so...

        scroll0.valueChanged.connect(
            scroll1.setValue
        )

        scroll0.valueChanged.connect(
            scroll2.setValue
        )

        scroll1.valueChanged.connect(
            scroll0.setValue
        )

        scroll1.valueChanged.connect(
            scroll2.setValue
        )

        scroll2.valueChanged.connect(
            scroll1.setValue
        )

        scroll2.valueChanged.connect(
            scroll0.setValue
        )


# setStyle ... Sets the style of the QT Application. Right now using edgy black.
def set_style(q_app):
    q_app.setStyle("Fusion")

    dark_palette = QPalette()

    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.white)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    q_app.setPalette(dark_palette)

    q_app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")


def main():
    app = QApplication(sys.argv)
    set_style(app)

    hexqt = App()
    sys.exit(app.exec_())


# Initialize the program.
if __name__ == '__main__':
    main()
