"""
Document Q&A Skill - Answer questions from uploaded documents using in-memory storage
"""
import os
from typing import Generator, List, Dict, Optional
from groq import Groq
import hashlib


class DocumentStore:
    """Simple in-memory document storage"""
    
    def __init__(self):
        self.documents: List[Dict[str, str]] = []
    
    def add_document(self, content: str, filename: str = "document"):
        """Add a document to the store (prevents duplicates)"""
        doc_id = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Check if document already exists (by ID)
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc_id  # Already exists, don't add again
        
        # Add new document
        self.documents.append({
            "id": doc_id,
            "filename": filename,
            "content": content
        })
        return doc_id
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """Improved search with substring matching for better Chinese support"""
        query_lower = query.lower()
        
        # Score documents by multiple criteria
        scored_docs = []
        for doc in self.documents:
            content_lower = doc["content"].lower()
            score = 0
            
            # 1. Direct substring match (highest priority)
            if query_lower in content_lower:
                score += 100
            
            # 2. Individual character matching (for Chinese)
            for char in query_lower:
                if char in content_lower and char.strip():
                    score += 1
            
            # 3. Word-based matching (for English/mixed content)
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            word_overlap = len(query_words & content_words)
            score += word_overlap * 10
            
            if score > 0:
                scored_docs.append((score, doc))
        
        # Sort by score and return top_k
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        return [doc for _, doc in scored_docs[:top_k]]
    
    def get_all_documents(self) -> List[Dict[str, str]]:
        """Get all documents"""
        return self.documents
    
    def clear(self):
        """Clear all documents"""
        self.documents.clear()


# Global document store - will be initialized in get_document_store()
_document_store = None


class DocumentQASkill:
    """Answer questions from documents using RAG approach"""
    
    def __init__(self, document_store: Optional[DocumentStore] = None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        # Use provided store or fallback to global
        self.store = document_store if document_store is not None else get_document_store()
    
    def execute(self, query: str) -> Generator[str, None, None]:
        """
        Execute document Q&A and stream results
        
        Args:
            query: User's question
            
        Yields:
            Answer with source citations
        """
        try:
            yield f"📚 正在搜索文档：**{query}**\n\n"
            
            # Check if documents exist
            if not self.store.documents:
                yield "❌ **知识库中未找到文档。**\n\n"
                yield "请先使用文档管理界面上传文档。\n"
                return
            
            # Search for relevant documents
            relevant_docs = self.store.search(query, top_k=3)
            
            if not relevant_docs:
                yield "❌ **文档中未找到相关信息。**\n\n"
                yield f"知识库包含 {len(self.store.documents)} 个文档，但没有匹配你的查询。\n"
                yield f"提示：尝试使用文档中的具体关键词进行搜索。\n"
                return
            
            yield f"✅ 找到 {len(relevant_docs)} 个相关文档\n\n"
            
            # Build context from relevant documents
            context_parts = []
            for idx, doc in enumerate(relevant_docs, 1):
                context_parts.append(f"[Document {idx}: {doc['filename']}]\n{doc['content']}\n")
            
            context = "\n---\n".join(context_parts)
            
            # Generate answer using LLM
            yield "## 💡 回答\n\n"
            
            prompt = f"""根据以下文档回答用户的问题。如果文档中没有答案，请明确说明。

文档：
{context}

问题：{query}

请提供清晰、简洁的回答，并引用你使用的文档。使用简体中文回答。"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个有帮助的助手，根据提供的文档回答问题。始终引用你的来源。使用简体中文回答。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            yield "\n\n"
            
            # Show sources
            yield "## 📄 来源\n\n"
            for idx, doc in enumerate(relevant_docs, 1):
                yield f"{idx}. **{doc['filename']}** (ID: {doc['id']})\n"
            
            yield "\n"
            
        except Exception as e:
            yield f"❌ **文档问答错误：** {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    Entry point for the skill
    
    Args:
        params: Dictionary with 'query' key and optional 'document_store'
        
    Yields:
        Q&A results
    """
    query = params.get("query")
    if not query:
        yield "❌ 错误：缺少 'query' 参数\n"
        return
    
    # Get document store from params (passed from app.py)
    document_store = params.get("document_store")
    skill = DocumentQASkill(document_store=document_store)
    yield from skill.execute(query)


def add_document(content: str, filename: str = "document") -> str:
    """Helper function to add documents to the store"""
    return get_document_store().add_document(content, filename)


def get_document_store() -> DocumentStore:
    """Get the global document store (singleton pattern)"""
    global _document_store
    if _document_store is None:
        _document_store = DocumentStore()
    return _document_store


# For testing
if __name__ == "__main__":
    import sys
    
    # Add sample documents
    sample_doc1 = """
    Company Refund Policy
    
    All products can be returned within 30 days of purchase for a full refund.
    Items must be in original condition with tags attached.
    Refunds will be processed within 5-7 business days.
    Shipping costs are non-refundable.
    """
    
    sample_doc2 = """
    Product Warranty Information
    
    All electronics come with a 1-year manufacturer warranty.
    The warranty covers defects in materials and workmanship.
    Accidental damage is not covered.
    Extended warranty options are available at checkout.
    """
    
    add_document(sample_doc1, "refund_policy.txt")
    add_document(sample_doc2, "warranty_info.txt")
    
    test_query = "What is the refund policy?"
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    
    print(f"Testing document_qa skill with query: {test_query}\n")
    print("="*80)
    
    for chunk in run({"query": test_query}):
        print(chunk, end="", flush=True)

# Made with Bob
