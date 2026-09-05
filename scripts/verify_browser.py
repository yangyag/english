"""Run real UI tests against a disposable local PostgreSQL database."""
import os
import argparse
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from time import monotonic, sleep
from uuid import uuid4
from datetime import date, timedelta

parser = argparse.ArgumentParser()
parser.add_argument('--preview', action='store_true', help='Keep a local demo API running on port 8090 for Docker preview')
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
stop_file = ROOT / '.cache' / 'english-preview.stop'
if args.preview:
    stop_file.parent.mkdir(exist_ok=True)
    stop_file.unlink(missing_ok=True)
sys.path.insert(0, str(ROOT / 'back'))
from local_testing import configure_local
configure_local()
from app.config import get_settings
from sqlalchemy import create_engine

admin = create_engine(get_settings().database_url, isolation_level='AUTOCOMMIT')
database = 'english_test_browser_' + uuid4().hex
with admin.connect() as conn:
    conn.exec_driver_sql(f'CREATE DATABASE "{database}"')
os.environ['PGDATABASE'] = database
os.environ['ENGLISH_API_TARGET'] = 'http://127.0.0.1:18090'
get_settings.cache_clear()

from app.db import SessionLocal, engine, init_db
from app.models import Word
from app.schemas import SubmitIn
from app.study import submit
from app.main import app
from app.clock import get_today
import uvicorn

server = None
thread = None
try:
    init_db()
    demo_today = get_today() if args.preview else date(2026, 9, 5)
    previous_day = demo_today - timedelta(days=2)
    vocabulary = ['begin', 'wander', 'quiet', 'bloom', 'gentle', 'notice', 'gather', 'belong', 'wonder', 'steady',
                  'bright', 'journey', 'little', 'enough', 'simple', 'listen', 'create', 'discover', 'remember', 'grow',
                  'interconnectedness', 'thoughtful', 'curiosity', 'delight', 'breathe', 'patient', 'embrace', 'imagine', 'reflect', 'hope',
                  'tomorrow', 'kindness', 'peaceful', 'treasure', 'continue']
    with SessionLocal.begin() as db:
        for rank, word in enumerate(vocabulary, 1):
            db.add(Word(rank=rank, word=word, meaning='서로 연결되어 있음; 상호 연결성' if rank == 21 else '기억하고 싶은 단어',
                        example=('The interconnectedness of small everyday choices reminds us that learning grows through patient practice, curiosity, and the willingness to begin again, even after a long pause.' if rank == 21 else f'I want to {word} in my own way.'),
                        example_ko='작은 일상의 선택들은 서로 연결되어 있고, 잠시 쉬었더라도 다시 시작하는 마음과 꾸준한 연습이 배움을 키워 준다.'))
        db.flush()
        for start in (1, 11):
            submit(db, previous_day, SubmitIn(request_id=uuid4(), study_date=previous_day,
                results=[dict(rank=i, known=True) for i in range(start, start + 10)]), 'new')
    if not args.preview:
        app.dependency_overrides[get_today] = lambda: demo_today
    server = uvicorn.Server(uvicorn.Config(app, host='0.0.0.0' if args.preview else '127.0.0.1',
                                          port=8090 if args.preview else 18090, log_level='warning'))
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    deadline = monotonic() + 20
    while not server.started:
        if not thread.is_alive() or monotonic() > deadline:
            raise RuntimeError('Browser fixture server failed to start')
        sleep(.1)
    if args.preview:
        (ROOT / '.cache' / 'english-preview.json').write_text(
            json.dumps(dict(pid=os.getpid(), database=database, port=8090)), encoding='utf-8')
        while thread.is_alive() and not stop_file.exists():
            sleep(1)
    else:
        result = subprocess.run(['npx.cmd' if os.name == 'nt' else 'npx', 'playwright', 'test'], cwd=ROOT / 'front')
finally:
    if server:
        server.should_exit = True
    if thread:
        thread.join(timeout=10)
    engine.dispose()
    with admin.connect() as conn:
        conn.exec_driver_sql(f'DROP DATABASE "{database}" WITH (FORCE)')
    admin.dispose()
sys.exit(0 if args.preview else result.returncode)
