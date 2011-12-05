import itertools
import re

import diff_match_patch

def side_by_side_diff(old_text, new_text):
    """
    Calculates a side-by-side line-based difference view.

    Wraps insertions in <ins></ins> and deletions in <del></del>.
    """
    def yield_open_entry(open_entry):
        """ Yield all open changes. """
        ls, rs = open_entry
        # Get unchanged parts onto the right line
        if ls[0] == rs[0]:
            yield (False, ls[0], rs[0])
            for l, r in itertools.izip_longest(ls[1:], rs[1:]):
                yield (True, l, r)
        elif ls[-1] == rs[-1]:
            for l, r in itertools.izip_longest(ls[:-1], rs[:-1]):
                yield (l != r, l, r)
            yield (False, ls[-1], rs[-1])
        else:
            for l, r in itertools.izip_longest(ls, rs):
                yield (True, l, r)

    line_split = re.compile(r'(?:\r?\n)')
    dmp = diff_match_patch.diff_match_patch()

    diff = dmp.diff_main(old_text, new_text)
    dmp.diff_cleanupSemantic(diff)

    open_entry = ([None], [None])
    for change_type, entry in diff:
        assert change_type in [-1, 0, 1]

        entry = (entry.replace('&', '&amp;')
                      .replace('<', '&lt;')
                      .replace('>', '&gt;'))

        lines = line_split.split(entry)

        # Merge with previous entry if still open
        ls, rs = open_entry

        line = lines[0]
        if line:
            if change_type == 0:
                ls[-1] = ls[-1] or ''
                rs[-1] = rs[-1] or ''
                ls[-1] = ls[-1] + line
                rs[-1] = rs[-1] + line
            elif change_type == 1:
                rs[-1] = rs[-1] or ''
                rs[-1] += '<ins>%s</ins>' % line if line else ''
            elif change_type == -1:
                ls[-1] = ls[-1] or ''
                ls[-1] += '<del>%s</del>' % line if line else ''

        lines = lines[1:]

        if lines:
            if change_type == 0:
                # Push out open entry
                for entry in yield_open_entry(open_entry):
                    yield entry

                # Directly push out lines until last
                for line in lines[:-1]:
                    yield (False, line, line)

                # Keep last line open
                open_entry = ([lines[-1]], [lines[-1]])
            elif change_type == 1:
                ls, rs = open_entry

                for line in lines:
                    rs.append('<ins>%s</ins>' % line if line else '')

                open_entry = (ls, rs)
            elif change_type == -1:
                ls, rs = open_entry

                for line in lines:
                    ls.append('<del>%s</del>' % line if line else '')

                open_entry = (ls, rs)

    # Push out open entry
    for entry in yield_open_entry(open_entry):
        yield entry


def context_diff(diff, context=2):
    if context < 0:
        raise ValueError("Context must be zero or positive")

    seen_context = None
    current_change = None
    seen_entries = []

    left_line_idx = right_line_idx = 0
    for entry in diff:
        is_change, left, right = entry

        if is_change:
            if current_change and seen_context > context * 2:
                # A current change was still active, however the context
                # between this and the new one is more than twice as we want
                yield current_change
                current_change = None

            if not current_change:
                left_line_idx_start = max(0, left_line_idx - context)
                right_line_idx_start = max(0, right_line_idx - context)
                current_change = (left_line_idx_start, right_line_idx_start,
                                  seen_entries + [entry])
                seen_context = 0
            else:
                current_change[2].append(entry)
                seen_context = 0

        elif current_change:
            if seen_context < context:
                current_change[2].append(entry)
            seen_context += 1

        # Save the last #context-1 entries and the current seen
        if context:
            seen_entries.append(entry)
            seen_entries = seen_entries[-context:]

        if left is not None:
            left_line_idx += 1
        if right is not None:
            right_line_idx += 1

    if current_change:
        yield current_change
