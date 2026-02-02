"""Database module"""

from app.db.vector import get_domain_law_retriever, get_vectorstore

__all__ = ["get_vectorstore", "get_domain_law_retriever"]
