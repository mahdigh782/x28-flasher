"""Turn ConPTY's ANSI output into the plain line/prompt stream used by the page."""


class TerminalText:
    def __init__(self):
        self.escape = ""
        self.cr = False

    def feed(self, text, final=False):
        out = []
        for ch in text:
            if self.escape:
                self.escape += ch
                if self.escape.startswith('\x1b['):
                    done = len(self.escape) > 2 and '@' <= ch <= '~'
                elif self.escape.startswith('\x1b]'):
                    done = ch == '\a' or self.escape.endswith('\x1b\\')
                else:
                    done = len(self.escape) >= 2 and ch not in '[]'
                if done or len(self.escape) > 4096:
                    self.escape = ""
                continue
            if ch == '\x1b':
                self.escape = ch
                continue
            if self.cr:
                out.append('\n' if ch == '\n' else '\r')
                self.cr = False
                if ch == '\n':
                    continue
            if ch == '\r':
                self.cr = True
            else:
                out.append(ch)
        if final and self.cr:
            out.append('\r')
            self.cr = False
        return ''.join(out)
