from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem
from reports.excel_export import local_time


class Table(QTableWidget):
    def __init__(self, columns):
        super().__init__()
        self.columns = columns
        self.rows = []
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([label for _,label in columns])
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()

    def fill(self, rows):
        selected = self.selected()
        self.rows = rows
        self.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,(key,_) in enumerate(self.columns):
                value = row.get(key)
                if key in ("start_timestamp","end_timestamp") and value is not None:
                    try:
                        value = local_time(value).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError,OSError,OverflowError):
                        value = str(value)
                self.setItem(i,j,QTableWidgetItem("" if value is None else str(value)))
            if selected and row.get("id") == selected.get("id"):
                self.selectRow(i)
        self.resizeColumnsToContents()
        for j,(key,_) in enumerate(self.columns):
            minimum = 110
            if key in ("start_timestamp","end_timestamp","created_at"):
                minimum = 175
            elif key in ("scenario_code","source_path"):
                minimum = 310
            elif key in ("user_name","profile_name","name","ets_profile_id","match_confidence"):
                minimum = 165
            self.setColumnWidth(j,max(minimum,self.columnWidth(j)))

    def selected(self):
        row = self.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None


class JobSignals(QObject):
    done = Signal(object)
    error = Signal(str)


class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = JobSignals()

    @Slot()
    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as exc:
            self.signals.error.emit(str(exc))
