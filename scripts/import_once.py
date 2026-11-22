import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.repository import Repository
from monitoring.importer import Importer


def main():
    parser = argparse.ArgumentParser(description="Import Academy do lokalnej bazy SQLite")
    parser.add_argument("source",type=Path)
    parser.add_argument("--database",type=Path,required=True)
    parser.add_argument("--user",default="Kursant")
    parser.add_argument("--profile",default="Profil ETS2")
    args = parser.parse_args()
    repo = Repository(args.database)
    source = str(args.source.resolve())
    profiles = repo.query("SELECT id FROM profiles WHERE source_path=? AND ets_profile_id=?",(source,args.profile))
    if profiles:
        pid = profiles[0]["id"]
    else:
        users = repo.query("SELECT id FROM users WHERE name=?",(args.user,))
        uid = users[0]["id"] if users else repo.add_user(args.user)
        pid = repo.add_profile(uid,args.profile,source)
    print(Importer(repo).import_file(pid))


if __name__ == "__main__":
    main()
