import os
import re
import srt
import timeit
import logging

from srt import Subtitle
from typing import List, Generator

from .translators.base import Translator

logger = logging.getLogger(__name__)


class SrtFile:
    """SRT file class abstraction

    Args:
        filepath (str): file path of srt
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.backup_file = f"{self.filepath}.tmp"
        #
        self.subtitles = []
        self.length = 0
        print(f"Loading {filepath}")
        # from bs4.dammit import UnicodeDammit
        # with open(filepath, 'rb') as file:
        #     content = file.read()
        # suggestion = UnicodeDammit(content)
        # encode = suggestion.original_encoding
        with open(filepath, "r", encoding="utf-8", errors="ignore") as input_file:
            srt_file = srt.parse(input_file)
            subtitles = list(srt_file)
            subtitles = list(srt.sort_and_reindex(subtitles))
            self.subtitles = self._clean_subs_content(subtitles)
            self.length = sum(len(sub.content) + 1 for sub in self.subtitles)

    def _load_backup(self):
        if not os.path.exists(self.backup_file):
            return

        print(f"Backup file found = {self.backup_file}")
        with open(
                self.backup_file, "r", encoding="utf-8", errors="ignore"
        ) as input_file:
            subtitles = self.load_from_file(input_file)

            self.start_from = len(subtitles)
            self.current_subtitle = self.start_from
            print(f"Starting from subtitle {self.start_from}")
            self.subtitles = [
                *subtitles,
                *self.subtitles[self.start_from :],
            ]

    def load_from_file(self, input_file):
        srt_file = srt.parse(input_file)
        subtitles = list(srt_file)
        subtitles = list(srt.sort_and_reindex(subtitles))
        return self._clean_subs_content(subtitles)

    def _get_next_chunk(self, chunk_size: int = 4500) -> Generator:
        """Get a portion of the subtitles at the time based on the chunk size

        Args:
            chunk_size (int, optional): Maximum number of letter in text chunk. Defaults to 4500.

        Yields:
            Generator: Each chunk at the time
        """
        portion = []
        lengthPortion = 0
        for subtitle in self.subtitles:
            # Calculate new chunk size if subtitle content is added to actual chunk
            n_char = (
                # sum(len(sub.content) for sub in portion)  # All subtitles in chunk
                    + ((sum(len(line) for line in subtitle.content)+ len(subtitle.content))
                       if (isinstance(subtitle.content, list)) else (len(subtitle.content)+1))  # New subtitle
                    #+ len(subtitle.content)  # + len(portion)  # Break lines in chunk
                    + 1 # (len(f"[000_{subtitle.index}_000]") + 1) #  5  # 1 New breakline and 4 size for number and breakline number
            )

            # If chunk goes beyond the limit, yield it
            if n_char + lengthPortion >= chunk_size and len(portion) != 0:
                # logger.info( f"Length ------------------------------------------------- lengthPortion {lengthPortion}")
                # abbbb = [
                #     (
                #             (
                #                 (sum(len(line) for line in abc.content) + len(abc.content))
                #                 if (isinstance(abc.content, list)) else (len(abc.content) + 1)
                #             )
                #             +  1
                #     )
                #     for abc in portion
                # ]
                #
                #
                # text = [(f"\n" + ("\n".join(sub.content)))
                #         if isinstance(sub.content,list)
                #         else f"\n{sub.content}"
                #         for sub in portion]
                # text = "\n".join(text)
                #
                # if len(text) > chunk_size:
                #     logger.info(
                #         f"ERROR Please check data split ............................................................ len(text) {len(text)}  {sum(abbbb)}")
                yield portion
                portion = []
                lengthPortion = 0

            # Put subtitle content in chunk
            portion.append(subtitle)
            lengthPortion += n_char

        # Yield last chunk
        yield portion

    def _clean_subs_content(self, subtitles: List[Subtitle]) -> List[Subtitle]:
        """Cleans subtitles content and delete line breaks

        Args:
            subtitles (List[Subtitle]): List of subtitles

        Returns:
            List[Subtitle]: Same list of subtitles, but cleaned
        """
        cleanr = re.compile("<.*?>")
        import codecs
        for sub in subtitles:
            sub.content = cleanr.sub("", sub.content)
            sub.content = sub.content.strip() \
                .replace("'", "")\
                .replace("`", "")\
                .replace('（', "(")\
                .replace('）', ")")\
                .replace("\\n", "\n")\
                .replace("\\N", "\n")\
                .replace("\\ ", "\n")\
                .replace("\\", "\n")\
                .replace("\\ n", "\n")\
                .replace("\\ N", "\n") # "\n", "\N", "\ ", "\ N", "\ n"
            sub.content = srt.make_legal_content(sub.content)

            if sub.content == "":
                sub.content = "..."

            # if all(sentence.startswith("-") for sentence in sub.content.split("\n")):
            #     sub.content = sub.content.replace("\n", "_")
            #     continue

            # NTT sub.content = sub.content.replace("\n", " ")
            sub.content = list(sub.content.strip().split("\n"))

        return subtitles

    def join_lines(self) -> None:
        """Re-single str lines in all subtitles multi line list type in file
        """
        for sub in self.subtitles:
            sub.content = (str("\n".join(sub.content)) if isinstance(sub.content, list) else sub.content) \
                .replace('("', "(").replace('（"', "(").replace('（', "(") \
                .replace('")', ")").replace('.)', ")")

    def wrap_lines(self, line_wrap_limit: int = 50) -> None:
        """Wrap lines in all subtitles in file

        Args:
            line_wrap_limit (int): Number of maximum characters in a line before wrap. Defaults to 50.
        """
        for sub in self.subtitles:
            sub.content = sub.content.replace("_-", "\n-")

            content = []
            for line in sub.content.split("\n"):
                if len(line) > line_wrap_limit:
                    line = self.wrap_line(line, line_wrap_limit)
                content.append(line)

            sub.content = "\n".join(content)

    def wrap_line(self, text: str, line_wrap_limit: int = 50) -> str:
        """Wraps a line of text without breaking any word in half

        Args:
            text (str): Line text to wrap
            line_wrap_limit (int): Number of maximum characters in a line before wrap. Defaults to 50.

        Returns:
            str: Text line wraped
        """
        wraped_lines = []
        for word in text.split():
            # Check if inserting a word in the last sentence goes beyond the wrap limit
            if (
                    len(wraped_lines) != 0
                    and len(wraped_lines[-1]) + len(word) < line_wrap_limit
            ):
                # If not, add it to it
                wraped_lines[-1] += f" {word}"
                continue

            # Insert a new sentence
            wraped_lines.append(f"{word}")

        # Join sentences with line break
        return "\n".join(wraped_lines)

    def translate(
            self,
            translator: Translator,
            source_language: str,
            destination_language: str,
    ) -> None:
        """Translate SRT file using a translator of your choose

        Args:
            translator (Translator): Translator object of choose
            destination_language (str): Destination language (must be coherent with your translator)
            source_language (str): Source language (must be coherent with your translator)
        """
        progress = 0

        # For each chunk of the file (based on the translator capabilities)
        for subs_slice in self._get_next_chunk(translator.max_char):
            first_str = str('; '.join(subs_slice[0].content)) if isinstance(subs_slice[0].content,list) else str(subs_slice[0].content)
            logger.info(f"......Waiting batch translating............ {int(100 * progress / self.length)} percent   %s",first_str)

            # Put chunk in a single text with break lines
            # text = [sub.content for sub in subs_slice]
            # text = [("\n".join(sub.content)) if isinstance(sub.content, list) else sub.content for sub in subs_slice]
            text = [(f"\n" + ("\n".join(sub.content)))
                    if isinstance(sub.content, list) else f"\n{sub.content}"
                    for sub in subs_slice]
            text = "\n".join(text)

            if len(text) > translator.max_char:
                logger.warning(
                    f"ERROR Please check data split ............................................................ len(text) {len(text)}  translator.max_char {translator.max_char}")

            # Translate
            start = timeit.default_timer()
            translation = translator.translate(
                text, source_language, destination_language
            )
            logger.debug(f"TIME WAIT translation_ing {timeit.default_timer() - start}")

            # Break each line back into subtitle content
            translation = translation.splitlines()
            j: int = 1
            for i in range(len(subs_slice)):
                if (isinstance(subs_slice[i].content, list)):
                    subs_slice[i].content = translation[j:j + len(subs_slice[i].content)]
                    j = j + len(subs_slice[i].content) + 1  # 1 line number
                else:
                    subs_slice[i].content = translation[i]
                    j = j + 2  # 1 line number and 1 next index line content str

            progress += len(subs_slice)

        print(f"..................................................................................... TRANSLATION DONE")

    def save_backup(self):
        self.subtitles = self.subtitles[: self.current_subtitle]
        self.save(self.backup_file)

    def _delete_backup(self):
        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)

    def save(self, filepath: str) -> None:
        """Saves SRT to file

        Args:
            filepath (str): Path of the new file
        """
        logger.info(f"Saving {filepath}")
        subtitles = srt.compose(self.subtitles)
        with open(filepath, "w", encoding="utf-8") as file_out:
            file_out.write(subtitles)
