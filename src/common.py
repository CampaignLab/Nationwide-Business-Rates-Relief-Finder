"""Shared paths, logging and stage bookkeeping for the pipeline."""
import json
import logging
import sys
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
OUT = ROOT / "out"
CONFIG = ROOT / "config"
MAPPING = ROOT / "mapping"

WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)


def get_logger(stage: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger(stage)


def load_rules() -> dict:
    with open(CONFIG / "rules.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET temp_directory = '{WORK / 'duckdb_tmp'}'")
    return con


def write_stage_log(stage: str, rows_in: int | None, rows_out: int, **extra) -> None:
    """Record row counts for the run report. Overwrites the stage's previous log."""
    record = {"stage": stage, "rows_in": rows_in, "rows_out": rows_out, **extra}
    with open(WORK / f"stage_{stage}.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str)


def read_stage_log(stage: str) -> dict:
    with open(WORK / f"stage_{stage}.json", encoding="utf-8") as f:
        return json.load(f)


def count(con: duckdb.DuckDBPyConnection, relation: str) -> int:
    return con.execute(f"SELECT count(*) FROM {relation}").fetchone()[0]


def sql_path(path: Path) -> str:
    return str(path).replace("'", "''")
