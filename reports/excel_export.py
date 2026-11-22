from collections import defaultdict
from datetime import datetime, timezone
import logging
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from database.connection import connect
from database.repository import Repository

WARSAW = ZoneInfo("Europe/Warsaw")


def local_time(timestamp):
    return datetime.fromtimestamp(timestamp,timezone.utc).astimezone(WARSAW).replace(tzinfo=None) if timestamp is not None else None


def safe(value):
    # Force user-controlled text to a literal Excel cell, never a formula.
    return value


def export_excel(repo: Repository, destination: str | Path, **filters) -> Path:
    destination = Path(destination)
    # Prevent replacing game saves or the live database with an Excel workbook.
    if destination.suffix.lower() != ".xlsx":
        raise ValueError("Plik raportu musi mieć rozszerzenie .xlsx")
    paths = {Path(p["source_path"]).resolve() for p in repo.profiles()}
    if destination.resolve() in paths or destination.resolve() == repo.path.resolve():
        raise ValueError("Raport nie może nadpisać źródła ani bazy danych")
    # One read transaction yields a consistent report while monitoring imports.
    with connect(repo.path) as db:
        db.execute("BEGIN")
        class View:
            def query(self, sql, params=()):
                return [dict(r) for r in db.execute(sql,params)]
        view = View()
        rows = Repository.attempts(view,**filters)
        profiles = view.query("SELECT p.*,u.name user_name FROM profiles p JOIN users u ON u.id=p.user_id")
        snapshots = view.query("SELECT i.*,p.ets_profile_id FROM import_snapshots i JOIN profiles p ON p.id=i.profile_id ORDER BY i.id")
    allowed = {p["id"] for p in profiles if (not filters.get("user_id") or p["user_id"]==filters["user_id"])
               and (not filters.get("profile_id") or p["id"]==filters["profile_id"])}
    workbook = Workbook()
    workbook.remove(workbook.active)

    def sheet(name,headers,data):
        ws = workbook.create_sheet(name)
        ws.append(headers)
        for values in data:
            ws.append(values)
            for cell in ws[ws.max_row]:
                if isinstance(cell.value,str):
                    cell.data_type = "s"
                elif isinstance(cell.value,datetime):
                    cell.number_format = "yyyy-mm-dd hh:mm:ss"
        for cell in ws[1]:
            cell.font = Font(bold=True,color="FFFFFF")
            cell.fill = PatternFill("solid",fgColor="173D50")
            cell.alignment = Alignment(wrap_text=True)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column in ws.columns:
            width = min(65,max(14,max(len(str(c.value or "")) for c in column)+2))
            ws.column_dimensions[column[0].column_letter].width = width
        ws.row_dimensions[1].height = 32

    by_profile, by_scenario = defaultdict(list),defaultdict(list)
    for r in rows:
        by_profile[r["profile_id"]].append(r)
        by_scenario[(r["profile_id"],r["scenario_code"])] .append(r)
    sheet("Użytkownicy",["Użytkownik","Profil","Scenariusze","Próby","Potwierdzone zaliczenia","Nieznany wynik"],
          [(p["user_name"],p["ets_profile_id"],len({r["scenario_code"] for r in by_profile[p["id"]]}),len(by_profile[p["id"]]),
            sum(r["status"]=="completed" for r in by_profile[p["id"]]),sum(r["status"]=="unknown" for r in by_profile[p["id"]]))
           for p in profiles if p["id"] in allowed])
    sheet("Scenariusze",["Użytkownik","Profil","Scenariusz","Próby","Potwierdzone zaliczenia","Ostatnia próba (Warszawa)","Najwyższa liczba punktów"],
          [(group[0]["user_name"],group[0]["profile_name"],code,len(group),sum(r["status"]=="completed" for r in group),
            local_time(max(r["end_timestamp"] or r["start_timestamp"] for r in group)),
            max((r["score"] for r in group if r["score"] is not None),default=None))
           for (_,code),group in by_scenario.items()])
    sheet("Historia prób",["Użytkownik","Profil","Scenariusz","Nr próby","Start (Warszawa)","Koniec (Warszawa)",
                         "Punkty","Ranga surowa","Czas gry (jednostka nieznana)","Czas start–koniec (s)","Status","Pewność","Widoczna w ostatnim zapisie"],
          [(r["user_name"],r["profile_name"],r["scenario_code"],r["attempt_number"],local_time(r["start_timestamp"]),
            local_time(r["end_timestamp"]),r["score"],r["rank_raw"],r["game_duration_raw"],r["elapsed_seconds"],r["status"],
            r["match_confidence"],bool(r["visible_in_latest"])) for r in rows])
    sheet("Diagnostyka importu",["Profil","Import (UTC)","SHA256","Zdarzenia","Status","Błąd","Uwagi"],
          [(r["ets_profile_id"],datetime.fromisoformat(r["imported_at"]),r["file_sha256"],r["event_count"],r["import_status"],
            r["error_message"],r["warnings_json"]) for r in snapshots if r["profile_id"] in allowed])
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Atomic replacement protects an existing report if Excel has it open or export fails.
    with tempfile.NamedTemporaryFile(dir=destination.parent,suffix=".xlsx",delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        workbook.save(temp_path)
        temp_path.replace(destination)
    finally:
        temp_path.unlink(missing_ok=True)
    logging.getLogger(__name__).info("Excel export completed")
    return destination
