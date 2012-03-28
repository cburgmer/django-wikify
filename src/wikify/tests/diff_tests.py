import itertools

from django.utils import unittest

try:
    from wikify.diff_utils import side_by_side_diff, context_diff
except ImportError:
    can_test_diff = False
else:
    can_test_diff = True

@unittest.skipUnless(can_test_diff, "Diff match patch library not installed")
class SideBySideDiffTest(unittest.TestCase):
    def test_one_line_with_change(self):
        self.assertEqual(list(side_by_side_diff("old text",
                                                "new text")),
                         [("<del>old</del> text", "<ins>new</ins> text")])

    def test_one_line_with_insertion(self):
        self.assertEqual(list(side_by_side_diff("text",
                                                "new text")),
                         [("text", "<ins>new </ins>text")])

    def test_one_line_with_deletion(self):
        self.assertEqual(list(side_by_side_diff("old text",
                                                "text")),
                         [("<del>old </del>text", "text")])

    def test_one_line_without_change(self):
        self.assertEqual(list(side_by_side_diff("text",
                                                "text")),
                         [("text", "text")])

    def test_empty_text_without_change_has_no_diff(self):
        self.assertEqual(list(side_by_side_diff("",
                                                "")),
                         [])

    def test_empty_text_with_insertion(self):
        self.assertEqual(list(side_by_side_diff("",
                                                "new")),
                         [(None, "<ins>new</ins>")])

    def test_empty_line_with_insertion(self):
        self.assertEqual(list(side_by_side_diff("\n",
                                                "new\n")),
                         [("", "<ins>new</ins>"),
                          ("", "")])

    def test_empty_lines_with_insertion(self):
        self.assertEqual(list(side_by_side_diff("\n\n\n",
                                                "\n\nnew\n")),
                         [("", ""),
                          ("", ""),
                          ("", "<ins>new</ins>"),
                          ("", "")])

    def test_text_with_full_deletion(self):
        self.assertEqual(list(side_by_side_diff("old",
                                                "")),
                         [("<del>old</del>", None)])

    def test_line_with_full_deletion(self):
        self.assertEqual(list(side_by_side_diff("old\n",
                                                "\n")),
                         [("<del>old</del>", ""),
                          ("", "")])

    def test_empty_lines_with_deletion(self):
        self.assertEqual(list(side_by_side_diff("\n\nold\n",
                                                "\n\n\n")),
                         [("", ""),
                          ("", ""),
                          ("<del>old</del>", ""),
                          ("", "")])

    def test_two_lines_with_one_change(self):
        self.assertEqual(list(side_by_side_diff("old text\nline",
                                                "new text\nline")),
                         [("<del>old</del> text", "<ins>new</ins> text"),
                          ("line", "line")])

    def test_two_lines_without_change(self):
        self.assertEqual(list(side_by_side_diff("text\nline",
                                                "text\nline")),
                         [("text", "text"),
                          ("line", "line")])

    def test_line_insertion_at_beginning(self):
        self.assertEqual(list(side_by_side_diff("line",
                                                "new text\nline")),
                         [(None, "<ins>new text</ins>"),
                          ("line", "line")])

    def test_line_insertion_at_end(self):
        self.assertEqual(list(side_by_side_diff("line",
                                                "line\nnew text")),
                         [("line", "line"),
                          (None, "<ins>new text</ins>")])

    def test_line_insertion_in_middle(self):
        self.assertEqual(list(side_by_side_diff("line\nanother line",
                                                "line\nnew text\nanother line")),
                         [("line", "line"),
                          (None, "<ins>new text</ins>"),
                          ("another line", "another line")])

    def test_that_inserted_newline_keeps_changes_minimal(self):
        self.assertEqual(list(side_by_side_diff("a long line with words",
                                                "a long line\nwith words")),
                         [("a long line<del> </del>with words", "a long line"),
                          (None, "with words")])

    def test_inserted_newline_with_text_change(self):
        self.assertEqual(list(side_by_side_diff("a long line with words",
                                                "a long line\nand words")),
                         [("a long line<del> with</del> words", "a long line"),
                          (None, "<ins>and</ins> words")])


@unittest.skipUnless(can_test_diff, "Diff match patch library not installed")
class ContextDiffTest(unittest.TestCase):
    def test_small_change_is_included(self):
        diff = side_by_side_diff("old text",
                                 "new text")
        diff, diff_clone = itertools.tee(diff)
        self.assertEqual(list(context_diff(diff)),
                         [(0, 0, list(diff_clone))])

    def test_multi_line_change_is_included(self):
        diff = side_by_side_diff("old text\nline\nanother line",
                                 "new text\nline\nsome line")
        diff, diff_clone = itertools.tee(diff)
        self.assertEqual(list(context_diff(diff)),
                         [(0, 0, list(diff_clone))])

    def test_context_excludes_initial_unchanged(self):
        lines = [("line %d" % i) for i in range(5)]
        changed_lines = lines[:3] + ['one line', 'another line']

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)

        self.assertEqual(list(context_diff(diff)),
                         [(1, 1, list(diff_clone)[1:])])

    def test_context_excludes_final_unchanged(self):
        lines = [("line %d" % i) for i in range(5)]
        changed_lines = ['one line', 'another line'] + lines[2:]

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)

        self.assertEqual(list(context_diff(diff)),
                         [(0, 0, list(diff_clone)[:-1])])

    def test_context_excludes_bordering_unchanged(self):
        lines = [("line %d" % i) for i in range(10)]
        changed_lines = lines[:4] + ['one line', 'another line'] + lines[6:]

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)

        self.assertEqual(list(context_diff(diff)),
                         [(2, 2, list(diff_clone)[2:8])])

    def test_multiple_contexts(self):
        lines = [("line %d" % i) for i in range(20)]
        changed_lines = (lines[:4] + ['one line', 'another line'] + lines[6:14]
                         + ['third line', 'forth line'] + lines[16:])

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)
        diff_clone = list(diff_clone)

        self.assertEqual(list(context_diff(diff)),
                         [(2, 2, diff_clone[2:8]),
                          (12, 12, diff_clone[12:18])])

    def test_bordering_contexts_are_merged(self):
        lines = [("line %d" % i) for i in range(12)]
        changed_lines = (lines[:3] + ['one line'] + lines[4:8]
                         + ['another one'] + lines[9:])

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)

        self.assertEqual(list(context_diff(diff)),
                         [(1, 1, list(diff_clone)[1:11])])

    def test_insertion_context(self):
        lines = [("line %d" % i) for i in range(13)]
        changed_lines = (lines[:3] + ['one line', 'another line'] + lines[3:8]
                         + ['third line', 'forth line'] + lines[10:])

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)
        diff_clone = list(diff_clone)

        self.assertEqual(list(context_diff(diff)),
                         [(1, 1, diff_clone[1:7]),
                          (6, 8, diff_clone[8:14])])

    def test_deletion_context(self):
        lines = [("line %d" % i) for i in range(15)]
        changed_lines = (lines[:3] + lines[5:10]
                         + ['third line', 'forth line'] + lines[12:])

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)
        diff_clone = list(diff_clone)

        self.assertEqual(list(context_diff(diff)),
                         [(1, 1, diff_clone[1:7]),
                          (8, 6, diff_clone[8:14])])

    def test_full_change_contexts(self):
        lines = [("line %d" % i) for i in range(34)]
        changed_lines = (lines[:3] + ['one line', 'another line'] + lines[5:10]
                         + ['third line', 'forth line'] + lines[10:15]
                         + ['one more line', 'yet another'] + lines[17:22]
                         + lines[24:29]
                         + ['nearly last', 'possibly last line'] + lines[31:])

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)
        diff_clone = list(diff_clone)

        self.assertEqual(list(context_diff(diff)),
                         [(1, 1, diff_clone[1:7]),
                          (8, 8, diff_clone[8:14]),
                          (13, 15, diff_clone[15:21]),
                          (20, 22, diff_clone[22:28]),
                          (27, 27, diff_clone[29:35])])

    def test_full_change_merged_contexts(self):
        lines = [("line %d" % i) for i in range(30)]
        changed_lines = (lines[:3] + ['one line', 'another line'] + lines[5:9]
                         + ['third line', 'forth line'] + lines[9:13]
                         + ['one more line', 'yet another'] + lines[15:19]
                         + lines[21:25]
                         + ['nearly last', 'possibly last line'] + lines[27:])

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)
        diff_clone = list(diff_clone)

        self.assertEqual(list(context_diff(diff)),
                         [(1, 1, diff_clone[1:31])])

    def test_user_defined_context(self):
        lines = [("line %d" % i) for i in range(12)]
        changed_lines = lines[:5] + ['one line', 'another line'] + lines[7:]

        diff = side_by_side_diff('\n'.join(lines), '\n'.join(changed_lines))
        diff, diff_clone = itertools.tee(diff)

        self.assertEqual(list(context_diff(diff, context=4)),
                         [(1, 1, list(diff_clone)[1:11])])
