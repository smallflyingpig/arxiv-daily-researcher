"""
DBLP 数据源

DBLP 是计算机科学领域的权威文献索引数据库。
支持按关键词搜索论文，无需 API Key。

API 文档: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
"""

import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base_source import BasePaperSource, PaperMetadata

logger = logging.getLogger(__name__)


class DBLPSource(BasePaperSource):
    """
    DBLP 数据源实现。

    功能：
    - 按关键词搜索 CS 论文
    - 支持按时间范围筛选
    - 覆盖期刊、会议、预印本
    """

    API_BASE_URL = "https://dblp.org/search"

    # DBLP 支持的搜索类型
    SEARCH_TYPES = ["publ", "author", "venue"]

    def __init__(
        self,
        history_dir: Path,
        max_results: int = 100,
    ):
        """
        初始化 DBLP 数据源。

        参数:
            history_dir: 历史记录存储目录
            max_results: 最大结果数
        """
        super().__init__("dblp", history_dir)

        self.max_results = max_results

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArxivDailyResearcher/3.0 (https://github.com/yzr278892/arxiv-daily-researcher)"
        })

        logger.info("[DBLP] 已启用数据源（无需 API Key）")

    @property
    def display_name(self) -> str:
        return "DBLP (Computer Science Bibliography)"

    def can_download_pdf(self) -> bool:
        """DBLP 本身不提供 PDF，但可能链接到 arXiv"""
        return False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.session:
            self.session.close()
            logger.debug("[DBLP] Session 已关闭")

    def _api_get(
        self, url: str, params: dict, timeout: int = 30
    ) -> Optional[requests.Response]:
        """发送 API GET 请求，带自动重试"""
        from config import settings as _settings

        @retry(
            stop=stop_after_attempt(_settings.RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(min=_settings.RETRY_MIN_WAIT, max=_settings.RETRY_MAX_WAIT),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _do_get():
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp

        try:
            return _do_get()
        except Exception as e:
            logger.warning(f"[DBLP] API 请求失败: {e}")
            return None

    def fetch_papers(self, days: int, **kwargs) -> List[PaperMetadata]:
        """
        搜索最近 N 天的论文。

        参数:
            days: 搜索最近 N 天
            keywords: 搜索关键词列表

        返回:
            List[PaperMetadata]: 论文列表
        """
        keywords = kwargs.get("keywords", [])

        if not keywords:
            logger.warning("[DBLP] 未提供关键词，无法搜索")
            return []

        logger.info(f"[DBLP] 开始搜索论文")
        logger.info(f"  关键词: {keywords}")
        logger.info(f"  时间范围: 最近 {days} 天")

        papers = []

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        for keyword in keywords:
            keyword_papers = self._search_by_keyword(keyword, start_date, end_date)
            papers.extend(keyword_papers)

        # 过滤已处理的论文
        new_papers = []
        for paper in papers:
            if not self.is_processed(paper.paper_id):
                new_papers.append(paper)
            else:
                logger.debug(f"[DBLP] 跳过已处理: {paper.paper_id}")

        logger.info(f"[DBLP] 发现 {len(new_papers)} 篇新论文")

        return new_papers[:self.max_results]

    def _search_by_keyword(
        self,
        keyword: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[PaperMetadata]:
        """按关键词搜索论文"""

        # DBLP 搜索 API
        url = f"{self.API_BASE_URL}/publ/api"
        params = {
            "q": keyword,
            "format": "json",
            "h": self.max_results,  # 结果数量
        }

        response = self._api_get(url, params)
        if not response:
            return []

        try:
            data = response.json()
        except Exception as e:
            logger.warning(f"[DBLP] 解析 JSON 失败: {e}")
            return []

        return self._parse_search_results(
            data.get("result", {}).get("hits", {}).get("hit", []),
            start_date,
            end_date,
        )

    def _parse_search_results(
        self,
        hits: List[Dict],
        start_date: datetime,
        end_date: datetime,
    ) -> List[PaperMetadata]:
        """解析搜索结果为 PaperMetadata 列表"""

        papers = []
        for hit in hits:
            try:
                paper = self._parse_hit_item(hit, start_date, end_date)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"[DBLP] 解析论文失败: {e}")
                continue

        return papers

    def _parse_hit_item(
        self,
        hit: Dict,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[PaperMetadata]:
        """解析单个论文数据"""

        info = hit.get("info", {})
        if not info:
            return None

        # 获取标题
        title = info.get("title", "")
        if not title:
            return None

        # 获取 DBLP key 作为 paper_id
        key = info.get("key", "")
        if not key:
            return None

        # 解析作者
        authors_data = info.get("authors", {}).get("author", [])
        if isinstance(authors_data, dict):
            # 单作者情况
            authors = [authors_data.get("text", "")]
        else:
            authors = [a.get("text", "") for a in authors_data if isinstance(a, dict)]

        # 解析年份
        year = info.get("year")
        if year:
            try:
                year_int = int(year)
                published_date = datetime(year_int, 1, 1)

                # 时间范围过滤
                if published_date < start_date or published_date > end_date:
                    return None
            except:
                published_date = datetime.now()
        else:
            published_date = datetime.now()

        # 解析 URL
        url = info.get("url", f"https://dblp.org/rec/{key}")

        # 解析 DOI
        doi = info.get("doi")
        if isinstance(doi, list):
            doi = doi[0] if doi else None

        # 解析期刊/会议类型
        venue = info.get("venue", "")
        type_str = info.get("type", "")

        # 解析电子版链接（可能有 arXiv）
        ee = info.get("ee", "")
        if isinstance(ee, list):
            ee = ee[0] if ee else ""

        # 尝试提取 arXiv ID
        arxiv_id = None
        arxiv_url = None
        if ee:
            if "arxiv.org" in ee:
                # 从 URL 提取 arXiv ID
                try:
                    import re
                    match = re.search(r"arxiv\.org/(abs|pdf)/([0-9.]+|[^/]+)", ee)
                    if match:
                        arxiv_id = match.group(2)
                        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                except:
                    pass

        # 构建摘要（DBLP 通常不提供摘要）
        abstract = info.get("abstract", "")

        return PaperMetadata(
            paper_id=key,
            title=title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            url=url,
            source="dblp",
            pdf_url=None,
            doi=doi,
            journal=f"{venue} ({type_str})" if venue else None,
            categories=[],
            semantic_scholar_tldr=None,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )