import json
import os
from typing import List, Dict, Any
import re

class KnowledgeLoader:
    """Loads and chunks travel knowledge documents."""
    
    def __init__(self, faqs_path: str = None):
        self.faqs_path = faqs_path or os.path.join(
            os.path.dirname(__file__), "faqs.json"
        )
        self.documents = []
        self.chunks = []
        
    def load_faqs(self) -> List[Dict[str, Any]]:
        """Load FAQs from JSON file."""
        try:
            with open(self.faqs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data.get("documents", [])
                return self.documents
        except FileNotFoundError:
            
            self._create_default_faqs()
            return self.documents
    
    def _create_default_faqs(self):
        """Create default FAQs if file not found."""
        default_faqs = {
            "documents": [
                {
                    "id": "faq_general_1",
                    "title": "General Travel Planning",
                    "destination": "general",
                    "content": "When planning a trip, consider booking accommodations and flights at least 2-3 months in advance for better prices. Always check visa requirements and travel insurance options. Save emergency contact numbers and have copies of important documents.",
                    "category": "planning"
                },
                {
                    "id": "faq_general_2",
                    "title": "Budget Travel Tips",
                    "destination": "general",
                    "content": "Travel during off-peak seasons for lower prices. Use public transportation instead of taxis. Eat like a local at markets and street food stalls. Book free walking tours in major cities and use travel credit cards with no foreign transaction fees.",
                    "category": "budget_tips"
                }
            ]
        }
        
        os.makedirs(os.path.dirname(self.faqs_path), exist_ok=True)
        
        with open(self.faqs_path, 'w', encoding='utf-8') as f:
            json.dump(default_faqs, f, indent=2, ensure_ascii=False)
        
        self.documents = default_faqs["documents"]
    
    def chunk_documents(self, documents: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Split documents into smaller chunks for embedding."""
        if documents is None:
            documents = self.documents
        
        chunks = []
        for doc in documents:
            content_parts = self._split_content(doc["content"])
            
            for i, part in enumerate(content_parts):
                chunks.append({
                    "id": f"{doc['id']}_chunk_{i+1}",
                    "source_id": doc["id"],
                    "title": doc["title"],
                    "destination": doc.get("destination", "general"),
                    "category": doc.get("category", "general"),
                    "content": part,
                    "metadata": {
                        "source": "faq",
                        "destination": doc.get("destination", "general")
                    }
                })
        
        self.chunks = chunks
        return chunks
    
    def _split_content(self, content: str) -> List[str]:
        """Split content into smaller chunks based on sentences."""
        
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        chunks = []
        current_chunk = ""
        max_chunk_size = 500  # Characters, adjust as needed
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def get_filtered_by_destination(self, destination: str) -> List[Dict[str, Any]]:
        """Get chunks specific to a destination."""
        if not self.chunks:
            self.load_and_chunk()
        
        return [chunk for chunk in self.chunks 
                if chunk.get("destination", "").lower() == destination.lower() 
                or chunk.get("destination", "").lower() == "general"]
    
    def load_and_chunk(self) -> List[Dict[str, Any]]:
        """Load FAQs and chunk them in one call."""
        self.load_faqs()
        return self.chunk_documents()

# Singleton instance for reuse
knowledge_loader = KnowledgeLoader()