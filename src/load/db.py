# Shared connection helper for Step 4's Load stage. Credentials come from
# .env (gitignored; copy .env.example to get started) rather than being
# hardcoded, so the same code works against the docker-compose Postgres
# locally or a different instance later without editing source.

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():

    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
