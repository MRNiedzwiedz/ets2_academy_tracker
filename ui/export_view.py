from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QFileDialog,QMessageBox
from ui.attempts_view import Filters


class ExportView(QWidget):
    requested = Signal(str,object)

    def __init__(self,repo):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Raport XLSX z bazy SQLite: Użytkownicy, Scenariusze, Historia prób, Diagnostyka importu."))
        self.filters = Filters(repo)
        layout.addWidget(self.filters)
        button = QPushButton("Eksportuj XLSX…")
        button.clicked.connect(self.export)
        layout.addWidget(button)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        layout.addStretch()

    def refresh(self):
        self.filters.refresh()

    def export(self):
        try:
            filters = self.filters.values()
        except ValueError as exc:
            QMessageBox.warning(self,"Eksport",str(exc))
            return
        path,_ = QFileDialog.getSaveFileName(self,"Zapisz raport","Academy.xlsx","Excel (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            self.feedback.setText("Tworzenie raportu…")
            self.requested.emit(path,filters)
