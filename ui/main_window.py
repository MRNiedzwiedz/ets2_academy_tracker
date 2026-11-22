from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QThread, QThreadPool, Signal, QTimer
from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,QMessageBox
from academy.decoder import Decoder
from config import configure_logging
from monitoring.file_watcher import FileMonitor
from monitoring.importer import Importer
from reports.excel_export import export_excel
from ui.common import Job
from ui.dashboard import Dashboard
from ui.users_view import UsersView
from ui.scenarios_view import ScenariosView
from ui.attempts_view import AttemptsView
from ui.settings_view import SettingsView
from ui.export_view import ExportView


class MonitorThread(QThread):
    update = Signal(str,str)

    def __init__(self,importer,config):
        super().__init__()
        self.monitor = FileMonitor(importer,config.scan_seconds,config.debounce_seconds,self.update.emit)

    def run(self):
        try:
            self.monitor.run()
        except Exception as exc:
            self.update.emit("error",str(exc))


class MainWindow(QMainWindow):
    def __init__(self,repo,config,config_path):
        super().__init__()
        self.repo,self.config = repo,config
        self.importer = Importer(repo,Decoder(config.bsii_command))
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.jobs = []
        self.monitor_thread = None
        self.setWindowTitle("ETS2 Academy Tracker")
        self.resize(1280,800)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        top = QHBoxLayout()
        title = QLabel("ETS2  /  ACADEMY TRACKER")
        title.setObjectName("heading")
        top.addWidget(title)
        top.addStretch()
        self.monitor_button = QPushButton("Uruchom monitorowanie")
        self.monitor_button.clicked.connect(self.toggle_monitor)
        top.addWidget(self.monitor_button)
        layout.addLayout(top)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.dashboard = Dashboard(repo)
        self.users = UsersView(repo)
        self.scenarios = ScenariosView(repo)
        self.attempts = AttemptsView(repo)
        self.export = ExportView(repo)
        self.settings = SettingsView(config,config_path)
        self.views = [self.dashboard,self.users,self.scenarios,self.attempts,self.export]
        for widget,name in zip(self.views+[self.settings],["Dashboard","Użytkownicy","Scenariusze","Historia prób","Eksport","Ustawienia"]):
            self.tabs.addTab(widget,name)
        self.users.changed.connect(self.refresh)
        self.users.import_requested.connect(self.import_profile)
        self.scenarios.selected.connect(self.show_scenario)
        self.export.requested.connect(self.export_report)
        self.settings.saved.connect(self.apply_settings)
        self.refresh()
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#f3f6f7; color:#183b49; font-family:'Segoe UI'; font-size:13px; }
            QLabel#heading { font-size:24px; font-weight:700; padding:12px 0; }
            QFrame#card { background:white; border:1px solid #d7e2e5; border-radius:9px; padding:14px; }
            QLabel#number { font-size:36px; font-weight:700; color:#007c83; }
            QPushButton { background:#176977; color:white; padding:9px 15px; border:0; border-radius:5px; }
            QPushButton:hover { background:#218b97; } QPushButton:disabled { background:#8caaaf; }
            QTabBar::tab { padding:13px 19px; } QTabBar::tab:selected { background:#173d50; color:white; }
            QTableWidget { background:white; alternate-background-color:#edf4f5; gridline-color:#dce5e8; }
            QHeaderView::section { background:#dce9ed; padding:8px; border:0; font-weight:600; }
            QLineEdit,QComboBox,QDateEdit,QDoubleSpinBox { background:white; padding:6px; border:1px solid #bacdd3; border-radius:4px; }
        """)
        QTimer.singleShot(0,self.start_monitor)

    def refresh(self):
        for view in self.views:
            view.refresh()

    def submit(self,function,done):
        job = Job(function)
        self.jobs.append(job)
        def finish(result):
            done(result)
            if job in self.jobs:
                self.jobs.remove(job)
        def fail(message):
            self.error(message)
            self.export.feedback.setText("Operacja nie powiodła się: " + message)
            if job in self.jobs:
                self.jobs.remove(job)
        job.signals.done.connect(finish)
        job.signals.error.connect(fail)
        self.pool.start(job)

    def error(self,message):
        self.statusBar().showMessage(message,15000)
        self.dashboard.last_import.setText(message)

    def import_profile(self,pid):
        self.statusBar().showMessage("Import w tle…")
        importer = self.importer
        def done(result):
            message = f"Zdarzenia: {result.events}; nowe próby: {result.new_attempts}" + ("; zapis już zaimportowany" if result.duplicate else "")
            self.dashboard.last_import.setText(message + "\n" + "\n".join(result.warnings))
            self.statusBar().showMessage(message,10000)
            self.refresh()
        self.submit(lambda:importer.import_file(pid),done)

    def export_report(self,path,filters):
        self.submit(lambda:export_excel(self.repo,path,**filters),
                    lambda result:self.export.feedback.setText(f"Zapisano: {result}"))

    def show_scenario(self,code):
        self.attempts.filters.scenario.setCurrentIndex(self.attempts.filters.scenario.findData(code))
        self.attempts.refresh_table()
        self.tabs.setCurrentWidget(self.attempts)

    def start_monitor(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            return
        self.monitor_thread = MonitorThread(self.importer,self.config)
        self.monitor_thread.update.connect(self.monitor_update)
        self.monitor_thread.finished.connect(self.monitor_finished)
        self.monitor_thread.start()
        self.monitor_button.setText("Zatrzymaj monitorowanie")

    def monitor_finished(self):
        self.monitor_button.setEnabled(True)
        self.monitor_button.setText("Uruchom monitorowanie")
        self.dashboard.monitor_label.setText("Monitorowanie zatrzymane")

    def toggle_monitor(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.monitor.stop()
            self.monitor_button.setEnabled(False)
            self.monitor_button.setText("Zatrzymywanie…")
        else:
            self.start_monitor()

    def monitor_update(self,kind,message):
        if kind == "status":
            self.dashboard.monitor_label.setText(message)
        else:
            self.dashboard.last_import.setText(message)
            self.statusBar().showMessage(message,15000)
            if kind == "import":
                self.refresh()

    def apply_settings(self,config):
        # Keep the active database/log directory until restart.
        self.config = replace(config,data_dir=self.config.data_dir)
        configure_logging(self.config)
        self.importer = Importer(self.repo,Decoder(config.bsii_command))
        if self.monitor_thread and self.monitor_thread.isRunning():
            monitor = self.monitor_thread.monitor
            monitor.importer = self.importer
            monitor.scan_seconds = config.scan_seconds
            monitor.debounce_seconds = config.debounce_seconds
            monitor.wake.set()

    def closeEvent(self,event):
        self.timer.stop()
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.monitor.stop()
            self.monitor_thread.wait(35000)
        self.pool.waitForDone(35000)
        if (self.monitor_thread and self.monitor_thread.isRunning()) or self.pool.activeThreadCount():
            event.ignore()
            self.statusBar().showMessage("Trwa kończenie importu. Zamknij okno ponownie za chwilę.")
            return
        event.accept()
