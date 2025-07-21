import re
from typing import List

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using basic regex
    """
    # Basic sentence splitting - can be enhanced with more sophisticated NLP
    sentences = re.split(r'[.!?]+', text)
    
    # Clean up sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def format_qa_pairs(pairs: List[tuple]) -> str:
    """
    Format question-answer pairs into the specified format
    """
    formatted_lines = []
    
    for question, answer in pairs:
        formatted_lines.append(f"Question: {question}")
        formatted_lines.append(f"Answer: {answer}")
        formatted_lines.append("")  # Empty line separator
    
    return "\n".join(formatted_lines).strip()