"""Generate reviewable local sample report and verify the packaged GUI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from config import Config
from database.repository import Repository
from monitoring.importer import Importer
from reports.excel_export import export_excel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("--exe",type=Path)
    args = parser.parse_args()
    folder = ROOT/"data"/"verification"
    folder.mkdir(parents=True,exist_ok=True)
    config_path = folder/"config.json"
    Config(data_dir=str(folder)).save(config_path)
    source = args.source.resolve()
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    repo = Repository(folder/"academy.db")
    profiles = repo.profiles()
    pid = profiles[0]["id"] if profiles else repo.add_profile(repo.add_user("Próbka referencyjna"),"Zapis testowy",str(source))
    first = Importer(repo).import_file(pid)
    second = Importer(repo).import_file(pid)
    assert second.duplicate
    report = export_excel(repo,folder/"Academy-przyklad.xlsx")
    from openpyxl import load_workbook
    workbook = load_workbook(report)
    assert workbook["Historia prób"].max_row == len(repo.attempts())+1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    summary = {"source_sha256_unchanged":original_hash,"attempts":len(repo.attempts()),
               "scenarios":len({r["scenario_code"] for r in repo.attempts()}),
               "duplicate_import":second.duplicate,"report":str(report)}
    if args.exe:
        env = dict(os.environ,QT_QPA_PLATFORM="offscreen")
        run = subprocess.run([str(args.exe.resolve()),"--config",str(config_path),"--smoke-test"],env=env,timeout=30)
        summary["exe_exit_code"] = run.returncode
        assert run.returncode == 0
    (folder/"result.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(summary,indent=2,ensure_ascii=False))


if __name__ == "__main__":
    main()
