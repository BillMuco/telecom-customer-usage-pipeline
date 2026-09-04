from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_LOCAL_DELTA_ROOT = Path("data/delta")
DEFAULT_REMOTE_ROOT = "dbfs:/Volumes/<catalog>/<schema>/<volume>/telecom-customer-usage-pipeline/delta"
CHUNK_SIZE = 512 * 1024


class DatabricksClient:
    def __init__(self, host: str, token: str) -> None:
        self.host = host.rstrip("/")
        self.token = token

    def post(self, path: str, payload: dict) -> dict:
        url = f"{self.host}{path}"
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=60) as response:
                response_body = response.read().decode("utf-8")
                return json.loads(response_body) if response_body else {}
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Databricks API call failed: {path} {error.code} {details}") from error

    def put(self, path: str, data: bytes = b"", content_type: str = "application/json") -> None:
        url = f"{self.host}{path}"
        request = Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type,
            },
            method="PUT",
        )

        try:
            with urlopen(request, timeout=60) as response:
                response.read()
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Databricks API call failed: {path} {error.code} {details}") from error

    def mkdirs(self, dbfs_path: str) -> None:
        self.post("/api/2.0/dbfs/mkdirs", {"path": dbfs_path})

    def upload_file(self, local_path: Path, dbfs_path: str, overwrite: bool = True) -> None:
        create_response = self.post(
            "/api/2.0/dbfs/create",
            {"path": dbfs_path, "overwrite": overwrite},
        )
        handle = create_response["handle"]

        try:
            with local_path.open("rb") as file:
                while True:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.post(
                        "/api/2.0/dbfs/add-block",
                        {
                            "handle": handle,
                            "data": base64.b64encode(chunk).decode("ascii"),
                        },
                    )
        finally:
            self.post("/api/2.0/dbfs/close", {"handle": handle})

    def create_volume_directory(self, volume_path: str) -> None:
        path = quote(volume_path.rstrip("/") + "/", safe="/")
        self.put(f"/api/2.0/fs/directories{path}")

    def upload_volume_file(self, local_path: Path, volume_path: str, overwrite: bool = True) -> None:
        path = quote(volume_path, safe="/")
        query = "true" if overwrite else "false"
        self.put(
            f"/api/2.0/fs/files{path}?overwrite={query}",
            data=local_path.read_bytes(),
            content_type="application/octet-stream",
        )

    def execute_sql(
        self,
        warehouse_id: str,
        statement: str,
        catalog: str | None = None,
        schema: str | None = None,
    ) -> dict:
        payload: dict = {
            "warehouse_id": warehouse_id,
            "statement": statement,
            "wait_timeout": "30s",
            "on_wait_timeout": "CONTINUE",
        }
        if catalog:
            payload["catalog"] = catalog
        if schema:
            payload["schema"] = schema
        return self.post("/api/2.0/sql/statements", payload)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def should_upload(path: Path) -> bool:
    if path.name == ".gitkeep":
        return False
    if path.name == "_SUCCESS":
        return False
    if path.name.endswith(".crc"):
        return False
    return True


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and should_upload(path):
            yield path


def remote_join(root: str, relative_path: Path) -> str:
    clean_root = root.rstrip("/")
    parts = [part for part in relative_path.parts if part]
    return "/".join([clean_root, *parts]).replace("\\", "/")


def is_volume_path(path: str) -> bool:
    return path.startswith("dbfs:/Volumes/") or path.startswith("/Volumes/")


def to_volume_path(path: str) -> str:
    if path.startswith("dbfs:/Volumes/"):
        return path.removeprefix("dbfs:")
    return path


def find_delta_tables(root: Path, scope_root: Path, remote_root: str) -> list[tuple[str, str]]:
    tables: list[tuple[str, str]] = []

    for delta_log in sorted(scope_root.rglob("_delta_log")):
        table_dir = delta_log.parent
        relative_table_path = table_dir.relative_to(root)
        remote_table_path = remote_join(remote_root, relative_table_path)
        table_name = table_dir.name

        if "bronze" in relative_table_path.parts:
            table_name = f"bronze_{table_name}"
        elif "silver" in relative_table_path.parts:
            table_name = f"silver_{table_name}"

        tables.append((table_name, remote_table_path))

    return tables


def quote_identifier(identifier: str) -> str:
    return "`" + identifier.replace("`", "``") + "`"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload local Delta Lake tables to Databricks.")
    parser.add_argument("--env-file", default=".env", help="Optional .env file with Databricks settings.")
    parser.add_argument("--local-root", default=str(DEFAULT_LOCAL_DELTA_ROOT), help="Local Delta root folder.")
    parser.add_argument("--remote-root", default=None, help="Target remote root. Defaults to DATABRICKS_REMOTE_ROOT.")
    parser.add_argument("--scope", choices=["all", "bronze", "silver", "gold"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Show what would upload without calling Databricks.")
    parser.add_argument("--register-tables", action="store_true", help="Create SQL tables after upload.")
    args = parser.parse_args()

    load_dotenv(Path(args.env_file))

    local_root = Path(args.local_root)
    remote_root = args.remote_root or os.getenv("DATABRICKS_REMOTE_ROOT") or os.getenv("DATABRICKS_DBFS_ROOT", DEFAULT_REMOTE_ROOT)
    if "<" in remote_root or ">" in remote_root:
        raise ValueError(
            "Set DATABRICKS_REMOTE_ROOT to a real Unity Catalog volume path, "
            "for example dbfs:/Volumes/<catalog>/<schema>/<volume>/telecom-customer-usage-pipeline/delta."
        )
    if args.scope == "all":
        upload_root = local_root
    else:
        upload_root = local_root / args.scope

    if not upload_root.exists():
        raise FileNotFoundError(f"Delta folder not found: {upload_root}")

    files = list(iter_files(upload_root))
    if not files:
        raise ValueError(f"No uploadable files found under: {upload_root}")

    print(f"Local Delta root: {local_root}")
    print(f"Upload scope: {args.scope}")
    print(f"Databricks remote root: {remote_root}")
    print(f"Files to upload: {len(files)}")

    if args.dry_run:
        for path in files:
            print(f"DRY RUN: {path} -> {remote_join(remote_root, path.relative_to(local_root))}")
        tables = find_delta_tables(local_root, upload_root, remote_root)
        print(f"Delta tables found: {len(tables)}")
        for table_name, table_path in tables:
            print(f"DRY RUN TABLE: {table_name} LOCATION {table_path}")
        return

    host = os.getenv("DATABRICKS_HOST", "").strip()
    token = os.getenv("DATABRICKS_TOKEN", "").strip()
    if not host or not token:
        raise ValueError("Set DATABRICKS_HOST and DATABRICKS_TOKEN in .env or environment variables.")

    client = DatabricksClient(host, token)
    use_files_api = is_volume_path(remote_root)

    for path in files:
        relative_path = path.relative_to(local_root)
        target_path = remote_join(remote_root, relative_path)
        target_dir = target_path.rsplit("/", 1)[0]
        if use_files_api:
            client.create_volume_directory(to_volume_path(target_dir))
            client.upload_volume_file(path, to_volume_path(target_path))
        else:
            client.mkdirs(target_dir)
            client.upload_file(path, target_path)
        print(f"Uploaded: {relative_path} -> {target_path}")

    should_register = args.register_tables or os.getenv("DATABRICKS_REGISTER_TABLES", "").lower() == "true"
    if not should_register:
        print("Upload complete. SQL table registration skipped.")
        return

    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "").strip()
    if not warehouse_id:
        raise ValueError("Set DATABRICKS_WAREHOUSE_ID before registering SQL tables.")

    catalog = os.getenv("DATABRICKS_SQL_CATALOG", "").strip() or None
    schema = os.getenv("DATABRICKS_SQL_SCHEMA", "telecom_customer_usage").strip()

    if catalog:
        client.execute_sql(warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(catalog)}.{quote_identifier(schema)}")
    else:
        client.execute_sql(warehouse_id, f"CREATE DATABASE IF NOT EXISTS {quote_identifier(schema)}")

    for table_name, table_path in find_delta_tables(local_root, upload_root, remote_root):
        identifier = f"{quote_identifier(schema)}.{quote_identifier(table_name)}"
        if catalog:
            identifier = f"{quote_identifier(catalog)}.{identifier}"
        table_location = to_volume_path(table_path) if is_volume_path(table_path) else table_path
        statement = f"CREATE TABLE IF NOT EXISTS {identifier} USING DELTA LOCATION '{table_location}'"
        client.execute_sql(warehouse_id, statement, catalog=catalog, schema=schema)
        print(f"Registered SQL table: {identifier} -> {table_path}")

    print("Upload and SQL registration complete.")


if __name__ == "__main__":
    main()
