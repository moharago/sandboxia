"""Database module"""

from app.db.vector import get_vectorstore, get_domain_law_retriever

__all__ = ["get_vectorstore", "get_domain_law_retriever"]
