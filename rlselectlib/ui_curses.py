# Copyright (C) 2017  Rickard Lindberg
#
# This file is part of rlselect.
#
# rlselect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# rlselect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with rlselect.  If not, see <http://www.gnu.org/licenses/>.


import contextlib
import curses
import locale
import os
import sys

from rlselectlib.unicode import BS, CR


COLOR_MAP = {
    "BACKGROUND": -1,
    "FOREGROUND": -1,
    "BLACK": curses.COLOR_BLACK,
    "BLUE": curses.COLOR_BLUE,
    "CYAN": curses.COLOR_CYAN,
    "GREEN": curses.COLOR_GREEN,
    "MAGENTA": curses.COLOR_MAGENTA,
    "RED": curses.COLOR_RED,
    "WHITE": curses.COLOR_WHITE,
    "YELLOW": curses.COLOR_YELLOW,
}


def curses_ui_run(config, controller):
    with _redirect_terminal():
        return curses.wrapper(_run, config, controller)


@contextlib.contextmanager
def _redirect_terminal():
    stdin_fileno = sys.stdin.fileno()
    stdout_fileno = sys.stdout.fileno()
    process_stdin = os.dup(sys.stdin.fileno())
    process_stdout = os.dup(sys.stdout.fileno())
    try:
        terminal_stdin = open("/dev/tty", "rb")
        terminal_stdout = open("/dev/tty", "wb")
        os.dup2(terminal_stdin.fileno(), stdin_fileno)
        os.dup2(terminal_stdout.fileno(), stdout_fileno)
        yield
    finally:
        os.dup2(process_stdin, stdin_fileno)
        os.dup2(process_stdout, stdout_fileno)


def _run(screen, config, controller):
    curses.raw()
    if curses.has_colors():
        curses.use_default_colors()
        curses.init_pair(
            1,
            COLOR_MAP[config.get_highlight_fg()],
            COLOR_MAP[config.get_highlight_bg()],
        )
        curses.init_pair(
            2,
            COLOR_MAP[config.get_selection_fg()],
            COLOR_MAP[config.get_selection_bg()]
        )
    controller.setup(screen)
    return _loop(controller, screen)


def _loop(controller, screen):
    patched_screen = _Screen(screen)
    buf = ""
    while True:
        controller.render(patched_screen)
        ch = screen.getch()
        if ch > 255:
            if ch == curses.KEY_BACKSPACE:
                buf = BS.encode(locale.getpreferredencoding())
            elif ch == curses.KEY_ENTER:
                buf = CR.encode(locale.getpreferredencoding())
            else:
                buf = ""
                continue
        else:
            buf += chr(ch)
        try:
            unicode_character = buf.decode(locale.getpreferredencoding())
        except UnicodeDecodeError:
            # We are dealing with an incomplete multi-byte character.
            pass
        else:
            buf = ""
            result = controller.process_input(unicode_character)
            if result:
                return result


class _Screen(object):

    def __init__(self, curses_screen):
        self._curses_screen = curses_screen

    def getmaxyx(self):
        return self._curses_screen.getmaxyx()

    def erase(self):
        return self._curses_screen.erase()

    def addstr(self, y, x, text, style):
        if style == "highlight":
            attrs = curses.A_BOLD
            if curses.has_colors():
                attrs |= curses.color_pair(1)
        elif style == "select":
            attrs = curses.A_BOLD
            if curses.has_colors():
                attrs |= curses.color_pair(2)
        elif style == "status":
            attrs = curses.A_REVERSE | curses.A_BOLD
        else:
            attrs = 0
        try:
            self._curses_screen.addstr(y, x, self._encode(text), attrs)
        except curses.error:
            # Writing last position (max_y, max_x) fails, but we can ignore it.
            pass

    def refresh(self):
        return self._curses_screen.refresh()

    def _encode(self, text):
        return text.encode(locale.getpreferredencoding())
