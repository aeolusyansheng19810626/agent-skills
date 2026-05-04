"""
ドキュメントQ&Aスキル - インメモリストレージを使用してアップロードされたドキュメントから質問に回答
"""
import os
import sys
from typing import Generator, List, Dict, Optional
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import groq_client


class DocumentStore:
    """シンプルなインメモリドキュメントストレージ"""
    
    def __init__(self):
        self.documents: List[Dict[str, str]] = []
    
    def add_document(self, content: str, filename: str = "document"):
        """ストアにドキュメントを追加（重複を防止）"""
        doc_id = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # ドキュメントが既に存在するかチェック（IDで）
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc_id  # 既に存在、再度追加しない
        
        # 新しいドキュメントを追加
        self.documents.append({
            "id": doc_id,
            "filename": filename,
            "content": content
        })
        return doc_id
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """中国語サポート向上のため部分文字列マッチングを使用した改善された検索"""
        query_lower = query.lower()
        
        # 複数の基準でドキュメントをスコアリング
        scored_docs = []
        for doc in self.documents:
            content_lower = doc["content"].lower()
            score = 0
            
            # 1. 直接部分文字列マッチ（最優先）
            if query_lower in content_lower:
                score += 100
            
            # 2. 個別文字マッチング（中国語用）
            for char in query_lower:
                if char in content_lower and char.strip():
                    score += 1
            
            # 3. 単語ベースマッチング（英語/混合コンテンツ用）
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            word_overlap = len(query_words & content_words)
            score += word_overlap * 10
            
            if score > 0:
                scored_docs.append((score, doc))
        
        # スコアでソートしてtop_kを返す
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        return [doc for _, doc in scored_docs[:top_k]]
    
    def get_all_documents(self) -> List[Dict[str, str]]:
        """すべてのドキュメントを取得"""
        return self.documents
    
    def remove_document(self, doc_id: str):
        """IDで単一のドキュメントを削除"""
        self.documents = [d for d in self.documents if d["id"] != doc_id]

    def clear(self):
        """すべてのドキュメントをクリア"""
        self.documents.clear()


# グローバルドキュメントストア - get_document_store()で初期化される
_document_store = None


class DocumentQASkill:
    """RAGアプローチを使用してドキュメントから質問に回答"""
    
    def __init__(self, document_store: Optional[DocumentStore] = None):
        self.store = document_store if document_store is not None else get_document_store()
    
    def execute(self, query: str) -> Generator[str, None, None]:
        """
        ドキュメントQ&Aを実行して結果をストリーム
        
        Args:
            query: ユーザーの質問
            
        Yields:
            ソース引用付きの回答
        """
        try:
            yield f"📚 正在搜索文档：**{query}**\n\n"
            
            # ドキュメントが存在するかチェック
            if not self.store.documents:
                yield "❌ **知识库中未找到文档。**\n\n"
                yield "请先使用文档管理界面上传文档。\n"
                return
            
            # 関連ドキュメントを検索
            relevant_docs = self.store.search(query, top_k=3)
            
            if not relevant_docs:
                yield "❌ **文档中未找到相关信息。**\n\n"
                yield f"知识库包含 {len(self.store.documents)} 个文档，但没有匹配你的查询。\n"
                yield f"提示：尝试使用文档中的具体关键词进行搜索。\n"
                return
            
            yield f"✅ 找到 {len(relevant_docs)} 个相关文档\n\n"
            
            # 関連ドキュメントからコンテキストを構築
            context_parts = []
            for idx, doc in enumerate(relevant_docs, 1):
                context_parts.append(f"[Document {idx}: {doc['filename']}]\n{doc['content']}\n")
            
            context = "\n---\n".join(context_parts)
            
            # LLMを使用して回答を生成
            yield "## 💡 回答\n\n"
            
            prompt = f"""根据以下文档回答用户的问题。如果文档中没有答案，请明确说明。

文档：
{context}

问题：{query}

请提供清晰、简洁的回答，并引用你使用的文档。使用简体中文回答。"""

            messages = [
                {"role": "system", "content": "你是一个有帮助的助手，根据提供的文档回答问题。始终引用你的来源。使用简体中文回答。"},
                {"role": "user", "content": prompt},
            ]
            response, warning = groq_client.chat_completion(
                messages, stream=True, temperature=0.3, max_tokens=1000
            )
            if warning:
                yield f"\n\n{warning}\n\n"

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            yield "\n\n"
            
            # ソースを表示
            yield "## 📄 来源\n\n"
            for idx, doc in enumerate(relevant_docs, 1):
                yield f"{idx}. **{doc['filename']}** (ID: {doc['id']})\n"
            
            yield "\n"
            
        except Exception as e:
            yield f"❌ **文档问答错误：** {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    スキルのエントリーポイント
    
    Args:
        params: 'query'キーとオプションの'document_store'を含む辞書
        
    Yields:
        Q&A結果
    """
    query = params.get("query")
    if not query:
        yield "❌ 错误：缺少 'query' 参数\n"
        return
    
    # paramsからドキュメントストアを取得（app.pyから渡される）
    document_store = params.get("document_store")
    skill = DocumentQASkill(document_store=document_store)
    yield from skill.execute(query)


def add_document(content: str, filename: str = "document") -> str:
    """ストアにドキュメントを追加するヘルパー関数"""
    return get_document_store().add_document(content, filename)


def get_document_store() -> DocumentStore:
    """グローバルドキュメントストアを取得（シングルトンパターン）"""
    global _document_store
    if _document_store is None:
        _document_store = DocumentStore()
    return _document_store


# テスト用
if __name__ == "__main__":
    import sys
    
    # サンプルドキュメントを追加
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

