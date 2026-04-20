"""
Hugging Face Papers 数据源

Hugging Face 每日精选 AI/NLP 领域的热门论文。
通过解析每日论文页面获取数据。

页面: https://huggingface.co/papers
"""

import logging
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base_source import BasePaperSource, PaperMetadata

logger = logging.getLogger(__name__)


class HuggingFacePapersSource(BasePaperSource):
    """
    Hugging Face Papers 数据源实现。

    功能：
    - 获取每日精选 AI 论文
    - 按热度排序
    - 支持指定日期范围
    """

    BASE_URL = "https://huggingface.co"

    def __init__(
        self,
        history_dir: Path,
        max_results: int = 100,
    ):
        """
        初始化 Hugging Face Papers 数据源。

        参数:
            history_dir: 历史记录存储目录
            max_results: 最大结果数
        """
        super().__init__("huggingface_papers", history_dir)

        self.max_results = max_results

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArxivDailyResearcher/3.0 (https://github.com/yzr278892/arxiv-daily-researcher)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        logger.info("[HuggingFace] 已启用 Papers 数据源")

    @property
    def display_name(self) -> str:
        return "Hugging Face Papers"

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
            logger.debug("[HuggingFace] Session 已关闭")

    def _api_get(
        self, url: str, params: dict = None, timeout: int = 30
    ) -> Optional[requests.Response]:
        """发送 GET 请求，带自动重试"""
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
            logger.warning(f"[HuggingFace] 请求失败: {e}")
            return None

    def fetch_papers(self, days: int, **kwargs) -> List[PaperMetadata]:
        """
        获取最近 N 天的精选论文。

        参数:
            days: 获取最近 N 天

        返回:
            List[PaperMetadata]: 论文列表
        """
        logger.info(f"[HuggingFace] 开始获取每日论文")
        logger.info(f"  时间范围: 最近 {days} 天")

        papers = []

        # 计算日期范围
        today = datetime.now()

        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            daily_papers = self._fetch_daily_papers(date_str)
            papers.extend(daily_papers)

        # 过滤已处理的论文
        new_papers = []
        seen_ids = set()

        for paper in papers:
            if paper.paper_id not in seen_ids and not self.is_processed(paper.paper_id):
                new_papers.append(paper)
                seen_ids.add(paper.paper_id)
            else:
                logger.debug(f"[HuggingFace] 跳过重复: {paper.paper_id}")

        logger.info(f"[HuggingFace] 发现 {len(new_papers)} 篇新论文")

        return new_papers[:self.max_results]

    def _fetch_daily_papers(self, date_str: str) -> List[PaperMetadata]:
        """获取指定日期的论文"""

        url = f"{self.BASE_URL}/papers"
        params = {"date": date_str}

        response = self._api_get(url, params)
        if not response:
            return []

        return self._parse_papers_page(response.text, date_str)

    def _parse_papers_page(self, html: str, date_str: str) -> List[PaperMetadata]:
        """解析论文页面 HTML"""

        papers = []

        # Hugging Face Papers 页面结构相对简单
        # 论文通常以 arXiv ID 为标识

        # 查找所有论文链接
        # 模式: /papers/xxxx.xxxxx
        paper_pattern = r'/papers/(\d{4}\.\d{4,5}(?:v\d+)?)'

        matches = re.findall(paper_pattern, html)

        if not matches:
            # 尝试另一种模式（旧版 arXiv ID）
            paper_pattern = r'/papers/([a-z-]+/\d{4}\.\d{4,5})'
            matches = re.findall(paper_pattern, html)

        for arxiv_id in matches[:self.max_results]:
            try:
                paper = self._create_paper_from_arxiv_id(arxiv_id, date_str)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"[HuggingFace] 解析论文失败: {e}")
                continue

        return papers

    def _create_paper_from_arxiv_id(
        self,
        arxiv_id: str,
        date_str: str,
    ) -> Optional[PaperMetadata]:
        """从 arXiv ID 创建 PaperMetadata"""

        # 清理 arXiv ID
        arxiv_id = arxiv_id.strip()

        # 构建 URL
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
        hf_url = f"{self.BASE_URL}/papers/{arxiv_id}"

        # PDF URL
        pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

        # 解析日期
        try:
            published_date = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            published_date = datetime.now()

        return PaperMetadata(
            paper_id=f"hf-{arxiv_id}",
            title="",  # 需要从 arXiv API 补充
            authors=[],  # 需要从 arXiv API 补充
            abstract="",  # 需要从 arXiv API 补充
            published_date=published_date,
            url=hf_url,
            source="huggingface_papers",
            pdf_url=pdf_url,
            doi=None,
            journal="Hugging Face Daily Papers",
            categories=["AI", "NLP", "ML"],
            semantic_scholar_tldr=None,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )

    def enrich_paper_metadata(self, paper: PaperMetadata) -> PaperMetadata:
        """
        补充论文元数据（从 arXiv API）。

        由于 HF Papers 页面只有 arXiv ID，
        需要调用 arXiv API 获取完整信息。
        """
        if not paper.arxiv_id:
            return paper

        try:
            # 使用 arXiv API 获取详情
            import arxiv

            search = arxiv.Search(id_list=[paper.arxiv_id])
            result = next(search.results(), None)

            if result:
                paper.title = result.title
                paper.authors = [a.name for a in result.authors]
                paper.abstract = result.summary
                paper.published_date = result.published

                logger.debug(f"[HuggingFace] 补充元数据: {paper.title[:50]}...")

        except Exception as e:
            logger.warning(f"[HuggingFace] 补充元数据失败: {e}")

        return paper