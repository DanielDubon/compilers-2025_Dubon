from antlr4.error.ErrorListener import ErrorListener
import sys

class PrettyErrorListener(ErrorListener):
    def __init__(self, source_lines=None, use_color=None):
        super().__init__()
        self.errors = []
        self.source_lines = source_lines or []
        
        self.use_color = sys.stdout.isatty() if use_color is None else bool(use_color)

        self.RED = "\033[91m"
        self.YELLOW = "\033[93m"
        self.BOLD = "\033[1m"
        self.DIM = "\033[2m"
        self.RESET = "\033[0m"

    def _c(self, text, code):
        return f"{code}{text}{self.RESET}" if self.use_color else text

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        tok = getattr(offendingSymbol, "text", "")
        
        print(self._c(f"Error sintactico (linea {line}, columna {column})", self.RED + self.BOLD))

        
        if 1 <= line <= len(self.source_lines):
            src = self.source_lines[line - 1].rstrip("\n")
            print(self._c("    " + src, self.DIM))
            print(self._c("    " + (" " * column) + "^", self.YELLOW + self.BOLD))

        # Mensaje corto
        if tok:
            print("  " + self._c(f"Token '{tok}': {msg}", self.YELLOW))
        else:
            print("  " + self._c(msg, self.YELLOW))

        self.errors.append((line, column, msg))
