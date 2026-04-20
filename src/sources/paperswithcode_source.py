"""
Papers with Code 数据源

Papers with Code 提供 ML 论文与代码实现的关联数据。
支持按关键词、任务、方法搜索论文。

API 文档: https://paperswithcode.com/api/v1/
"""

import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base_source import BasePaperSource, PaperMetadata

logger = logging.getLogger(__name__)


class PapersWithCodeSource(BasePaperSource):
    """
    Papers with Code 数据源实现。

    功能：
    - 搜索 ML 论文
    - 获取论文关联的代码仓库
    - 支持按任务、方法、数据集筛选
    """

    API_BASE_URL = "https://paperswithcode.com/api/v1"

    def __init__(
        self,
        history_dir: Path,
        max_results: int = 100,
    ):
        """
        初始化 Papers with Code 数据源。

        参数:
            history_dir: 历史记录存储目录
            max_results: 最大结果数
        """
        super().__init__("paperswithcode", history_dir)

        self.max_results = max_results

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArxivDailyResearcher/3.0 (https://github.com/yzr278892/arxiv-daily-researcher)"
        })

        logger.info("[PapersWithCode] 已启用数据源（公开 API，无需 Key）")

    @property
    def display_name(self) -> str:
        return "Papers with Code"

    def can_download_pdf(self) -> bool:
        """通过 arXiv ID 可以获取 PDF"""
        return True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.session:
            self.session.close()
            logger.debug("[PapersWithCode] Session 已关闭")

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
            logger.warning(f"[PapersWithCode] API 请求失败: {e}")
            return None
            logger.warning(f"[PapersWithCode] API 请求失败: {e}")
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

        logger.info(f"[PapersWithCode] 开始搜索论文")
        logger.info(f"  关键词: {keywords if keywords else '无'}")
        logger.info(f"  时间范围: 最近 {days} 天")

        papers = []

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        if keywords:
            for keyword in keywords:
                keyword_papers = self._search_by_keyword(keyword, start_date, end_date)
                papers.extend(keyword_papers)
        else:
            # 无关键词时获取最新论文
            papers = self._search_latest(start_date, end_date)

        # 过滤已处理的论文
        new_papers = []
        for paper in papers:
            if not self.is_processed(paper.paper_id):
                new_papers.append(paper)
            else:
                logger.debug(f"[PapersWithCode] 跳过已处理: {paper.paper_id}")

        logger.info(f"[PapersWithCode] 发现 {len(new_papers)} 篇新论文")

        return new_papers[:self.max_results]

    def _search_by_keyword(
        self,
        keyword: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[PaperMetadata]:
        """按关键词搜索论文"""

        url = f"{self.API_BASE_URL}/papers/"
        params = {
            "title_icontains": keyword,
            "ordering": "-published",
            "page": 1,
            "items_per_page": 50,
        }

        papers = []
        page = 1

        while len(papers) < self.max_results:
            params["page"] = page
            response = self._api_get(url, params)

            if not response:
                break

            try:
                data = response.json()
            except Exception as e:
                logger.warning(f"[PapersWithCode] 解析 JSON 失败: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                paper = self._parse_paper_item(item, start_date, end_date)
                if paper:
                    papers.append(paper)

            # 检查是否有下一页
            if not data.get("next"):
                break

            page += 1

        return papers

    def _search_latest(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[PaperMetadata]:
        """搜索最新论文"""

        url = f"{self.API_BASE_URL}/papers/"
        params = {
            "ordering": "-published",
            "page": 1,
            "items_per_page": min(self.max_results, 100),
        }

        response = self._api_get(url, params)
        if not response:
            return []

        try:
            data = response.json()
        except Exception as e:
            logger.warning(f"[PapersWithCode] 解析 JSON 失败: {e}")
            return []

        return self._parse_search_results(data.get("results", []), start_date, end_date)

    def _parse_search_results(
        self,
        results: List[Dict],
        start_date: datetime,
        end_date: datetime,
    ) -> List[PaperMetadata]:
        """解析搜索结果"""

        papers = []
        for item in results:
            paper = self._parse_paper_item(item, start_date, end_date)
            if paper:
                papers.append(paper)

        return papers

    def _parse_paper_item(
        self,
        item: Dict,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[PaperMetadata]:
        """解析单个论文数据"""

        paper_id = str(item.get("id", ""))
        if not paper_id:
            return None

        title = item.get("title", "")
        if not title:
            return None

        # 解析作者
        authors_data = item.get("authors", [])
        authors = []
        for a in authors_data:
            if isinstance(a, dict):
                authors.append(a.get("name", ""))
            elif isinstance(a, str):
                authors.append(a)

        # 解析摘要
        abstract = item.get("abstract", "")

        # 解析发布日期
        pub_date_str = item.get("published")
        if pub_date_str:
            try:
                # 格式: YYYY-MM-DD
                published_date = datetime.strptime(pub_date_str, "%Y-%m-%d")

                # 时间范围过滤
                if published_date < start_date or published_date > end_date:
                    return None
            except:
                published_date = datetime.now()
        else:
            published_date = datetime.now()

        # 解析 URL
        url = item.get("url", f"https://paperswithcode.com/paper/{paper_id}")

        # 解析 arXiv ID
        arxiv_id = item.get("arxiv_id")
        arxiv_url = None
        if arxiv_id:
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

        # 解析 PDF URL
        pdf_url = None
        if arxiv_id:
            pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

        # 解析代码仓库信息
        code_repo = None
        repo_url = item.get("repo_url")
        if repo_url:
            code_repo = repo_url

        return PaperMetadata(
            paper_id=f"pwc-{paper_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            url=url,
            source="paperswithcode",
            pdf_url=pdf_url,
            doi=None,
            journal=item.get("venue", ""),
            categories=item.get("tasks", []) if isinstance(item.get("tasks"), list) else [],
            semantic_scholar_tldr=None,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )