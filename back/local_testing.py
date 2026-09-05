"""Local test database helpers; never imported by the production application."""
import json
import os
import subprocess
import atexit
from uuid import uuid4
from pathlib import Path


def configure_local():
    os.environ['PGHOST'] = '127.0.0.1'
    os.environ['PGPORT'] = '5432'
    os.environ['PGSCHEMA'] = 'english'
    # Fresh workspaces may have no .env. Reuse credentials internally from
    # the already-running local Postgres container; do not print or save them.
    if not Path(__file__).resolve().parents[1].joinpath('.env').exists() and not os.environ.get('PGPASSWORD'):
        container = os.environ.get('ENGLISH_TEST_POSTGRES_CONTAINER', 'yangyag-postgres')
        info = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True))[0]
        env = dict(item.split('=', 1) for item in info['Config']['Env'] if '=' in item)
        if env.get('POSTGRES_PASSWORD'):
            os.environ['PGUSER'] = env.get('POSTGRES_USER', 'postgres')
            os.environ['PGPASSWORD'] = env['POSTGRES_PASSWORD']
            os.environ['PGDATABASE'] = env.get('POSTGRES_DB', os.environ['PGUSER'])
        else:
            role = 'english_test_' + uuid4().hex
            password = uuid4().hex
            command = ['docker', 'exec', '-i', container, 'psql', '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1']
            subprocess.run(command, input=f"CREATE ROLE {role} LOGIN CREATEDB PASSWORD '{password}';", text=True, check=True, capture_output=True)
            os.environ['PGUSER'] = role
            os.environ['PGPASSWORD'] = password
            os.environ['PGDATABASE'] = 'postgres'
            atexit.register(lambda: subprocess.run(command, input=f'DROP ROLE IF EXISTS {role};', text=True, capture_output=True))
