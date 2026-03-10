"""
任务并发锁 — 防止完全相同的任务同时执行。

使用文件独占锁（fcntl.LOCK_EX | LOCK_NB），进程退出后锁自动释放。

锁文件目录：data/run/
  daily_research.lock                — 每日研究（同时只允许一个）
  trend_research_<params_hash>.lock  — 趋势研究（相同参数同时只允许一个）
"""

import fcntl
import hashlib
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def _lock_dir() -> Path:
    try:
        from config import settings

        d = Path(settings.DATA_DIR) / "run"
    except Exception:
        d = Path("data/run")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _params_hash(
    keywords: List[str],
    date_from,
    date_to,
    categories: Optional[List[str]],
) -> str:
    key = "|".join(
        [
            ",".join(sorted(str(k) for k in keywords)),
            str(date_from),
            str(date_to),
            ",".join(sorted(str(c) for c in (categories or []))),
        ]
    )
    return hashlib.md5(key.encode()).hexdigest()[:8]


@contextmanager
def run_lock(
    mode: str,
    keywords: Optional[List[str]] = None,
    date_from=None,
    date_to=None,
    categories: Optional[List[str]] = None,
):
    """
    获取运行锁；若相同任务已在运行则打印提示并以 exit(0) 退出。

    用法:
        with run_lock("daily_research"):
            DailyResearchPipeline().run()

        with run_lock("trend_research", keywords=[...], date_from=..., date_to=..., categories=[...]):
            TrendResearchPipeline(...).run()
    """
    if mode == "trend_research" and keywords:
        h = _params_hash(keywords, date_from, date_to, categories)
        fname = f"trend_research_{h}.lock"
        task_desc = f"trend_research [keywords={keywords}, {date_from}~{date_to}"
        if categories:
            task_desc += f", categories={categories}"
        task_desc += "]"
    else:
        fname = f"{mode}.lock"
        task_desc = mode

    lock_path = _lock_dir() / fname
    lock_file = open(lock_path, "a+")

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        try:
            lock_file.seek(0)
            info = lock_file.read().strip()
        except Exception:
            info = ""
        lock_file.close()

        print(f"\n⚠️  相同任务正在运行中，跳过本次执行")
        print(f"   任务: {task_desc}")
        if info:
            print(f"   运行信息: {info}")
        print(f"   锁文件: {lock_path}\n")
        sys.exit(0)

    # 写入诊断信息方便排查
    try:
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(
            f"PID={os.getpid()}, started={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lock_file.flush()
    except Exception:
        pass

    try:
        yield
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass
