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
            done_map = {
                "zh": "✅ **代码生成完成！**",
                "ja": "✅ **ｺｰﾄﾞの生成が完了しました！**",
                "en": "✅ **Code generation complete!**"
            }
            yield done_map.get(ui_lang, done_map["zh"]) + "\n\n"
            
            # 役立つヒントを追加
            steps_label = {"zh": "### 💡 后续步骤", "ja": "### 💡 次のｽﾃｯﾌﾟ", "en": "### 💡 Next Steps"}
            yield steps_label.get(ui_lang, steps_label["zh"]) + "\n\n"
            
            if language.lower() == "python":
                if ui_lang == "ja":
                    yield "1. ｺｰﾄﾞを `.py` ﾌｧｲﾙとして保存します\n2. 必要な依存関係をｲﾝｽﾄｰﾙします\n3. `python filename.py` で実行します\n"
                elif ui_lang == "en":
                    yield "1. Save the code as a `.py` file\n2. Install required dependencies\n3. Run with `python filename.py`\n"
                else:
                    yield "1. 将代码保存为 `.py` 文件\n2. 安装所需依赖\n3. 使用 `python filename.py` 运行\n"
            elif language.lower() in ["javascript", "js"]:
                if ui_lang == "ja":
                    yield "1. ｺｰﾄﾞを `.js` ﾌｧｲﾙとして保存します\n2. `npm install` で依存関係をｲﾝｽﾄｰﾙします\n3. `node filename.js` で実行します\n"
                elif ui_lang == "en":
                    yield "1. Save the code as a `.js` file\n2. Install dependencies with `npm install`\n3. Run with `node filename.js`\n"
                else:
                    yield "1. 将代码保存为 `.js` 文件\n2. 使用 `npm install` 安装依赖\n3. 使用 `node filename.js` 运行\n"
            else:
                if ui_lang == "ja":
                    yield "1. ｺｰﾄﾞを適切なﾌｧｲﾙとして保存します\n2. 実行手順に従ってください\n"
                elif ui_lang == "en":
                    yield "1. Save the code as an appropriate file\n2. Follow execution steps\n"
                else:
                    yield "1. 将代码保存为适当的文件\n2. 按照执行步骤操作\n"
            
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

