from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QInputDialog
from ui.common import Table


class ScenariosView(QWidget):
    selected = Signal(str)

    def __init__(self,repo):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Dwuklik scenariusza otwiera historię prób."))
        self.table = Table([("scenario_code","Kod scenariusza"),("display_name","Nazwa"),("book_code","Księga"),
                            ("attempt_count","Próby"),("last_score","Ostatnie punkty"),("last_rank","Ostatnia ranga")])
        self.table.cellDoubleClicked.connect(lambda *_: self.selected.emit(self.table.selected()["scenario_code"]))
        layout.addWidget(self.table)
        edit = QPushButton("Ustaw nazwę wybranego scenariusza")
        edit.clicked.connect(self.edit)
        layout.addWidget(edit)

    def edit(self):
        row = self.table.selected()
        if row:
            name,ok = QInputDialog.getText(self,"Nazwa scenariusza","Nazwa:",text=row["display_name"] or "")
            if ok:
                self.repo.execute("UPDATE scenarios SET display_name=? WHERE id=?",(name,row["id"]))
                self.refresh()

    def refresh(self):
        self.table.fill(self.repo.query("""SELECT s.*, (SELECT count(*) FROM attempts a WHERE a.scenario_id=s.id) attempt_count,
            (SELECT score FROM attempts WHERE scenario_id=s.id ORDER BY COALESCE(end_timestamp,start_timestamp) DESC,id DESC LIMIT 1) last_score,
            (SELECT rank_raw FROM attempts WHERE scenario_id=s.id ORDER BY COALESCE(end_timestamp,start_timestamp) DESC,id DESC LIMIT 1) last_rank
            FROM scenarios s ORDER BY scenario_code"""))
