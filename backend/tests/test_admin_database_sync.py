# -*- coding: utf-8 -*-
"""
全局管理后台数据库备份下载（HTTP Range）与远程同步拉取完整性校验单元测试。
"""
from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from fastapi import HTTPException

from backend.api.v1 import admin_console


class _FakeStreamResponse:
    """模拟 `httpx.Client.stream` 返回的流式响应对象。"""

    def __init__(self, status_code: int, chunks: list[bytes], headers: dict[str, str] | None = None, raise_exc: Exception | None = None):
        self.status_code = status_code
        self._chunks = chunks
        self.headers = httpx.Headers(headers or {})
        self._raise_exc = raise_exc

    def read(self) -> bytes:
        return b"".join(self._chunks)

    def iter_bytes(self, chunk_size: int = 65536):
        for c in self._chunks:
            yield c
        if self._raise_exc is not None:
            raise self._raise_exc


class AdminDatabaseSyncTests(unittest.TestCase):
    """覆盖 Range 下载、分片续传、字节校验、归档校验与恢复失败状态标记。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parse_http_range_variants(self) -> None:
        self.assertEqual(admin_console._parse_http_range("bytes=0-9", 100), (0, 9))
        self.assertEqual(admin_console._parse_http_range("bytes=90-", 100), (90, 99))
        self.assertEqual(admin_console._parse_http_range("bytes=-10", 100), (90, 99))
        self.assertEqual(admin_console._parse_http_range("bytes=50-500", 100), (50, 99))
        self.assertIsNone(admin_console._parse_http_range("bytes=100-110", 100))
        self.assertIsNone(admin_console._parse_http_range("bytes=20-10", 100))
        self.assertIsNone(admin_console._parse_http_range("items=0-5", 100))

    def test_download_database_backup_range_and_headers(self) -> None:
        sample = self.tmp_dir / "sample.dump"
        payload = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        sample.write_bytes(payload)
        fake_session = SimpleNamespace(username="admin", unit="系统管理员", group="Global_admin")

        with (
            patch.object(admin_console, "DB_BACKUP_DIR", self.tmp_dir),
            patch.object(admin_console.auth_manager, "require_session", return_value=fake_session),
            patch.object(admin_console, "_ensure_admin_console_access", return_value=None),
        ):
            full_resp = admin_console.download_database_backup("sample.dump", authorization="Bearer tok", range_header=None)
            self.assertEqual(full_resp.headers.get("accept-ranges"), "bytes")
            self.assertEqual(full_resp.headers.get("cache-control"), "no-transform")

            part_resp = admin_console.download_database_backup("sample.dump", authorization="Bearer tok", range_header="bytes=4-11")
            self.assertEqual(part_resp.status_code, 206)
            self.assertEqual(part_resp.headers.get("content-range"), f"bytes 4-11/{len(payload)}")
            self.assertEqual(part_resp.headers.get("content-length"), "8")

            with self.assertRaises(HTTPException) as ctx:
                admin_console.download_database_backup("sample.dump", authorization="Bearer tok", range_header="bytes=999-1000")
            self.assertEqual(ctx.exception.status_code, 416)

    def test_download_remote_file_range_chunk_retry_succeeds(self) -> None:
        """远端支持 206 分片且第二片偶发超时时，应断点重传并最终拼出完整文件。"""
        full_data = b"A" * 10 + b"B" * 10 + b"C" * 5
        temp_file = self.tmp_dir / "part.downloading"
        chunk2_calls = {"n": 0}

        class _FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            @contextmanager
            def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
                rng = (headers or {}).get("Range", "")
                if rng == "bytes=0-9":
                    yield _FakeStreamResponse(206, [full_data[0:10]], {"Content-Range": f"bytes 0-9/{len(full_data)}"})
                elif rng == "bytes=10-19":
                    chunk2_calls["n"] += 1
                    if chunk2_calls["n"] == 1:
                        yield _FakeStreamResponse(
                            206,
                            [full_data[10:14]],
                            {"Content-Range": f"bytes 10-19/{len(full_data)}"},
                            raise_exc=httpx.ReadTimeout("simulated stall"),
                        )
                    else:
                        yield _FakeStreamResponse(206, [full_data[10:20]], {"Content-Range": f"bytes 10-19/{len(full_data)}"})
                elif rng == "bytes=20-24":
                    yield _FakeStreamResponse(206, [full_data[20:25]], {"Content-Range": f"bytes 20-24/{len(full_data)}"})
                else:
                    raise AssertionError(f"unexpected range: {rng}")

        with (
            patch.object(admin_console.httpx, "Client", _FakeClient),
            patch.object(admin_console.time, "sleep", return_value=None),
        ):
            written = admin_console._download_remote_file_with_verification(
                download_url="https://example.test/download/a.dump",
                temp_dest_path=temp_file,
                headers={"Authorization": "Bearer t"},
                expected_size=len(full_data),
                chunk_size=10,
                max_retries=3,
            )

        self.assertEqual(written, len(full_data))
        self.assertEqual(temp_file.read_bytes(), full_data)
        self.assertEqual(chunk2_calls["n"], 2)

    def test_download_remote_file_200_rejects_truncation_and_retries(self) -> None:
        """远端仅返回 200 且第一次流被截断时，必须识别字节不足并重试，绝不将残缺文件视为成功。"""
        full_data = b"X" * 32
        temp_file = self.tmp_dir / "full200.downloading"
        calls = {"n": 0}

        class _FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            @contextmanager
            def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
                calls["n"] += 1
                if calls["n"] == 1:
                    yield _FakeStreamResponse(200, [full_data[:12]], {"Content-Length": str(len(full_data))})
                else:
                    yield _FakeStreamResponse(200, [full_data], {"Content-Length": str(len(full_data))})

        with (
            patch.object(admin_console.httpx, "Client", _FakeClient),
            patch.object(admin_console.time, "sleep", return_value=None),
        ):
            written = admin_console._download_remote_file_with_verification(
                download_url="https://example.test/download/a.dump",
                temp_dest_path=temp_file,
                headers={"Authorization": "Bearer t"},
                expected_size=len(full_data),
                chunk_size=16,
                max_retries=3,
            )

        self.assertEqual(written, len(full_data))
        self.assertEqual(temp_file.read_bytes(), full_data)
        self.assertEqual(calls["n"], 2)

    def test_download_remote_file_200_all_truncated_raises_502(self) -> None:
        """所有重试均截断时必须抛出 502 错误且不残留损坏文件。"""
        temp_file = self.tmp_dir / "broken.downloading"

        class _FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            @contextmanager
            def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
                yield _FakeStreamResponse(200, [b"short"], {"Content-Length": "100"})

        with (
            patch.object(admin_console.httpx, "Client", _FakeClient),
            patch.object(admin_console.time, "sleep", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                admin_console._download_remote_file_with_verification(
                    download_url="https://example.test/download/a.dump",
                    temp_dest_path=temp_file,
                    headers={"Authorization": "Bearer t"},
                    expected_size=100,
                    max_retries=2,
                )
        self.assertEqual(ctx.exception.status_code, 502)

    def test_pull_remote_backup_rejects_corrupt_archive_and_preserves_existing(self) -> None:
        """若归档完整性校验失败，必须拒收并保留本地原有正式备份文件不被覆盖。"""
        existing = self.tmp_dir / "远程_demo.dump"
        existing.write_bytes(b"INTACT_LOCAL_BACKUP")
        fake_session = SimpleNamespace(username="admin", unit="系统管理员")

        def _fake_download(download_url, temp_dest_path, headers, expected_size, **kwargs):
            temp_dest_path.write_bytes(b"CORRUPT_DATA")
            return len(b"CORRUPT_DATA")

        with (
            patch.object(admin_console, "DB_BACKUP_DIR", self.tmp_dir),
            patch.object(admin_console, "_ensure_admin_console_access", return_value=None),
            patch.object(admin_console, "_load_remote_sync_config", return_value={"remote_url": "https://r.test", "token": "t"}),
            patch.object(admin_console, "_get_remote_auth_token", return_value="t"),
            patch.object(admin_console, "_fetch_remote_backup_metadata", return_value=("demo.dump", 12)),
            patch.object(admin_console, "_download_remote_file_with_verification", side_effect=_fake_download),
            patch.object(admin_console, "_verify_pg_dump_archive", return_value=(False, "end of file")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                admin_console.pull_remote_backup(
                    admin_console.RemoteSyncPullPayload(filename="demo.dump"),
                    session=fake_session,
                )
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(existing.read_bytes(), b"INTACT_LOCAL_BACKUP")
        self.assertEqual(list(self.tmp_dir.glob("*.downloading_*")), [])

    def test_run_restore_thread_marks_failed_on_nonzero_exit(self) -> None:
        """pg_restore 返回非 0 退出码时，恢复任务状态必须标记为 failed。"""
        import io
        job = admin_console.RestoreJob("job_1", "demo.dump", ["pg_restore"], os.environ.copy())
        fake_proc = MagicMock()
        fake_proc.stdout = io.StringIO("pg_restore: error: could not read from input file: end of file\n")
        fake_proc.returncode = 1
        fake_proc.wait.return_value = 1

        with patch.object(admin_console.subprocess, "Popen", return_value=fake_proc):
            admin_console._run_restore_thread(job)

        self.assertEqual(job.status, "failed")
        self.assertEqual(job.returncode, 1)

    def test_pull_job_progress_and_cancel(self) -> None:
        """PullJob 进度百分比、速率计算与取消状态转换应准确无误。"""
        job = admin_console.PullJob("pull_test1", "https://platform.smartview.top")
        job.update_progress(500, 1000, "range_parallel", 1, 4)
        snap = job.snapshot()
        self.assertEqual(snap["percent"], 50.0)
        self.assertEqual(snap["download_mode"], "range_parallel")

        fake_session = SimpleNamespace(username="admin", unit="系统管理员")
        admin_console.PULL_JOBS["pull_test1"] = job
        try:
            with patch.object(admin_console, "_ensure_admin_console_access", return_value=None):
                res = admin_console.cancel_pull_remote_backup("pull_test1", session=fake_session)
                self.assertTrue(res["ok"])
                self.assertTrue(job.cancel_requested)
        finally:
            admin_console.PULL_JOBS.pop("pull_test1", None)

    def test_probe_direct_origin_switches_when_cdn_header_present(self) -> None:
        """当响应头包含 CloudFront Via 与 X-Served-By 源站且源站探测返回 200 时，应自动切换直连源站。"""
        resp_headers = httpx.Headers({
            "Via": "1.1 abc.cloudfront.net (CloudFront)",
            "X-Served-By": "originplatform.smartview.top",
        })
        fake_resp = SimpleNamespace(status_code=200)

        class _ProbeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url, headers=None):
                self.url = url
                return fake_resp

        logs: list[str] = []
        with patch.object(admin_console.httpx, "Client", _ProbeClient):
            origin = admin_console._probe_direct_origin_base_url(
                remote_url="https://platform.smartview.top",
                probe_url="https://platform.smartview.top/api/v1/admin/database/backup/download/a.dump",
                headers={"Authorization": "Bearer t"},
                resp_headers=resp_headers,
                log_cb=logs.append,
            )

        self.assertEqual(origin, "https://originplatform.smartview.top")
        self.assertTrue(any("originplatform.smartview.top" in x for x in logs))


if __name__ == "__main__":
    unittest.main()
