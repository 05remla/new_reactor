import re
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

def create_format(color, style='', bg_color=None):
    _color = QColor(color)
    _format = QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    if 'underline' in style:
        _format.setFontUnderline(True)
    if bg_color:
        from PyQt5.QtGui import QBrush
        _format.setBackground(QBrush(QColor(bg_color)))
    return _format

STYLES = {
    'keyword': create_format('#0033B3', 'bold'),      # Blue
    'builtins': create_format('#0055AA'),             # Light Blue
    'operator': create_format('#CC0000'),             # Red
    'defclass': create_format('#000000', 'bold'),     # Black Bold
    'string': create_format('#008000'),               # Green
    'comment': create_format('#8C8C8C', 'italic'),    # Gray Italic
    'numbers': create_format('#1750EB'),              # Blueish
    'bash_var': create_format('#660E7A', 'bold'),     # Purple
    'markdown_code': create_format('#000000'),        # Code Block Text
    'markdown_heading': create_format('#2C3E50', 'bold'),
    'markdown_title': create_format('#1A5276', 'bold underline'),
    'markdown_subtitle': create_format('#2980B9', 'bold underline'),
    'markdown_highlight': create_format('#FF00FF', 'bold'),
    'markdown_bold': create_format('#000000', 'bold'),
    'markdown_italic': create_format('#000000', 'italic'),
    'markdown_link': create_format('#2980B9'),
    'markdown_quote': create_format('#7F8C8D', 'italic'),
    'markdown_inline_code': create_format('#009999'),
    'markdown_list': create_format('#E67E22', 'bold'),
}

# Apply background color to markdown code block
STYLES['markdown_code'].setBackground(QColor('#F5F5F5'))

class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language='python'):
        super().__init__(document)
        self.language = language
        self.rules = []
        
        self.multi_line_comment_start = None
        self.multi_line_comment_end = None
        self.multi_line_comment_format = None
        
        if language == 'python':
            self._setup_python()
        elif language == 'bash':
            self._setup_bash()
        elif language == 'markdown':
            self._setup_markdown()

    def _setup_python(self):
        keywords = [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield',
            'None', 'True', 'False', 'nonlocal', 'async', 'await'
        ]
        builtins = [
            'open', 'list', 'dict', 'set', 'str', 'int', 'float', 'bool', 'type', 'len', 'isinstance'
        ]
        
        self.rules += [(r'\b%s\b' % w, STYLES['keyword']) for w in keywords]
        self.rules += [(r'\b%s\b' % w, STYLES['builtins']) for w in builtins]
        
        # Numbers
        self.rules.append((r'\b[+-]?[0-9]+[lL]?\b', STYLES['numbers']))
        self.rules.append((r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', STYLES['numbers']))
        self.rules.append((r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', STYLES['numbers']))

        # Double-quoted string (negative lookahead to ignore triple quotes)
        self.rules.append((r'"(?!"")[^"\\]*(\\.[^"\\]*)*"', STYLES['string']))
        # Single-quoted string (negative lookahead to ignore triple quotes)
        self.rules.append((r"'(?!'')[^'\\]*(\\.[^'\\]*)*'", STYLES['string']))

        # Class / Def names
        self.rules.append((r'\bclass\b\s*(\w+)', STYLES['defclass']))
        self.rules.append((r'\bdef\b\s*(\w+)', STYLES['defclass']))

        # Comments
        self.rules.append((r'#[^\n]*', STYLES['comment']))
        
        # Decorators
        self.rules.append((r'@[^\n]*', STYLES['defclass']))

        # Multiline strings are handled manually in highlightBlock using states

    def _setup_bash(self):
        keywords = [
            'if', 'fi', 'then', 'elif', 'else', 'for', 'do', 'done',
            'until', 'while', 'break', 'continue', 'case', 'esac',
            'function', 'in', 'eq', 'ne', 'gt', 'lt', 'ge', 'le',
            'echo', 'export', 'source', 'read', 'set', 'unset'
        ]
        
        self.rules += [(r'\b%s\b' % w, STYLES['keyword']) for w in keywords]
        
        # Variables ($VAR or ${VAR})
        self.rules.append((r'\$\w+', STYLES['bash_var']))
        self.rules.append((r'\$\{[^\}]+\}', STYLES['bash_var']))
        
        # Strings
        self.rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', STYLES['string']))
        self.rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", STYLES['string']))
        
        # Comments
        self.rules.append((r'#[^\n]*', STYLES['comment']))

    def _setup_markdown(self):
        self.rules.append((r'^#\s+.*', STYLES['markdown_title']))
        self.rules.append((r'^##\s+.*', STYLES['markdown_subtitle']))
        self.rules.append((r'^#{3,6}\s+.*', STYLES['markdown_heading']))
        
        # Single asterisks and underscores MUST run before double ones 
        # so they get overwritten properly by the stronger double formats!
        self.rules.append((r'\*[^\*\_]+\*', STYLES['markdown_italic']))
        self.rules.append((r'_[^\*\_]+_', STYLES['markdown_italic']))
        
        self.rules.append((r'\*\*[^\*]+\*\*', STYLES['markdown_highlight']))
        self.rules.append((r'__[^_]+__', STYLES['markdown_bold']))
        
        self.rules.append((r'`[^`]+`', STYLES['markdown_inline_code']))
        self.rules.append((r'^>\s+.*', STYLES['markdown_quote']))
        self.rules.append((r'^\s*[\-\*\+]\s+', STYLES['markdown_list']))
        self.rules.append((r'^\s*\d+\.\s+', STYLES['markdown_list']))
        self.rules.append((r'\[[^\]]+\]\([^\)]+\)', STYLES['markdown_link']))

    def highlightBlock(self, text):
        is_md_code_block = False
        if self.language == 'markdown':
            is_md_code_block = self._highlight_markdown_block(text)
            if is_md_code_block:
                return

        # Apply basic Regex rules
        for pattern, format in self.rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
                
        # Handle multi-line strings / comments (e.g. Python ''')
        if self.language == 'python':
            self.setCurrentBlockState(0)
            startIndex = 0
            
            if self.previousBlockState() == 1:
                # Inside '''
                endIndex = QRegExp(r"'''").indexIn(text)
                if endIndex == -1:
                    self.setCurrentBlockState(1)
                    self.setFormat(0, len(text), STYLES['string'])
                    startIndex = -1
                else:
                    self.setFormat(0, endIndex + 3, STYLES['string'])
                    startIndex = endIndex + 3
            elif self.previousBlockState() == 2:
                # Inside \"\"\"
                endIndex = QRegExp(r'\"\"\"').indexIn(text)
                if endIndex == -1:
                    self.setCurrentBlockState(2)
                    self.setFormat(0, len(text), STYLES['string'])
                    startIndex = -1
                else:
                    self.setFormat(0, endIndex + 3, STYLES['string'])
                    startIndex = endIndex + 3

            # Search for new triple quotes
            start_regex = QRegExp(r"'''|\"\"\"")
            while startIndex >= 0:
                startIndex = start_regex.indexIn(text, startIndex)
                if startIndex >= 0:
                    matched = start_regex.cap(0)
                    end_regex = QRegExp(matched)
                    endIndex = end_regex.indexIn(text, startIndex + 3)
                    
                    if endIndex == -1:
                        self.setCurrentBlockState(1 if matched == "'''" else 2)
                        self.setFormat(startIndex, len(text) - startIndex, STYLES['string'])
                        break
                    else:
                        self.setFormat(startIndex, endIndex - startIndex + 3, STYLES['string'])
                        startIndex = endIndex + 3

    def _highlight_markdown_block(self, text):
        self.setCurrentBlockState(0)
        in_block = (self.previousBlockState() == 1)
        
        # We look for a line starting with ``` (ignoring leading whitespace)
        backtick_regex = QRegExp(r"^\s*```")
        
        if not in_block:
            if backtick_regex.indexIn(text) == 0:
                self.setCurrentBlockState(1)
                self.setFormat(0, len(text), STYLES['markdown_code'])
                return True
        else:
            if backtick_regex.indexIn(text) == 0:
                self.setCurrentBlockState(0)
                self.setFormat(0, len(text), STYLES['markdown_code'])
                return True
            else:
                self.setCurrentBlockState(1)
                self.setFormat(0, len(text), STYLES['markdown_code'])
                return True
        return False
