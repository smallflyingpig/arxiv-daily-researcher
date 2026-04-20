"""
Google Scholar 数据源

Google Scholar 没有官方 API，使用 scholarly 库进行搜索。
注意：可能面临被封禁风险，建议低频使用。

文档: https://github.com/scholarly-python-package/scholarly
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .base_source import BasePaperSource, PaperMetadata

logger = logging.getLogger(__name__)

# 尝试导入 scholarly
try:
    from scholarly import scholarly, ProxyGenerator
    HAS_SCHOLARLY = True
except ImportError:
    HAS_SCHOLARLY = False
    logger.warning("[GoogleScholar] scholarly 库未安装，数据源不可用。pip install scholarly")


class GoogleScholarSource(BasePaperSource):
    """
    Google Scholar 数据源实现。

    功能：
    - 按关键词搜索论文
    - 获取引用数、摘要等
    - 支持代理设置（防止被封）

    警告:
    - Google Scholar 无官方 API
    - 高频请求可能导致 IP 被封
    - 建议使用代理或设置低速率
    """

    def __init__(
        self,
        history_dir: Path,
        max_results: int = 50,
        use_proxy: bool = False,
        proxy_url: Optional[str] = None,
    ):
        """
        初始化 Google Scholar 数据源。

        参数:
            history_dir: 历史记录存储目录
            max_results: 最大结果数（建议不超过50）
            use_proxy: 是否使用代理
            proxy_url: 代理 URL（如 "socks5://127.0.0.1:9050"）
        """
        super().__init__("google_scholar", history_dir)

        self.max_results = max_results
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url

        if not HAS_SCHOLARLY:
            logger.error("[GoogleScholar] scholarly 库未安装")
            return

        # 设置代理（可选）
        if use_proxy and proxy_url:
            try:
                pg = ProxyGenerator()
                pg.SingleProxy(http=proxy_url, https=proxy_url)
                scholarly.use_proxy(pg)
                logger.info(f"[GoogleScholar] 已配置代理: {proxy_url}")
            except Exception as e:
                logger.warning(f"[GoogleScholar] 代理设置失败: {e}")

        # 设置较低的请求速率
        scholarly._SESSION_RATE_LIMIT = 30  # 30秒间隔

        logger.info("[GoogleScholar] 已启用数据源（警告：可能被封）")

    @property
    def display_name(self) -> str:
        return "Google Scholar"

    def can_download_pdf(self) -> bool:
        """Google Scholar 可能链接到 PDF"""
        return False

    def fetch_papers(self, days: int, **kwargs) -> List[PaperMetadata]:
        """
        搜索最近 N 天的论文。

        参数:
            days: 搜索最近 N 天
            keywords: 搜索关键词列表

        返回:
            List[PaperMetadata]: 论文列表
        """
        if not HAS_SCHOLARLY:
            logger.error("[GoogleScholar] scholarly 库未安装，无法搜索")
            return []

        keywords = kwargs.get("keywords", [])

        if not keywords:
            logger.warning("[GoogleScholar] 未提供关键词，无法搜索")
            return []

        logger.info(f"[GoogleScholar] 开始搜索论文")
        logger.info(f"  关键词: {keywords}")
        logger.info(f"  时间范围: 最近 {days} 天")
        logger.warning("[GoogleScholar] ⚠️ 低频运行中，避免被封")

        papers = []

        # 计算时间范围
        start_year = (datetime.now() - timedelta(days=days)).year
        end_year = datetime.now().year

        for keyword in keywords:
            keyword_papers = self._search_by_keyword(keyword, start_year, end_year)
            papers.extend(keyword_papers)

        # 过滤已处理的论文
        new_papers = []
        for paper in papers:
            if not self.is_processed(paper.paper_id):
                new_papers.append(paper)
            else:
                logger.debug(f"[GoogleScholar] 跳过已处理: {paper.paper_id}")

        logger.info(f"[GoogleScholar] 发现 {len(new_papers)} 篇新论文")

        return new_papers[:self.max_results]

    def _search_by_keyword(
        self,
        keyword: str,
        start_year: int,
        end_year: int,
    ) -> List[PaperMetadata]:
        """按关键词搜索"""

        papers = []

        try:
            # 构建搜索查询（包含年份范围）
            query = f"{keyword} after:{start_year} before:{end_year+1}"

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(min=30, max=120),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )
            def _search():
                return scholarly.search_pubs(query, limit=self.max_results)

            search_results = _search()

            for result in search_results:
                try:
                    paper = self._parse_scholarly_result(result)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"[GoogleScholar] 解析论文失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"[GoogleScholar] 搜索失败: {e}")

        return papers

    def _parse_scholarly_result(self, result: Dict) -> Optional[PaperMetadata]:
        """解析 scholarly 返回结果"""

        bib = result.get("bib", {})

        # 获取标题
        title = bib.get("title", "")
        if not title:
            return None

        # 获取作者
        authors = bib.get("author", [])
        if isinstance(authors, str):
            authors = [authors]

        # 获取摘要
        abstract = bib.get("abstract", "")

        # 获取年份
        year = bib.get("pub_year")
        if year:
            try:
                year_int = int(year)
                published_date = datetime(year_int, 1, 1)
            except:
                published_date = datetime.now()
        else:
            published_date = datetime.now()

        # 获取 URL
        url = result.get("url", "") or bib.get("url", "")

        # 获取 Scholar ID
        scholar_id = result.get("url_scholarbib", "")
        if scholar_id:
            # 提取 ID
            import re
            match = re.search(r"scholar\?q=info:([^:]+)", scholar_id)
            if match:
                scholar_id = match.group(1)

        if not scholar_id:
            scholar_id = f"gs-{hash(title) % 100000000}"

        # 获取引用数
        num_citations = result.get("num_citations", 0)

        # 获取 arXiv ID（如果有）
        arxiv_id = None
        arxiv_url = None
        eprint_url = result.get("eprint_url", "")
        if eprint_url and "arxiv.org" in eprint_url:
            match = re.search(r"arxiv\.org/(abs|pdf)/([0-9.]+)", eprint_url)
            if match:
                arxiv_id = match.group(2)
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

        # PDF URL
        pdf_url = eprint_url

        return PaperMetadata(
            paper_id=f"gs-{scholar_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            url=url or f"https://scholar.google.com/scholar?q={title}",
            source="google_scholar",
            pdf_url=pdf_url,
            doi=None,
            journal=bib.get("journal", "") or bib.get("venue", ""),
            categories=[],
            semantic_scholar_tldr=None,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )