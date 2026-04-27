"""
Models package for lo-scout application.
Provides data structures for performers, filters, and pagination.
"""

from .performer import Performer
from .filters import FilterConfig

__all__ = ['Performer', 'FilterConfig']