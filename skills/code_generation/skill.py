"""
Code Generation Skill - Generate code based on user requirements using Groq
"""
import os
from typing import Generator
from groq import Groq


class CodeGenerationSkill:
    """Generate code in various programming languages"""
    
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def execute(self, requirement: str, language: str = "Python") -> Generator[str, None, None]:
        """
        Execute code generation and stream results
        
        Args:
            requirement: Description of what code to generate
            language: Programming language (default: Python)
            
        Yields:
            Generated code with explanation
        """
        try:
            yield f"💻 正在生成 **{language}** 代码：*{requirement}*\n\n"
            yield "---\n\n"
            
            # Build prompt for code generation
            prompt = f"""为以下需求生成 {language} 代码：

{requirement}

要求：
1. 编写简洁、文档完善的代码
2. 包含注释解释关键部分
3. 遵循 {language} 最佳实践
4. 代码可直接用于生产环境
5. 适当添加错误处理
6. 如有帮助，添加使用示例

请提供完整、可运行的代码。使用简体中文注释和说明。"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"你是一位专业的 {language} 程序员。生成简洁、高效、文档完善的代码。所有注释和说明使用简体中文。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
                stream=True
            )
            
            # Stream the code generation
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            yield "\n\n"
            yield "---\n\n"
            yield "✅ **代码生成完成！**\n\n"
            
            # Add helpful tips
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
    Entry point for the skill
    
    Args:
        params: Dictionary with 'requirement' and optional 'language' keys
        
    Yields:
        Generated code
    """
    requirement = params.get("requirement")
    if not requirement:
        yield "❌ 错误：缺少 'requirement' 参数\n"
        return
    
    language = params.get("language", "Python")
    
    skill = CodeGenerationSkill()
    yield from skill.execute(requirement, language)


# For testing
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

# Made with Bob
