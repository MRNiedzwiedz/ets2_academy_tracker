import argparse
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication,QMessageBox
from config import Config,default_data_dir,configure_logging
from database.repository import Repository
from ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="ETS2 Academy Tracker")
    parser.add_argument("--config",type=Path,default=default_data_dir()/"config.json")
    parser.add_argument("--smoke-test",action="store_true",help="Uruchom GUI i zamknij po 1,5 s (kontrola pakietu)")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("ETS2 Academy Tracker")
    try:
        config = Config.load(args.config)
        configure_logging(config)
        repo = Repository(Path(config.data_dir)/"academy.db")
        window = MainWindow(repo,config,args.config)
        window.show()
        if args.smoke_test:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500,window.close)
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None,"ETS2 Academy Tracker",f"Nie można uruchomić aplikacji: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
