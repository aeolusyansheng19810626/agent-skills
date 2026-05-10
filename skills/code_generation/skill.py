"""
コード生成スキル - Groqを使用してユーザー要件に基づいてコードを生成
"""
import os
import sys
from typing import Generator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import groq_client


class CodeGenerationSkill:
    """様々なプログラミング言語でコードを生成"""

    def __init__(self):
        pass
    
    def execute(self, requirement: str, language: str = "Python", ui_lang: str = "zh") -> Generator[str, None, None]:
        """
        コード生成を実行して結果をストリーム
        """
        try:
            lang_names = {"zh": "简体中文", "ja": "日本語", "en": "English"}
            target_lang_name = lang_names.get(ui_lang, "简体中文")
            
            # ステータスメッセージの多言語化
            status_map = {
                "zh": f"💻 正在生成 **{language}** 代码：*{requirement}*",
                "ja": f"💻 **{language}** ｺｰﾄﾞを生成しています：*{requirement}*",
                "en": f"💻 Generating **{language}** code for: *{requirement}*"
            }
            yield status_map.get(ui_lang, status_map["zh"]) + "\n\n"
            yield "---\n\n"
            
            # コード生成用のプロンプトを構築
            prompt = f"""为以下需求生成 {language} 代码：

{requirement}

要求：
1. 编写简洁、文档完善的代码
2. 包含注释解释关键部分
3. 遵循 {language} 最佳实践
4. 代码可直接用于生产环境
5. 适当添加错误处理
6. 如有帮助，添加使用示例

请提供完整、可运行的代码。**所有注释和说明必须使用 {target_lang_name}。**"""

            messages = [
                {"role": "system", "content": f"你是一位专业的 {language} 程序员。生成简洁、高效、文档完善的代码。**所有注释和说明必须使用 {target_lang_name}。**"},
                {"role": "user", "content": prompt},
            ]
            response, warning = groq_client.chat_completion(
                messages, stream=True, temperature=0.2, max_tokens=2000
            )
            if warning:
                yield f"\n\n{warning}\n\n"

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            yield "\n\n"
            yield "---\n\n"
            yield "✅ **代码生成完成！**\n\n"
            
            # 役立つヒントを追加
            yield "### 💡 后续步骤\n\n"
            
            if language.lower() == "python":
                yield "1. 将代码保存为 `.py` 文件\n"
                yield "2. 安装所需依赖\n"
                yield "3. 使用 `python filename.py` 运行\n"
            elif language.lower() in ["javascript", "js"]:
                yield "1. 将代码保存为 `.js` 文件\n"
                yield "2. 使用 `npm install` 安装依赖\n"
                yield "3. 使用 `node filename.js` 运行\n"
            elif language.lower() in ["java"]:
                yield "1. 将代码保存为 `.java` 文件\n"
                yield "2. 使用 `javac filename.java` 编译\n"
                yield "3. 使用 `java ClassName` 运行\n"
            elif language.lower() in ["c++", "cpp"]:
                yield "1. 将代码保存为 `.cpp` 文件\n"
                yield "2. 使用 `g++ filename.cpp -o output` 编译\n"
                yield "3. 使用 `./output` 运行\n"
            else:
                yield "1. 将代码保存为适当的文件\n"
                yield "2. 按照语言特定的编译/执行步骤操作\n"
            
            yield "\n"
            
        except Exception as e:
            yield f"❌ **代码生成错误：** {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    スキルのエントリーポイント
    """
    requirement = params.get("requirement")
    if not requirement:
        yield "❌ Error: Missing 'requirement'\n"
        return
    
    language = params.get("language", "Python")
    ui_lang = params.get("ui_lang", "zh") # 获取注入的语言
    
    skill = CodeGenerationSkill()
    yield from skill.execute(requirement, language, ui_lang)


# テスト用
if __name__ == "__main__":
    import sys
    
    test_requirement = "a function to calculate fibonacci numbers"
    test_language = "Python"
    
    if len(sys.argv) > 1:
        test_requirement = " ".join(sys.argv[1:])
    
    print(f"Testing code_generation skill")
    print(f"Requirement: {test_requirement}")
    print(f"Language: {test_language}\n")
    print("="*80)
    
    for chunk in run({"requirement": test_requirement, "language": test_language}):
        print(chunk, end="", flush=True)

