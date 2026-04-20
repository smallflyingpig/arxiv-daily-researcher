"""
OpenReview 数据源

OpenReview 提供 ICLR、NeurIPS、ICML 等顶级 AI 会议的论文评审数据。
支持获取已录用论文、评审意见等。

API 文档: https://openreview.net/api
"""

import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base_source import BasePaperSource, PaperMetadata

logger = logging.getLogger(__name__)


class OpenReviewSource(BasePaperSource):
    """
    OpenReview 数据源实现。

    功能：
    - 获取 ICLR、NeurIPS、ICML 等顶会论文
    - 支持按年份、会议筛选
    - 可获取评审状态（accepted/rejected）
    """

    API_BASE_URL = "https://api.openreview.net"

    # 支持的会议
    SUPPORTED_VENUES = {
        "ICLR": {
            "2024": "ICLR.cc/2024/Conference",
            "2023": "ICLR.cc/2023/Conference",
            "2022": "ICLR.cc/2022/Conference",
        },
        "NeurIPS": {
            "2024": "NeurIPS.cc/2024/Conference",
            "2023": "NeurIPS.cc/2023/Conference",
        },
        "ICML": {
            "2024": "ICML.cc/2024/Conference",
            "2023": "ICML.cc/2023/Conference",
        },
        "ACL": {
            "2024": "ACL.cc/2024/Conference",
        },
    }

    def __init__(
        self,
        history_dir: Path,
        max_results: int = 100,
        api_key: Optional[str] = None,
    ):
        """
        初始化 OpenReview 数据源。

        参数:
            history_dir: 历史记录存储目录
            max_results: 最大结果数
            api_key: OpenReview API Key（可选）
        """
        super().__init__("openreview", history_dir)

        self.max_results = max_results
        self.api_key = api_key

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArxivDailyResearcher/3.0 (https://github.com/yzr278892/arxiv-daily-researcher)"
        })

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
            logger.info("[OpenReview] 已启用 API Key")
        else:
            logger.info("[OpenReview] 使用公共 API")

    @property
    def display_name(self) -> str:
        return "OpenReview (AI Conference Papers)"

    def can_download_pdf(self) -> bool:
        """OpenReview 提供 PDF 链接"""
        return True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.session:
            self.session.close()
            logger.debug("[OpenReview] Session 已关闭")

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
            if resp.status_code in (404, 403):
                return resp
            resp.raise_for_status()
            return resp

        try:
            return _do_get()
        except Exception as e:
            logger.warning(f"[OpenReview] API 请求失败: {e}")
            return None

    def fetch_papers(self, days: int, **kwargs) -> List[PaperMetadata]:
        """
        搜索最近 N 天的会议论文。

        参数:
            days: 搜索最近 N 天
            venues: 会议列表（如 ["ICLR", "NeurIPS"]）
            years: 年份列表（如 [2024, 2023]）
            accepted_only: 只获取已录用论文

        返回:
            List[PaperMetadata]: 论文列表
        """
        venues = kwargs.get("venues", ["ICLR", "NeurIPS"])
        years = kwargs.get("years", [datetime.now().year])
        accepted_only = kwargs.get("accepted_only", True)

        logger.info(f"[OpenReview] 开始搜索会议论文")
        logger.info(f"  会议: {venues}")
        logger.info(f"  年份: {years}")
        logger.info(f"  只获取已录用: {accepted_only}")

        papers = []

        for venue in venues:
            for year in years:
                venue_id = self.SUPPORTED_VENUES.get(venue, {}).get(str(year))
                if not venue_id:
                    logger.warning(f"[OpenReview] 不支持 {venue} {year}")
                    continue

                venue_papers = self._fetch_venue_papers(venue_id, venue, year, accepted_only)
                papers.extend(venue_papers)

        # 过滤已处理的论文
        new_papers = []
        for paper in papers:
            if not self.is_processed(paper.paper_id):
                new_papers.append(paper)
            else:
                logger.debug(f"[OpenReview] 跳过已处理: {paper.paper_id}")

        logger.info(f"[OpenReview] 发现 {len(new_papers)} 篇新论文")

        return new_papers[:self.max_results]

    def _fetch_venue_papers(
        self,
        venue_id: str,
        venue_name: str,
        year: int,
        accepted_only: bool,
    ) -> List[PaperMetadata]:
        """获取特定会议的论文"""

        url = f"{self.API_BASE_URL}/notes"
        params = {
            "content.venueid": venue_id,
            "details": "replyCount,writable",
            "limit": self.max_results,
        }

        # 如果只获取已录用论文
        if accepted_only:
            params["content.venue"] = f"{venue_name} {year} Conference"

        response = self._api_get(url, params)
        if not response or response.status_code != 200:
            logger.warning(f"[OpenReview] 获取 {venue_name} {year} 失败")
            return []

        try:
            data = response.json()
        except Exception as e:
            logger.warning(f"[OpenReview] 解析 JSON 失败: {e}")
            return []

        return self._parse_notes(data.get("notes", []), venue_name, year)

    def _parse_notes(
        self,
        notes: List[Dict],
        venue_name: str,
        year: int,
    ) -> List[PaperMetadata]:
        """解析 OpenReview notes 为 PaperMetadata"""

        papers = []
        for note in notes:
            try:
                paper = self._parse_note_item(note, venue_name, year)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"[OpenReview] 解析论文失败: {e}")
                continue

        return papers

    def _parse_note_item(
        self,
        note: Dict,
        venue_name: str,
        year: int,
    ) -> Optional[PaperMetadata]:
        """解析单个 note 数据"""

        note_id = note.get("id")
        if not note_id:
            return None

        content = note.get("content", {})

        # 获取标题
        title = content.get("title", "")
        if not title:
            title = content.get("Title", "")
        if not title:
            return None

        # 解析作者
        authors = content.get("authors", [])
        if not authors:
            authors_field = content.get("authors", {})
            if isinstance(authors_field, dict):
                authors = authors_field.get("value", [])

        # 解析摘要
        abstract = content.get("abstract", "")
        if not abstract:
            abstract = content.get("Abstract", "")
            if isinstance(abstract, dict):
                abstract = abstract.get("value", "")

        # 发布日期
        cdate = note.get("cdate")
        if cdate:
            try:
                # OpenReview 使用毫秒时间戳
                published_date = datetime.fromtimestamp(cdate / 1000)
            except:
                published_date = datetime(year, 1, 1)
        else:
            published_date = datetime(year, 1, 1)

        # URL
        url = f"https://openreview.net/forum?id={note_id}"

        # PDF URL
        pdf_url = None
        pdf = content.get("pdf")
        if pdf:
            if isinstance(pdf, dict):
                pdf_url = pdf.get("value")
            else:
                pdf_url = pdf
        elif note.get("pdf"):
            pdf_url = note.get("pdf")

        # 如果 PDF 是相对路径，补充完整 URL
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = f"https://openreview.net{pdf_url}"

        # arXiv ID
        arxiv_id = None
        arxiv_url = None
        venue_str = content.get("venue", "")
        if isinstance(venue_str, str) and "arXiv" in venue_str:
            # 尝试提取 arXiv ID
            import re
            match = re.search(r"arxiv\.org/(abs|pdf)/([0-9.]+)", venue_str)
            if match:
                arxiv_id = match.group(2)
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

        return PaperMetadata(
            paper_id=f"openreview-{note_id}",
            title=title,
            authors=authors if isinstance(authors, list) else [],
            abstract=abstract if isinstance(abstract, str) else "",
            published_date=published_date,
            url=url,
            source="openreview",
            pdf_url=pdf_url,
            doi=None,
            journal=f"{venue_name} {year}",
            categories=["AI", "ML"],
            semantic_scholar_tldr=None,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )