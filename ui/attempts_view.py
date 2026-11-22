from datetime import datetime, time
from zoneinfo import ZoneInfo
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QDateEdit,QCheckBox,QLabel,QPushButton
from ui.common import Table


class Filters(QWidget):
    def __init__(self,repo):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.user,self.profile,self.scenario,self.status = QComboBox(),QComboBox(),QComboBox(),QComboBox()
        for label,widget in [("Kursant",self.user),("Profil",self.profile),("Scenariusz",self.scenario),("Status",self.status)]:
            row.addWidget(QLabel(label))
            row.addWidget(widget)
        self.status.addItem("Wszystkie",None)
        for value in ("unknown","in_progress","interrupted","completed","failed"):
            self.status.addItem(value,value)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.dates = QCheckBox("Zakres dat (Warszawa)")
        self.start,self.end = QDateEdit(QDate.currentDate().addYears(-1)),QDateEdit(QDate.currentDate())
        for widget in (self.start,self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.dates)
        row.addWidget(self.start)
        row.addWidget(QLabel("do"))
        row.addWidget(self.end)
        row.addStretch()
        layout.addLayout(row)
        self.user.currentIndexChanged.connect(self.refresh_profiles)

    def refresh_profiles(self):
        value = self.profile.currentData()
        self.profile.blockSignals(True)
        self.profile.clear()
        self.profile.addItem("Wszystkie",None)
        for p in self.repo.profiles():
            if self.user.currentData() is None or p["user_id"] == self.user.currentData():
                self.profile.addItem(f'{p["ets_profile_id"]} (ID {p["id"]})',p["id"])
        self.profile.setCurrentIndex(max(0,self.profile.findData(value)))
        self.profile.blockSignals(False)

    def refresh(self):
        for widget,rows,key,label in [(self.user,self.repo.query("SELECT * FROM users ORDER BY name"),"id","name"),
                                      (self.scenario,self.repo.query("SELECT * FROM scenarios ORDER BY scenario_code"),"scenario_code","scenario_code")]:
            value = widget.currentData()
            widget.blockSignals(True)
            widget.clear()
            widget.addItem("Wszystkie",None)
            for r in rows:
                widget.addItem(r[label],r[key])
            widget.setCurrentIndex(max(0,widget.findData(value)))
            widget.blockSignals(False)
        self.refresh_profiles()

    def values(self):
        values = dict(user_id=self.user.currentData(),profile_id=self.profile.currentData(),
                      scenario=self.scenario.currentData(),status=self.status.currentData())
        if self.dates.isChecked():
            if self.start.date() > self.end.date():
                raise ValueError("Data początkowa jest późniejsza niż końcowa")
            zone = ZoneInfo("Europe/Warsaw")
            values["date_from"] = int(datetime.combine(self.start.date().toPython(),time.min,zone).timestamp())
            values["date_to"] = int(datetime.combine(self.end.date().toPython(),time.max,zone).timestamp())
        return values


class AttemptsView(QWidget):
    def __init__(self,repo):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)
        self.filters = Filters(repo)
        layout.addWidget(self.filters)
        button = QPushButton("Zastosuj filtry")
        button.clicked.connect(self.refresh_table)
        layout.addWidget(button)
        self.error = QLabel()
        layout.addWidget(self.error)
        self.table = Table([("user_name","Kursant"),("profile_name","Profil"),("scenario_code","Scenariusz"),("attempt_number","Próba"),
                            ("start_timestamp","Start (Warszawa)"),("end_timestamp","Koniec (Warszawa)"),("score","Punkty"),
                            ("rank_raw","Ranga"),("game_duration_raw","Czas gry (surowy)"),("elapsed_seconds","Czas (s)"),
                            ("status","Status"),("match_confidence","Pewność"),("visible_in_latest","W aktualnym zapisie 1/0")])
        layout.addWidget(self.table)

    def refresh(self):
        self.filters.refresh()
        self.refresh_table()

    def refresh_table(self):
        try:
            self.table.fill(self.repo.attempts(**self.filters.values()))
            self.error.clear()
        except ValueError as exc:
            self.error.setText(str(exc))
