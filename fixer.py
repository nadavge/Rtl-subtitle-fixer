import argparse
from collections import namedtuple
import re

SrtLine = namedtuple("SrtLine", ["sequence", "timing", "text"]) 
SPECIAL_CHARS_RE_SET = r'.,:;\'()\-?!+=*&$^%#@~`" \/'

class DecodeError(Exception): pass


def parse_args(args: list[str]) -> argparse.Namespace:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("file")

    return argparser.parse_args(args)


def get_file_lines(file: str) -> list[str]:
    try:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            if "י" in content:
                return content.splitlines()

    except UnicodeDecodeError:
        pass

    with open(file, "r", encoding="cp1255") as f:
            content = f.read()
            if "י" in content:
                return content.splitlines()
            
            raise DecodeError()


class SrtParser:

    STATE_SEQ = 1
    STATE_TIMING = 2
    STATE_TEXT = 3

    def __init__(self):
        self._seq = ""
        self._timing = ""
        self._text = []
        self._state = SrtParser.STATE_SEQ
        self._lines = []

    def _handle_line(self, line):
        if self._state == SrtParser.STATE_SEQ:
            self._handle_seq(line)
        elif self._state == SrtParser.STATE_TIMING:
            self._handle_timing(line)
        elif self._state == SrtParser.STATE_TEXT:
            self._handle_text(line)
    
    def _handle_seq(self, line: str):
        self._seq = line
        self._state = SrtParser.STATE_TIMING
    
    def _handle_timing(self, line: str):
        self._timing = line
        self._state = SrtParser.STATE_TEXT

    def _handle_text(self, line: str):
        if line.strip() == "":
            self._lines.append(SrtLine(self._seq, self._timing, self._text))
            self._text = []
            self._state = SrtParser.STATE_SEQ
        else:
            self._text.append(line)

    def parse_lines(self, lines: list[str]) -> list[SrtLine]:
        for line in lines:
            self._handle_line(line)
        
        # Handle new new line at the end of the file
        if self._state == SrtParser.STATE_TEXT:
            self._handle_text("")

        return self._lines[:]

    @property
    def lines(self):
        return self._lines[:]

class SrtWriter:

    def __init__(self, file: str):
        self._file = open(file, "w", encoding="utf-8")

    def write_lines(self, subtitles: list[SrtLine]):
        for i, sub in enumerate(subtitles):
            self._file.write(sub.sequence + "\n")
            self._file.write(sub.timing + "\n")

            for line in sub.text:
                self._file.write(line + '\n')

            if i != len(subtitles)-1:
                self._file.write("\n")

    def close(self):
        self._file.close()

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, tb):
        self.close()


def fix_line(line: str) -> str:
    prefix_match = re.search(f"^([{SPECIAL_CHARS_RE_SET}]*)", line)
    suffix_match = re.search(f"[^{SPECIAL_CHARS_RE_SET}]([{SPECIAL_CHARS_RE_SET}]*)$", line)
    prefix = prefix_match.group(1) if prefix_match else ""
    suffix = suffix_match.group(1) if suffix_match else ""

    # Ad-hoc fix for quotation lines
    if suffix.endswith(" -"):
        suffix = suffix[:-2] + "- "

    return suffix + line[len(prefix):len(line)-len(suffix)] + prefix


def fix_subtitles(subtitles: list[SrtLine]) -> list[SrtLine]:
    new_subtitles = []
    for subtitle_line in subtitles:
        new_text = [fix_line(text_line) for text_line in subtitle_line.text]
        new_subtitles.append(
            SrtLine(
                subtitle_line.sequence,
                subtitle_line.timing,
                new_text
            )
        )

    return new_subtitles


def main(args: argparse.Namespace):
    lines = get_file_lines(args.file)
    srt_parser = SrtParser()
    subtitles = srt_parser.parse_lines(lines)

    modified_subtitles = fix_subtitles(subtitles)
    with SrtWriter(args.file[:-3]+"fix.srt") as srt_writer:
        srt_writer.write_lines(modified_subtitles)

if __name__=="__main__":
    import sys
    
    args = parse_args(sys.argv[1:])
    main(args)