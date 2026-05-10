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
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc_id
        self.documents.append({
            "id": doc_id,
            "filename": filename,
            "content": content
        })
        return doc_id
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """部分文字列マッチングを使用した検索"""
        query_lower = query.lower()
        scored_docs = []
        for doc in self.documents:
            content_lower = doc["content"].lower()
            score = 0
            if query_lower in content_lower:
                score += 100
            for char in query_lower:
                if char in content_lower and char.strip():
                    score += 1
            if score > 0:
                scored_docs.append((score, doc))
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        return [doc for _, doc in scored_docs[:top_k]]

    def get_all_documents(self) -> List[Dict[str, str]]:
        return self.documents
    
    def remove_document(self, doc_id: str):
        self.documents = [d for d in self.documents if d["id"] != doc_id]

    def clear(self):
        self.documents.clear()


_document_store = None


class DocumentQASkill:
    """RAGアプローチを使用してドキュメントから質問に回答"""
    
    def __init__(self, document_store: Optional[DocumentStore] = None):
        self.store = document_store if document_store is not None else get_document_store()
    
    def execute(self, query: str, ui_lang: str = "zh") -> Generator[str, None, None]:
        """
        ドキュメントQ&Aを実行して結果をストリーム
        """
        try:
            lang_names = {"zh": "简体中文", "ja": "日本語", "en": "English"}
            target_lang = lang_names.get(ui_lang, "简体中文")
            
            status_map = {
                "zh": f"📚 正在搜索文档：**{query}**",
                "ja": f"📚 ﾄﾞｷｭﾒﾝﾄを検索中：**{query}**",
                "en": f"📚 Searching documents for: **{query}**"
            }
            yield status_map.get(ui_lang, status_map["zh"]) + "\n\n"
            
            if not self.store.documents:
                err_map = {
                    "zh": "❌ **知识库中未找到文档。**\n\n请先上传文档。",
                    "ja": "❌ **ﾅﾚｯｼﾞﾍﾞｰｽにﾄﾞｷｭﾒﾝﾄが見つかりません。**\n\n先にｱｯﾌﾟﾛｰﾄﾞしてください。",
                    "en": "❌ **No documents found in knowledge base.**\n\nPlease upload documents first."
                }
                yield err_map.get(ui_lang, err_map["zh"]) + "\n"
                return
            
            relevant_docs = self.store.search(query, top_k=3)
            
            if not relevant_docs:
                none_map = {
                    "zh": "❌ **未找到相关信息。**",
                    "ja": "❌ **関連情報が見つかりませんでした。**",
                    "en": "❌ **No relevant information found.**"
                }
                yield none_map.get(ui_lang, none_map["zh"]) + "\n"
                return
            
            found_map = {
                "zh": f"✅ 找到 {len(relevant_docs)} 个相关文档",
                "ja": f"✅ {len(relevant_docs)} 件の関連ﾄﾞｷｭﾒﾝﾄが見つかりました",
                "en": f"✅ Found {len(relevant_docs)} relevant documents"
            }
            yield found_map.get(ui_lang, found_map["zh"]) + "\n\n"
            
            context_parts = []
            for idx, doc in enumerate(relevant_docs, 1):
                context_parts.append(f"[Document {idx}: {doc['filename']}]\n{doc['content']}\n")
            context = "\n---\n".join(context_parts)
            
            ans_hdr = {"zh": "## 💡 回答", "ja": "## 💡 回答", "en": "## 💡 Answer"}
            yield ans_hdr.get(ui_lang, ans_hdr["zh"]) + "\n\n"
            
            prompt = f"""根据以下文档回答问题。
文档：
{context}

问题：{query}

请引用来源。**请使用 {target_lang} 回答。**"""

            messages = [
                {"role": "system", "content": f"你是一个 RAG 助手。始终引用来源。请使用 **{target_lang}** 回答。"},
                {"role": "user", "content": prompt},
            ]
            response, warning = groq_client.chat_completion(
                messages, stream=True, temperature=0.3, max_tokens=1000
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            src_hdr = {"zh": "## 📄 来源", "ja": "## 📄 出典", "en": "## 📄 Sources"}
            yield "\n\n" + src_hdr.get(ui_lang, src_hdr["zh"]) + "\n\n"
            for idx, doc in enumerate(relevant_docs, 1):
                yield f"{idx}. **{doc['filename']}**\n"
            
        except Exception as e:
            yield f"❌ Error: {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """スキルのエントリーポイント"""
    query = params.get("query")
    if not query:
        yield "❌ Error: 'query' is required\n"
        return
    
    document_store = params.get("document_store")
    ui_lang = params.get("ui_lang", "zh")
    skill = DocumentQASkill(document_store=document_store)
    yield from skill.execute(query, ui_lang)


def add_document(content: str, filename: str = "document") -> str:
    return get_document_store().add_document(content, filename)


def get_document_store() -> DocumentStore:
    global _document_store
    if _document_store is None:
        _document_store = DocumentStore()
    return _document_store
