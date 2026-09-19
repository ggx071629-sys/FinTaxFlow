"""Run only after backup, with API stopped. Default is rolled-back DB preview."""
import argparse
import json
from app.db import SessionLocal
from app.services.demo_identity_migration import migrate_demo_identities

parser = argparse.ArgumentParser()
parser.add_argument('--apply',action='store_true')
args = parser.parse_args()
with SessionLocal() as db:
    result = migrate_demo_identities(db,write_files=args.apply)
    if args.apply: db.commit()
    else: db.rollback()
print(json.dumps({'applied':args.apply,'changes':result},ensure_ascii=False))
