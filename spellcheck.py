import os
import re
import sys
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt5.QtCore import Qt

class SpellCheckHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter subclass that performs real-time spell checking.
    
    It highlights misspelled words with a red wavy underline. It attempts to load
    'pyenchant' first, falling back to 'pyspellchecker', and degrades gracefully
    if neither is installed.
    """
    def __init__(self, parent_document):
        super().__init__(parent_document)
        
        # Define the format for misspelled words (red wavy underline)
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor(Qt.red))
        self.error_format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        
        # Regex to match words (letters and apostrophes)
        self.word_pattern = re.compile(r"\b[a-zA-Z']+\b")
        
        # Load spell checking library
        self.spellchecker = None
        
        # Attempt Option 1: pyenchant (fast C-based library)
        try:
            import enchant
            self.spellchecker = enchant.Dict("en_US")
        except ImportError:
            # Attempt Option 2: pyspellchecker (pure Python library)
            try:
                from spellchecker import SpellChecker
                self.spellchecker = SpellChecker()
            except ImportError:
                # Fallback: log a notice on stderr so the user knows they can install it
                print(
                    "[SpellCheck] Notice: Neither 'pyenchant' nor 'pyspellchecker' is installed. "
                    "Spell checking will be disabled. Run 'pip install pyspellchecker' to enable it.",
                    file=sys.stderr
                )

    def highlightBlock(self, text):
        if not self.spellchecker:
            return
            
        # Match each word in the text block
        for match in self.word_pattern.finditer(text):
            word = match.group()
            
            # Skip checking short words or numbers
            if len(word) <= 1:
                continue
                
            is_correct = True
            
            # Check the dictionary using the available library interface
            if hasattr(self.spellchecker, "check"):  # pyenchant
                try:
                    is_correct = self.spellchecker.check(word)
                except Exception:
                    is_correct = True
            elif hasattr(self.spellchecker, "unknown"):  # pyspellchecker
                try:
                    is_correct = len(self.spellchecker.unknown([word])) == 0
                except Exception:
                    is_correct = True
                
            # If misspelled, apply the red wavy underline
            if not is_correct:
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, self.error_format)
