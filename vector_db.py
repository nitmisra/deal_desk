from typing import List, Dict, Any
import numpy as np
from datetime import datetime

class MockVectorDB:
    """
    A simplified Vector DB for demonstration.
    In production, replace with Pinecone, Qdrant, or Weaviate.
    """
    
    def __init__(self):
        # Mock knowledge base documents
        self.documents = [
            {
                "id": "doc_001",
                "text": "Our platform supports SAML 2.0 and OIDC for Single Sign-On. Session timeouts are strictly enforced at 15 minutes of inactivity. Multi-factor authentication (MFA) is required for all administrative accounts.",
                "metadata": {
                    "doc_type": "security_whitepaper",
                    "product_module": "core_platform",
                    "effective_date": "2026-01-01",
                    "expiration_date": "2027-01-01",
                    "classification": "public"
                }
            },
            {
                "id": "doc_002",
                "text": "DealDesk Enterprise tier includes 99.9% uptime SLA. Our infrastructure is hosted on AWS with data centers in US-East-1 and EU-West-1 (Frankfurt). We are SOC2 Type II certified and GDPR compliant.",
                "metadata": {
                    "doc_type": "compliance_policy",
                    "product_module": "infrastructure",
                    "effective_date": "2026-01-01",
                    "expiration_date": "2027-01-01",
                    "classification": "public"
                }
            },
            {
                "id": "doc_003",
                "text": "API rate limits: Starter tier - 1,000 requests/hour. Professional tier - 10,000 requests/hour. Enterprise tier - 100,000 requests/hour with dedicated support.",
                "metadata": {
                    "doc_type": "pricing_sheet",
                    "product_module": "api",
                    "effective_date": "2026-06-01",
                    "expiration_date": "2027-06-01",
                    "classification": "public"
                }
            }
        ]
    
    def query(
        self,
        query_text: str,
        metadata_filter: Dict[str, Any] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Mock retrieval with metadata filtering.
        In production, this would use actual vector similarity search.
        """
        results = []
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for doc in self.documents:
            # Apply metadata filters
            if metadata_filter:
                skip = False
                
                # Check doc_type filter
                if "doc_type" in metadata_filter:
                    if doc["metadata"]["doc_type"] not in metadata_filter["doc_type"]:
                        skip = True
                
                # Check classification filter
                if "classification" in metadata_filter:
                    if doc["metadata"]["classification"] != metadata_filter["classification"]:
                        skip = True
                
                # Check date validity
                if doc["metadata"]["effective_date"] > current_date:
                    skip = True
                if doc["metadata"]["expiration_date"] < current_date:
                    skip = True
                
                if skip:
                    continue
            
            # Mock similarity scoring (in production, use actual embeddings)
            # For demo, we'll use simple keyword matching
            score = self._calculate_mock_similarity(query_text, doc["text"])
            
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": score
            })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _calculate_mock_similarity(self, query: str, text: str) -> float:
        """Mock similarity calculation using keyword overlap."""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        overlap = len(query_words.intersection(text_words))
        return overlap / max(len(query_words), 1)