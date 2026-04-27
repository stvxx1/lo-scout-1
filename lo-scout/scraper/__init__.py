"""
Scraper package for lo-scout application.
Provides modular scraping capabilities for adult performer databases.
"""

from .base import BaseScraper
from .freeones import FreeonesScraper

__all__ = ['BaseScraper', 'FreeonesScraper']