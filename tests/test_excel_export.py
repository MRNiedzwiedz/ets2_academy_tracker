import hashlib
from openpyxl import load_workbook
from database.repository import Repository
from monitoring.importer import Importer
from monitoring.snapshot import Snapshot
from reports.excel_export import export_excel
from conftest import sii,result


def test_export(tmp_path):
    repo = Repository(tmp_path/"test.db")
    uid = repo.add_user('=HYPERLINK("evil")')
    pid = repo.add_profile(uid,"ETS2",str(tmp_path/"source.sii"))
    raw = sii([(1,"scenario_start","academy.scenario.book1.test"),(2,"scenario_end","r")],result(rank="nil")).encode()
    snap = Snapshot(raw,hashlib.sha256(raw).hexdigest())
    imp = Importer(repo)
    imp.import_snapshot(pid,snap)
    imp.import_snapshot(pid,snap)
    path = export_excel(repo,tmp_path/"report.xlsx",user_id=uid)
    wb = load_workbook(path)
    assert wb.sheetnames == ["Użytkownicy","Scenariusze","Historia prób","Diagnostyka importu"]
    history = wb["Historia prób"]
    assert history.max_row == 2
    assert history["A2"].data_type == "s"
    assert history["H2"].value == "nil"
    assert history["E2"].is_date
    for ws in wb:
        assert ws.freeze_panes == "A2" and ws.auto_filter.ref
    empty = load_workbook(export_excel(repo,tmp_path/"empty.xlsx",date_from=999))
    assert empty["Historia prób"].max_row == 1


def test_empty_database(tmp_path):
    repo = Repository(tmp_path/"test.db")
    wb = load_workbook(export_excel(repo,tmp_path/"empty.xlsx"))
    assert len(wb.sheetnames) == 4
