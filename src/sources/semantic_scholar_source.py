"""
Semantic Scholar 数据源

通过 Semantic Scholar API 搜索计算机科学领域的论文。
支持按关键词、领域、时间范围搜索。
"""

import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base_source import BasePaperSource, PaperMetadata

logger = logging.getLogger(__name__)


class SemanticScholarSource(BasePaperSource):
    """
    Semantic Scholar 数据源实现。

    功能：
    - 按关键词搜索论文
    - 支持按研究领域筛选（Computer Science）
    - 支持按时间范围筛选
    - 获取 AI 生成的 TLDR
    """

    API_BASE_URL = "https://api.semanticscholar.org/graph/v1"

    # 支持的研究领域
    FIELD_OF_STUDY_OPTIONS = [
        "Computer Science",
        "Medicine",
        "Chemistry",
        "Biology",
        "Materials Science",
        "Physics",
        "Geology",
        "Psychology",
        "Art",
        "History",
        "Geography",
        "Sociology",
        "Political Science",
        "Economics",
        "Business",
        "Environmental Science",
        "Engineering",
        "Mathematics",
        "Law",
        "Philosophy",
    ]

    def __init__(
        self,
        history_dir: Path,
        max_results: int = 100,
        api_key: Optional[str] = None,
        field_of_study: Optional[str] = "Computer Science",
    ):
        """
        初始化 Semantic Scholar 数据源。

        参数:
            history_dir: 历史记录存储目录
            max_results: 最大结果数
            api_key: Semantic Scholar API Key（可选，提高速率限制）
            field_of_study: 研究领域筛选（默认 Computer Science）
        """
        super().__init__("semantic_scholar", history_dir)

        self.max_results = max_results
        self.api_key = api_key
        self.field_of_study = field_of_study

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArxivDailyResearcher/3.0 (https://github.com/yzr278892/arxiv-daily-researcher)"
        })

        if api_key:
            self.session.headers.update({"x-api-key": api_key})
            logger.info("[SemanticScholar] 已启用 API Key，速率限制提升")
        else:
            logger.info("[SemanticScholar] 使用公共 API，限速 100次/5分钟")

    @property
    def display_name(self) -> str:
        return "Semantic Scholar"

    def can_download_pdf(self) -> bool:
        """Semantic Scholar 可以通过 arXiv ID 获取 PDF"""
        return True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.session:
            self.session.close()
            logger.debug("[SemanticScholar] Session 已关闭")

    def _api_get(
        self, url: str, params: dict, timeout: int = 30
    ) -> Optional[requests.Response]:
        """发送 API GET 请求，带自动重试（跳过 404/429）。"""
        from config import settings as _settings

        @retry(
            stop=stop_after_attempt(_settings.RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(min=_settings.RETRY_MIN_WAIT, max=_settings.RETRY_MAX_WAIT),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _do_get():
            resp = self.session.get(url, params=params, timeout=timeout)
            if resp.status_code in (404, 429):
                return resp
            resp.raise_for_status()
            return resp

        try:
            return _do_get()
        except Exception as e:
            logger.warning(f"[SemanticScholar] API 请求失败: {e}")
            return None

    def fetch_papers(self, days: int, **kwargs) -> List[PaperMetadata]:
        """
        搜索最近 N 天的论文。

        参数:
            days: 搜索最近 N 天
            keywords: 搜索关键词列表（可选）
            field_of_study: 研究领域（可选，覆盖默认值）

        返回:
            List[PaperMetadata]: 论文列表
        """
        keywords = kwargs.get("keywords", [])
        field_of_study = kwargs.get("field_of_study", self.field_of_study)

        logger.info(f"[SemanticScholar] 开始搜索论文")
        logger.info(f"  关键词: {keywords if keywords else '无（全领域搜索）'}")
        logger.info(f"  领域: {field_of_study}")
        logger.info(f"  时间范围: 最近 {days} 天")

        papers = []

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        year_start = start_date.year
        year_end = end_date.year

        # 构建搜索参数
        if keywords:
            # 按关键词搜索
            for keyword in keywords:
                keyword_papers = self._search_by_keyword(
                    keyword, field_of_study, year_start, year_end
                )
                papers.extend(keyword_papers)
        else:
            # 无关键词时，按领域搜索最新论文
            papers = self._search_by_field(field_of_study, year_start, year_end)

        # 过滤已处理的论文
        new_papers = []
        for paper in papers:
            if not self.is_processed(paper.paper_id):
                new_papers.append(paper)
            else:
                logger.debug(f"[SemanticScholar] 跳过已处理: {paper.paper_id}")

        logger.info(f"[SemanticScholar] 发现 {len(new_papers)} 篇新论文")

        return new_papers[:self.max_results]

    def _search_by_keyword(
        self,
        keyword: str,
        field_of_study: Optional[str],
        year_start: int,
        year_end: int,
    ) -> List[PaperMetadata]:
        """按关键词搜索论文"""

        url = f"{self.API_BASE_URL}/paper/search/bulk"
        params = {
            "query": keyword,
            "fields": "paperId,title,authors,abstract,year,publicationDate,url,externalIds,openAccessPdf,tldr,venue",
            "limit": 100,
        }

        if field_of_study:
            params["fieldsOfStudy"] = field_of_study

        if year_start and year_end:
            params["year"] = f"{year_start}-{year_end}"

        response = self._api_get(url, params)
        if not response or response.status_code != 200:
            return []

        data = response.json()
        return self._parse_search_results(data.get("data", []))

    def _search_by_field(
        self,
        field_of_study: str,
        year_start: int,
        year_end: int,
    ) -> List[PaperMetadata]:
        """按领域搜索最新论文"""

        url = f"{self.API_BASE_URL}/paper/search/bulk"
        params = {
            "query": "*",  # 通配符搜索
            "fields": "paperId,title,authors,abstract,year,publicationDate,url,externalIds,openAccessPdf,tldr,venue",
            "fieldsOfStudy": field_of_study,
            "year": f"{year_start}-{year_end}",
            "limit": self.max_results,
        }

        response = self._api_get(url, params)
        if not response or response.status_code != 200:
            return []

        data = response.json()
        return self._parse_search_results(data.get("data", []))

    def _parse_search_results(self, results: List[Dict]) -> List[PaperMetadata]:
        """解析搜索结果为 PaperMetadata 列表"""

        papers = []
        for item in results:
            try:
                paper = self._parse_paper_item(item)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"[SemanticScholar] 解析论文失败: {e}")
                continue

        return papers

    def _parse_paper_item(self, item: Dict) -> Optional[PaperMetadata]:
        """解析单个论文数据"""

        paper_id = item.get("paperId")
        if not paper_id:
            return None

        title = item.get("title", "")
        if not title:
            return None

        # 解析作者
        authors_data = item.get("authors", [])
        authors = [a.get("name", "") for a in authors_data if a.get("name")]

        # 解析摘要
        abstract = item.get("abstract", "")

        # 解析发布日期
        pub_date_str = item.get("publicationDate")
        if pub_date_str:
            try:
                published_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            except:
                published_date = datetime.now()
        else:
            year = item.get("year")
            if year:
                published_date = datetime(year, 1, 1)
            else:
                published_date = datetime.now()

        # 解析 URL
        url = item.get("url", f"https://www.semanticscholar.org/paper/{paper_id}")

        # 解析 TLDR
        tldr_obj = item.get("tldr")
        tldr_text = None
        if tldr_obj and isinstance(tldr_obj, dict):
            tldr_text = tldr_obj.get("text")

        # 解析 arXiv ID 和 PDF
        external_ids = item.get("externalIds", {})
        arxiv_id = external_ids.get("ArXiv")
        doi = external_ids.get("DOI")

        # 解析 PDF URL
        pdf_url = None
        open_access_pdf = item.get("openAccessPdf")
        if open_access_pdf:
            pdf_url = open_access_pdf.get("url")

        # 如果有 arXiv ID，构建 PDF URL
        if arxiv_id and not pdf_url:
            pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

        # 解析期刊/会议
        venue = item.get("venue", "")

        return PaperMetadata(
            paper_id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            url=url,
            source="semantic_scholar",
            pdf_url=pdf_url,
            doi=doi,
            journal=venue,
            categories=[self.field_of_study] if self.field_of_study else [],
            semantic_scholar_tldr=tldr_text,
            arxiv_id=arxiv_id,
            arxiv_url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
        )