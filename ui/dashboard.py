from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame


class Dashboard(QWidget):
    def __init__(self, repo):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)
        title = QLabel("Postępy Driving Academy")
        title.setObjectName("heading")
        layout.addWidget(title)
        layout.addWidget(QLabel("Historia lokalna • dane gry wyłącznie do odczytu"))
        grid = QGridLayout()
        self.cards = {}
        for i,(key,label) in enumerate([("users","Kursanci"),("profiles","Profile ETS2"),("scenarios","Scenariusze"),
                                       ("attempts","Zarejestrowane próby"),("unknown","Nieznany wynik")]):
            card = QFrame()
            card.setObjectName("card")
            content = QVBoxLayout(card)
            content.addWidget(QLabel(label))
            number = QLabel("0")
            number.setObjectName("number")
            content.addWidget(number)
            self.cards[key] = number
            grid.addWidget(card,i//3,i%3)
        layout.addLayout(grid)
        self.monitor_label = QLabel("Monitorowanie zatrzymane")
        layout.addWidget(self.monitor_label)
        self.last_import = QLabel("Brak importów w tej sesji")
        self.last_import.setWordWrap(True)
        layout.addWidget(self.last_import)
        note = QLabel("Wynik unknown oznacza brak potwierdzonej reguły zaliczenia. Ranga i czas gry są przechowywane w oryginalnej postaci. Daty prób: Europe/Warsaw.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def refresh(self):
        for table in ("users","profiles","scenarios","attempts"):
            self.cards[table].setText(str(self.repo.query(f"SELECT count(*) n FROM {table}")[0]["n"]))
        self.cards["unknown"].setText(str(self.repo.query("SELECT count(*) n FROM attempts WHERE status='unknown'")[0]["n"]))
