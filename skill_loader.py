"""
Skill Loader - Automatically scans and registers skills from the skills/ directory
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
import re


class SkillLoader:
    """Loads and manages skill definitions from skill.md files"""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Dict] = {}
        self._load_skills()
    
    def _load_skills(self):
        """Scan skills directory and load all skill.md files"""
        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Skills directory not found: {self.skills_dir}")
        
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md_path = skill_dir / "skill.md"
                if skill_md_path.exists():
                    skill_name = skill_dir.name
                    skill_data = self._parse_skill_md(skill_md_path)
                    skill_data['name'] = skill_name
                    skill_data['path'] = str(skill_dir)
                    self.skills[skill_name] = skill_data
                    print(f"✓ Loaded skill: {skill_name}")
    
    def _parse_skill_md(self, md_path: Path) -> Dict:
        """Parse skill.md file and extract metadata"""
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        skill_data = {
            'description': '',
            'trigger_conditions': [],
            'non_trigger_conditions': [],
            'parameters': [],
            'returns': '',
            'full_content': content
        }
        
        # Extract description
        desc_match = re.search(r'## 描述\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if desc_match:
            skill_data['description'] = desc_match.group(1).strip()
        
        # Extract trigger conditions
        trigger_match = re.search(r'## 触发条件\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if trigger_match:
            triggers = trigger_match.group(1).strip()
            skill_data['trigger_conditions'] = [
                line.strip('- ').strip() 
                for line in triggers.split('\n') 
                if line.strip().startswith('-')
            ]
        
        # Extract non-trigger conditions
        non_trigger_match = re.search(r'## 不触发条件\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if non_trigger_match:
            non_triggers = non_trigger_match.group(1).strip()
            skill_data['non_trigger_conditions'] = [
                line.strip('- ').strip() 
                for line in non_triggers.split('\n') 
                if line.strip().startswith('-')
            ]
        
        # Extract parameters
        params_match = re.search(r'## 参数\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if params_match:
            params = params_match.group(1).strip()
            skill_data['parameters'] = [
                line.strip('- ').strip() 
                for line in params.split('\n') 
                if line.strip().startswith('-')
            ]
        
        # Extract returns
        returns_match = re.search(r'## 返回\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if returns_match:
            skill_data['returns'] = returns_match.group(1).strip()
        
        return skill_data
    
    def get_skill(self, skill_name: str) -> Optional[Dict]:
        """Get skill metadata by name"""
        return self.skills.get(skill_name)
    
    def get_all_skills(self) -> Dict[str, Dict]:
        """Get all loaded skills"""
        return self.skills
    
    def get_skill_names(self) -> List[str]:
        """Get list of all skill names"""
        return list(self.skills.keys())
    
    def get_skills_summary(self) -> str:
        """Generate a summary of all skills for router prompt"""
        summary_parts = []
        
        for skill_name, skill_data in self.skills.items():
            summary = f"""
### Skill: {skill_name}
**Description:** {skill_data['description']}

**Trigger Conditions:**
{chr(10).join(f"- {cond}" for cond in skill_data['trigger_conditions'])}

**Non-Trigger Conditions:**
{chr(10).join(f"- {cond}" for cond in skill_data['non_trigger_conditions'])}

**Parameters:**
{chr(10).join(f"- {param}" for param in skill_data['parameters'])}

**Returns:** {skill_data['returns']}
"""
            summary_parts.append(summary.strip())
        
        return "\n\n---\n\n".join(summary_parts)
    
    def import_skill_module(self, skill_name: str):
        """Dynamically import skill.py module"""
        if skill_name not in self.skills:
            raise ValueError(f"Skill not found: {skill_name}")
        
        skill_path = Path(self.skills[skill_name]['path'])
        skill_py = skill_path / "skill.py"
        
        if not skill_py.exists():
            raise FileNotFoundError(f"skill.py not found for {skill_name}")
        
        # Dynamic import
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"skills.{skill_name}.skill", skill_py)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load spec for {skill_name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module


# Singleton instance
_loader_instance = None

def get_skill_loader() -> SkillLoader:
    """Get or create skill loader singleton"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SkillLoader()
    return _loader_instance


if __name__ == "__main__":
    # Test the loader
    loader = SkillLoader()
    print(f"\n📦 Loaded {len(loader.skills)} skills:")
    for name in loader.get_skill_names():
        print(f"  - {name}")
    
    print("\n" + "="*80)
    print("SKILLS SUMMARY FOR ROUTER:")
    print("="*80)
    print(loader.get_skills_summary())

# Made with Bob
