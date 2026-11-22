import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop,QTimer
from config import Config
from database.repository import Repository
from ui.main_window import MainWindow
from conftest import sii,result


def test_window_background_import(tmp_path):
    app = QApplication.instance() or QApplication([])
    source = tmp_path/"source.sii"
    source.write_text(sii([(1,"scenario_start","academy.scenario.book1.test"),(2,"scenario_end","r")],result()),encoding="utf-8")
    repo = Repository(tmp_path/"test.db")
    pid = repo.add_profile(repo.add_user("A"),"ETS",str(source))
    config = Config(data_dir=str(tmp_path))
    window = MainWindow(repo,config,tmp_path/"config.json")
    window.show()
    window.import_profile(pid)
    loop = QEventLoop()
    QTimer.singleShot(1500,loop.quit)
    loop.exec()
    window.refresh()
    assert window.tabs.count() == 6
    assert window.attempts.table.rowCount() == 1
    assert window.dashboard.cards["attempts"].text() == "1"
    window.close()
    app.processEvents()
