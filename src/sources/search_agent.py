"""
统一搜索调度器

管理多个论文数据源，根据配置调用相应的源进行论文抓取。
支持：ArXiv、DBLP、Papers with Code、Semantic Scholar、OpenReview、Hugging Face Papers、Google Scholar
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional

from .base_source import BasePaperSource, PaperMetadata
from .arxiv_source import ArxivSource
from .openalex_source import OpenAlexSource, JOURNAL_ISSN_MAP
from .semantic_scholar_source import SemanticScholarSource
from .semantic_scholar_enricher import SemanticScholarEnricher
from .dblp_source import DBLPSource
from .paperswithcode_source import PapersWithCodeSource
from .openreview_source import OpenReviewSource
from .huggingface_papers_source import HuggingFacePapersSource
from .google_scholar_source import GoogleScholarSource

logger = logging.getLogger(__name__)


class SearchAgent:
    """
    统一搜索调度器。

    职责：
    - 管理多个数据源（ArXiv、DBLP、Semantic Scholar 等）
    - 根据配置初始化和调用相应的数据源
    - 返回统一格式的论文列表
    - 支持按数据源分组返回结果
    """

    # CS 相关数据源列表
    CS_DATA_SOURCES = [
        "arxiv",
        "semantic_scholar",
        "dblp",
        "paperswithcode",
        "openreview",
        "huggingface_papers",
        "google_scholar",
    ]

    def __init__(
        self,
        history_dir: Path,
        enabled_sources: List[str] = None,
        arxiv_domains: List[str] = None,
        journals: List[str] = None,
        max_results: int = 100,
        max_results_per_source: Dict[str, int] = None,
        openalex_email: str = None,
        openalex_api_key: str = None,
        enable_semantic_scholar: bool = True,
        semantic_scholar_api_key: str = None,
        semantic_scholar_field_of_study: str = "Computer Science",
        keywords: List[str] = None,
        # OpenReview 配置
        openreview_api_key: str = None,
        openreview_venues: List[str] = None,
        openreview_accepted_only: bool = True,
        # Google Scholar 配置
        google_scholar_use_proxy: bool = False,
        google_scholar_proxy_url: str = None,
    ):
        """
        初始化搜索调度器。

        参数:
            history_dir: 历史记录存储目录
            enabled_sources: 启用的数据源列表
            arxiv_domains: ArXiv 领域列表，如 ["cs.AI", "cs.CL"]
            journals: 期刊代码列表（通过 OpenAlex）
            max_results: 每个数据源最多抓取的论文数
            max_results_per_source: 按数据源单独配置
            keywords: 搜索关键词（用于 DBLP、Papers with Code 等）
            semantic_scholar_field_of_study: Semantic Scholar 研究领域筛选
        """
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.enabled_sources = enabled_sources or ["arxiv"]
        self.arxiv_domains = arxiv_domains or []
        self.journals = journals or []
        self.max_results = max_results
        self.max_results_per_source = max_results_per_source or {}
        self.openalex_email = openalex_email
        self.openalex_api_key = openalex_api_key
        self.keywords = keywords or []

        # Semantic Scholar 配置
        self.enable_semantic_scholar = enable_semantic_scholar
        self.semantic_scholar_api_key = semantic_scholar_api_key
        self.semantic_scholar_field_of_study = semantic_scholar_field_of_study
        self.semantic_scholar_enricher = None

        # OpenReview 配置
        self.openreview_api_key = openreview_api_key
        self.openreview_venues = openreview_venues or ["ICLR", "NeurIPS"]
        self.openreview_accepted_only = openreview_accepted_only

        # Google Scholar 配置
        self.google_scholar_use_proxy = google_scholar_use_proxy
        self.google_scholar_proxy_url = google_scholar_proxy_url

        # 初始化 Semantic Scholar 增强器（用于 TLDR 增强）
        if enable_semantic_scholar:
            api_key = semantic_scholar_api_key if semantic_scholar_api_key else None
            self.semantic_scholar_enricher = SemanticScholarEnricher(api_key=api_key)
            logger.info("[SearchAgent] 已启用 Semantic Scholar TLDR 增强")

        # 初始化数据源
        self.sources: Dict[str, BasePaperSource] = {}
        self._init_sources()

    def _get_max_results(self, source: str) -> int:
        """获取指定数据源的最大结果数，优先使用单独配置，否则回退到全局默认值。"""
        return self.max_results_per_source.get(source, self.max_results)

    def _init_sources(self):
        """根据配置初始化数据源"""
        # ArXiv 数据源
        if "arxiv" in self.enabled_sources:
            self.sources["arxiv"] = ArxivSource(
                history_dir=self.history_dir, max_results=self._get_max_results("arxiv")
            )
            logger.info("[SearchAgent] 已启用 ArXiv 数据源")

        # Semantic Scholar 数据源（作为独立源，而非仅增强器）
        if "semantic_scholar" in self.enabled_sources:
            self.sources["semantic_scholar"] = SemanticScholarSource(
                history_dir=self.history_dir,
                max_results=self._get_max_results("semantic_scholar"),
                api_key=self.semantic_scholar_api_key,
                field_of_study=self.semantic_scholar_field_of_study,
            )
            logger.info("[SearchAgent] 已启用 Semantic Scholar 数据源")

        # DBLP 数据源
        if "dblp" in self.enabled_sources:
            self.sources["dblp"] = DBLPSource(
                history_dir=self.history_dir,
                max_results=self._get_max_results("dblp"),
            )
            logger.info("[SearchAgent] 已启用 DBLP 数据源")

        # Papers with Code 数据源
        if "paperswithcode" in self.enabled_sources:
            self.sources["paperswithcode"] = PapersWithCodeSource(
                history_dir=self.history_dir,
                max_results=self._get_max_results("paperswithcode"),
            )
            logger.info("[SearchAgent] 已启用 Papers with Code 数据源")

        # OpenReview 数据源
        if "openreview" in self.enabled_sources:
            self.sources["openreview"] = OpenReviewSource(
                history_dir=self.history_dir,
                max_results=self._get_max_results("openreview"),
                api_key=self.openreview_api_key,
            )
            logger.info("[SearchAgent] 已启用 OpenReview 数据源")

        # Hugging Face Papers 数据源
        if "huggingface_papers" in self.enabled_sources:
            self.sources["huggingface_papers"] = HuggingFacePapersSource(
                history_dir=self.history_dir,
                max_results=self._get_max_results("huggingface_papers"),
            )
            logger.info("[SearchAgent] 已启用 Hugging Face Papers 数据源")

        # Google Scholar 数据源（可选，风险较高）
        if "google_scholar" in self.enabled_sources:
            self.sources["google_scholar"] = GoogleScholarSource(
                history_dir=self.history_dir,
                max_results=self._get_max_results("google_scholar"),
                use_proxy=self.google_scholar_use_proxy,
                proxy_url=self.google_scholar_proxy_url,
            )
            logger.info("[SearchAgent] 已启用 Google Scholar 数据源（注意：可能被封）")

        # 期刊数据源（通过 OpenAlex）
        journal_codes = []
        for source in self.enabled_sources:
            if source not in self.CS_DATA_SOURCES and source in JOURNAL_ISSN_MAP:
                journal_codes.append(source)

        for journal in self.journals:
            if journal not in journal_codes and journal in JOURNAL_ISSN_MAP:
                journal_codes.append(journal)

        if journal_codes:
            openalex_max = max(
                (self._get_max_results(jc) for jc in journal_codes),
                default=self.max_results,
            )
            self.sources["openalex"] = OpenAlexSource(
                history_dir=self.history_dir,
                journals=journal_codes,
                max_results=openalex_max,
                email=self.openalex_email,
                api_key=self.openalex_api_key,
            )
            self._journal_codes = journal_codes
            logger.info(f"[SearchAgent] 已启用 OpenAlex 数据源，期刊: {journal_codes}")
        else:
            self._journal_codes = []

    def fetch_all_papers(self, days: int = 7) -> Dict[str, List[PaperMetadata]]:
        """
        从所有启用的数据源抓取论文。

        参数:
            days: 搜索最近 N 天的论文

        返回:
            Dict[str, List[PaperMetadata]]: {数据源名: 论文列表}
        """
        results = {}

        for source_name, source in self.sources.items():
            logger.info(f">>> 从 {source.display_name} 抓取论文...")

            try:
                if source_name == "arxiv":
                    papers = source.fetch_papers(days=days, domains=self.arxiv_domains)
                    results["arxiv"] = papers

                elif source_name == "semantic_scholar":
                    papers = source.fetch_papers(days=days, keywords=self.keywords)
                    results["semantic_scholar"] = papers

                elif source_name == "dblp":
                    papers = source.fetch_papers(days=days, keywords=self.keywords)
                    results["dblp"] = papers

                elif source_name == "paperswithcode":
                    papers = source.fetch_papers(days=days, keywords=self.keywords)
                    results["paperswithcode"] = papers

                elif source_name == "openreview":
                    papers = source.fetch_papers(
                        days=days,
                        venues=self.openreview_venues,
                        accepted_only=self.openreview_accepted_only,
                    )
                    results["openreview"] = papers

                elif source_name == "huggingface_papers":
                    papers = source.fetch_papers(days=days)
                    # 补充元数据（从 arXiv）
                    for paper in papers:
                        if paper.arxiv_id and not paper.title:
                            paper = source.enrich_paper_metadata(paper)
                    results["huggingface_papers"] = papers

                elif source_name == "google_scholar":
                    papers = source.fetch_papers(days=days, keywords=self.keywords)
                    results["google_scholar"] = papers

                elif source_name == "openalex":
                    papers = source.fetch_papers(days=days)
                    # 增强：获取 Semantic Scholar TLDR
                    if self.enable_semantic_scholar and self.semantic_scholar_enricher:
                        papers = self._enrich_with_semantic_scholar(papers)
                    for paper in papers:
                        if paper.source not in results:
                            results[paper.source] = []
                        results[paper.source].append(paper)

                else:
                    papers = source.fetch_papers(days=days)
                    results[source_name] = papers

            except Exception as e:
                logger.error(f"[{source_name}] 抓取失败: {e}")
                import traceback
                traceback.print_exc()

        # 统计
        total = sum(len(papers) for papers in results.values())
        logger.info(f">>> 总计抓取 {total} 篇论文，来自 {len(results)} 个数据源")

        return results

    def _enrich_with_semantic_scholar(self, papers: List[PaperMetadata]) -> List[PaperMetadata]:
        """
        使用 Semantic Scholar 增强论文元数据（添加 TLDR 和 arXiv 信息）。

        参数:
            papers: 论文列表

        返回:
            List[PaperMetadata]: 增强后的论文列表
        """
        if not self.semantic_scholar_enricher:
            return papers

        logger.info("  正在从 Semantic Scholar 获取增强信息...")
        enriched_count = 0
        arxiv_found_count = 0

        for paper in papers:
            if paper.doi:
                # 获取完整的论文信息（TLDR + arXiv ID）
                paper_info = self.semantic_scholar_enricher.get_paper_info(paper.doi)
                if paper_info:
                    # 设置 TLDR
                    if paper_info.get("tldr"):
                        paper.semantic_scholar_tldr = paper_info["tldr"]
                        enriched_count += 1

                    # 设置 arXiv 信息（用于后续深度分析）
                    if paper_info.get("arxiv_id"):
                        paper.arxiv_id = paper_info["arxiv_id"]
                        paper.arxiv_url = paper_info.get(
                            "arxiv_url", f"https://arxiv.org/abs/{paper_info['arxiv_id']}"
                        )
                        # 设置 PDF URL 以便下载
                        paper.pdf_url = f"https://arxiv.org/pdf/{paper_info['arxiv_id']}.pdf"
                        arxiv_found_count += 1
                        logger.debug(f"    找到 arXiv 版本: {paper_info['arxiv_id']}")

        if enriched_count > 0 or arxiv_found_count > 0:
            logger.info(f"    TLDR: {enriched_count}/{len(papers)} 篇")
            logger.info(f"    arXiv版本: {arxiv_found_count}/{len(papers)} 篇")
        else:
            logger.info("    未获取到增强信息")

        return papers

    def mark_as_processed(self, paper_id: str, source: str):
        """
        标记论文为已处理。

        参数:
            paper_id: 论文 ID
            source: 数据源名称
        """
        # 根据 source 找到对应的数据源实例
        if source in self.sources:
            self.sources[source].mark_as_processed(paper_id)
        elif source in self._journal_codes and "openalex" in self.sources:
            self.sources["openalex"].mark_as_processed(paper_id)
        elif source == "arxiv" and "arxiv" in self.sources:
            self.sources["arxiv"].mark_as_processed(paper_id)

    def get_source(self, source_name: str) -> Optional[BasePaperSource]:
        """获取指定的数据源实例"""
        return self.sources.get(source_name)

    def can_download_pdf(self, source: str) -> bool:
        """检查指定数据源是否支持 PDF 下载"""
        if source in self.sources:
            return self.sources[source].can_download_pdf()
        return False

    def get_enabled_sources(self) -> List[str]:
        """获取所有启用的数据源名称"""
        sources = list(self.sources.keys())
        # 如果有 openalex，展开为具体期刊
        if "openalex" in sources:
            sources.remove("openalex")
            sources.extend(self._journal_codes)
        return sources

    @staticmethod
    def get_available_journals() -> Dict[str, Dict]:
        """获取所有可用的期刊列表"""
        return JOURNAL_ISSN_MAP
