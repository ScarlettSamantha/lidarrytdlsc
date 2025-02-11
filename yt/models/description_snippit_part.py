from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class DescriptionSnippetPart:
    text: str
    bold: Optional[bool] = None  # Bold might not be present in all parts
    
    @classmethod
    def parse_description_snippet(cls, snippet_list: List[Dict]) -> List["DescriptionSnippetPart"]:
        return [DescriptionSnippetPart(**snippet) for snippet in snippet_list]