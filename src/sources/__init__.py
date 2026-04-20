"""
论文数据源模块

提供多种论文数据源的统一接口：
- ArxivSource: ArXiv预印本数据源（支持PDF下载）
- OpenAlexSource: OpenAlex期刊数据源（元数据 + 摘要）
- SemanticScholarSource: Semantic Scholar数据源（CS领域搜索）
- SemanticScholarEnricher: Semantic Scholar数据增强器（TLDR + arXiv链接）
- DBLPSource: DBLP计算机科学文献索引
- PapersWithCodeSource: Papers with Code ML论文+代码
- OpenReviewSource: OpenReview顶会论文（ICLR/NeurIPS）
- HuggingFacePapersSource: Hugging Face每日AI论文
- GoogleScholarSource: Google Scholar通用搜索（可选）
- SearchAgent: 多源论文抓取编排
"""

from .base_source import BasePaperSource, PaperMetadata
from .arxiv_source import ArxivSource
from .openalex_source import OpenAlexSource
from .semantic_scholar_source import SemanticScholarSource
from .semantic_scholar_enricher import SemanticScholarEnricher
from .dblp_source import DBLPSource
from .paperswithcode_source import PapersWithCodeSource
from .openreview_source import OpenReviewSource
from .huggingface_papers_source import HuggingFacePapersSource
from .google_scholar_source import GoogleScholarSource
from .search_agent import SearchAgent

__all__ = [
    "BasePaperSource",
    "PaperMetadata",
    "ArxivSource",
    "OpenAlexSource",
    "SemanticScholarSource",
    "SemanticScholarEnricher",
    "DBLPSource",
    "PapersWithCodeSource",
    "OpenReviewSource",
    "HuggingFacePapersSource",
    "GoogleScholarSource",
    "SearchAgent",
]
