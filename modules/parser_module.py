class ResumeParser:
    """Simple parser that uses your semantic modules"""
    
    def __init__(self):
        from .resume_analyzer import ResumeAnalyzer
        self.analyzer = ResumeAnalyzer(None)  # Pass config if needed
    
    def extract_sections(self, text):
        """Extract sections from resume"""
        # Use your semantic analyzer
        return self.analyzer._extract_sections_ml(text) if hasattr(self.analyzer, '_extract_sections_ml') else {}