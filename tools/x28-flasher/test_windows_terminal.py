"""ConPTY stream decoding, tested on every platform without Windows hardware."""
import unittest

from windows_terminal import TerminalText


class TerminalTextTests(unittest.TestCase):
    def test_ansi_and_crlf_are_removed_even_across_read_boundaries(self):
        text = '\x1b[?25l\x1b[2J\x1b[Hhello\r\n\x1b]0;title\x07Pick: \x1b[?25h'
        for width in range(1, len(text) + 1):
            terminal = TerminalText()
            out = ''.join(terminal.feed(text[i:i + width]) for i in range(0, len(text), width))
            self.assertEqual(out + terminal.feed('', final=True), 'hello\nPick: ')

    def test_progress_redraw_and_unicode_are_preserved(self):
        terminal = TerminalText()
        self.assertEqual(terminal.feed('10%\r'), '10%')
        self.assertEqual(terminal.feed('✓ 100%\r\n'), '\r✓ 100%\n')
        self.assertEqual(terminal.feed('\x1b]0;title\x1b\\end'), 'end')


if __name__ == '__main__':
    unittest.main()
