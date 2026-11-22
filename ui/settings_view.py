import json
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QFormLayout,QLineEdit,QDoubleSpinBox,QComboBox,QPushButton,QLabel,QMessageBox
from config import Config


class SettingsView(QWidget):
    saved = Signal(object)

    def __init__(self,config,path):
        super().__init__()
        self.path = path
        form = QFormLayout(self)
        self.folder = QLineEdit(config.data_dir)
        self.scan,self.debounce = QDoubleSpinBox(),QDoubleSpinBox()
        self.scan.setRange(1,3600)
        self.scan.setValue(config.scan_seconds)
        self.debounce.setRange(.1,60)
        self.debounce.setValue(config.debounce_seconds)
        self.command = QLineEdit(json.dumps(config.bsii_command,ensure_ascii=False))
        self.command.setPlaceholderText('["C:/tools/decoder.exe", "{input}", "{output}"]')
        self.level = QComboBox()
        self.level.addItems(["DEBUG","INFO","WARNING","ERROR"])
        self.level.setCurrentText(config.log_level)
        form.addRow("Katalog danych",self.folder)
        form.addRow("Skan okresowy (s)",self.scan)
        form.addRow("Debounce (s)",self.debounce)
        form.addRow("Dekoder BSII — argumenty JSON",self.command)
        form.addRow("Poziom logowania",self.level)
        note = QLabel("Zmiana katalogu danych wymaga ponownego uruchomienia. Baza nie jest automatycznie przenoszona. Ścieżki źródeł i ich monitorowanie ustawisz w zakładce Użytkownicy. Dekoder BSII działa na kopii pliku; dopasuj argumenty do jego dokumentacji.")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow("Plik konfiguracji",QLabel(str(path)))
        self.feedback = QLabel()
        form.addRow(self.feedback)
        button = QPushButton("Zapisz ustawienia")
        button.clicked.connect(self.save)
        form.addRow(button)

    def save(self):
        try:
            config = Config(self.folder.text(),self.scan.value(),self.debounce.value(),
                            json.loads(self.command.text()),self.level.currentText())
            config.save(self.path)
            self.saved.emit(config)
            self.feedback.setText("Zapisano. Zmiana katalogu danych obowiązuje po ponownym uruchomieniu.")
        except (ValueError,TypeError,OSError) as exc:
            QMessageBox.warning(self,"Ustawienia",str(exc))
