from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QInputDialog,QMessageBox,
                               QDialog,QFormLayout,QLineEdit,QComboBox,QFileDialog,QDialogButtonBox,QLabel)
from ui.common import Table


class UsersView(QWidget):
    changed = Signal()
    import_requested = Signal(int)

    def __init__(self,repo):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        for text,action in [("Dodaj kursanta",self.add_user),("Edytuj kursanta",self.edit_user),
                            ("Dodaj profil",lambda:self.profile_dialog()),("Edytuj profil",self.edit_profile),
                            ("Włącz / wyłącz profil",self.toggle),("Importuj profil",self.import_selected)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Kursanci"))
        self.users = Table([("id","ID"),("name","Nazwa"),("created_at","Dodano (UTC)")])
        layout.addWidget(self.users)
        layout.addWidget(QLabel("Profile ETS2 — wybierz profil do importu lub zmiany monitorowania"))
        self.profiles = Table([("id","ID"),("user_name","Kursant"),("ets_profile_id","Profil"),("enabled","Monitorowanie 1/0"),("source_path","Plik Academy")])
        layout.addWidget(self.profiles,2)

    def refresh(self):
        self.users.fill(self.repo.query("SELECT * FROM users ORDER BY id"))
        self.profiles.fill(self.repo.profiles())

    def add_user(self):
        name,ok = QInputDialog.getText(self,"Nowy kursant","Nazwa:")
        if ok and name.strip():
            self.repo.add_user(name)
            self.changed.emit()

    def edit_user(self):
        row = self.users.selected()
        if not row:
            return
        name,ok = QInputDialog.getText(self,"Edycja kursanta","Nazwa:",text=row["name"])
        if ok and name.strip():
            self.repo.execute("UPDATE users SET name=? WHERE id=?",(name.strip(),row["id"]))
            self.changed.emit()

    def edit_profile(self):
        row = self.profiles.selected()
        if row:
            self.profile_dialog(row)

    def profile_dialog(self,row=None):
        users = self.repo.query("SELECT * FROM users ORDER BY name")
        if not users:
            QMessageBox.information(self,"Profil","Najpierw dodaj kursanta.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Profil ETS2")
        form = QFormLayout(dialog)
        user = QComboBox()
        for u in users:
            user.addItem(f'{u["name"]} (ID {u["id"]})',u["id"])
        name = QLineEdit(row["ets_profile_id"] if row else "")
        path = QLineEdit(row["source_path"] if row else "")
        if row:
            user.setCurrentIndex(user.findData(row["user_id"]))
        pick = QPushButton("Wskaż plik Academy…")
        def browse():
            selected,_ = QFileDialog.getOpenFileName(dialog,"Plik Academy","","Pliki SII (*.sii);;Wszystkie (*)")
            if selected:
                path.setText(selected)
        pick.clicked.connect(browse)
        form.addRow("Kursant",user)
        form.addRow("Nazwa / ID profilu",name)
        form.addRow("Plik lub katalog Academy",path)
        form.addRow(pick)
        buttons = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.rejected.connect(dialog.reject)
        def save():
            from pathlib import Path
            if not name.text().strip() or not path.text().strip():
                QMessageBox.warning(dialog,"Brak danych","Podaj nazwę i ścieżkę profilu.")
                return
            source = Path(path.text()).expanduser().resolve()
            if source.is_dir():
                source /= "academy_book_states.sii"
            duplicates = [p for p in self.repo.profiles() if Path(p["source_path"]).resolve()==source and (not row or p["id"]!=row["id"])]
            if duplicates:
                QMessageBox.warning(dialog,"Powielona ścieżka","Inny profil wskazuje ten sam plik. Wyniki będą przechowywane osobno dla każdego profilu.")
            if row:
                self.repo.execute("UPDATE profiles SET user_id=?,ets_profile_id=?,source_path=? WHERE id=?",
                                  (user.currentData(),name.text().strip(),str(source),row["id"]))
            else:
                self.repo.add_profile(user.currentData(),name.text(),str(source))
            dialog.accept()
            self.changed.emit()
        buttons.accepted.connect(save)
        dialog.resize(620,220)
        dialog.exec()

    def toggle(self):
        row = self.profiles.selected()
        if row:
            self.repo.execute("UPDATE profiles SET enabled=1-enabled WHERE id=?",(row["id"],))
            self.changed.emit()

    def import_selected(self):
        row = self.profiles.selected()
        if row:
            self.import_requested.emit(row["id"])
