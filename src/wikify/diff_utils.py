__all__ = ["side_by_side_diff", "context_diff"]

import itertools
import re

import diff_match_patch


line_split = re.compile(r'(?:\r?\n)')

def side_by_side_diff(old_text, new_text):
    """
    Calculates a side-by-side line-based difference view.

    Wraps insertions in <ins></ins> and deletions in <del></del>.
    """
    def yield_open_change_site(open_change_site):
        """ Yield all open changes. """
        ls, rs = open_change_site
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

    # Treat an empty string and "None" as same
    old_text = old_text or ''
    new_text = new_text or ''
    if not old_text and not new_text:
        return

    dmp = diff_match_patch.diff_match_patch()

    diff = dmp.diff_main(old_text, new_text)
    dmp.diff_cleanupSemantic(diff)

    # Store multiple changes around one change site. Insertions & deletions can
    #   result in lines in the old_text corresponding to two and more lines in
    #   the new_text. We want to commit them in a batch together.
    open_change_site = ([None], [None])

    for change_type, entry in diff:
        assert change_type in [-1, 0, 1]

        # Quote XML as we are inserting our own
        entry = (entry.replace('&', '&amp;')
                      .replace('<', '&lt;')
                      .replace('>', '&gt;'))

        lines = line_split.split(entry)

        ls, rs = open_change_site

        # Merge with previous entry, an unfinished line, (if still open)
        first_line = lines[0]
        if change_type == 0:
            ls[-1] = ls[-1] or ''
            rs[-1] = rs[-1] or ''
            ls[-1] = ls[-1] + first_line
            rs[-1] = rs[-1] + first_line
        elif change_type == 1:
            rs[-1] = rs[-1] or ''
            rs[-1] += '<ins>%s</ins>' % first_line if first_line else ''
        elif change_type == -1:
            ls[-1] = ls[-1] or ''
            ls[-1] += '<del>%s</del>' % first_line if first_line else ''

        lines = lines[1:]

        if lines:
            if change_type == 0:
                # Push out open change site as we now have a 1:1 mapping of an
                #   old and new line
                for entry in yield_open_change_site(open_change_site):
                    yield entry

                # Directly push out lines until last
                for line in lines[:-1]:
                    yield (False, line, line)

                # Keep last line open
                open_change_site = ([lines[-1]], [lines[-1]])
            elif change_type == 1:
                ls, rs = open_change_site

                for line in lines:
                    rs.append('<ins>%s</ins>' % line if line else '')

                open_change_site = (ls, rs)
            elif change_type == -1:
                ls, rs = open_change_site

                for line in lines:
                    ls.append('<del>%s</del>' % line if line else '')

                open_change_site = (ls, rs)

    # Push out open entry
    for entry in yield_open_change_site(open_change_site):
        yield entry


def context_diff(diff, context=2):
    if context < 0:
        raise ValueError("Context must be zero or positive")

    unconsumed_context = []

    current_change_context = None
    current_change_left_line_idx = current_change_right_line_idx = 0
    current_change_needs_context_lines_append = 0

    left_line_idx = right_line_idx = 0
    for entry in diff:
        is_change, left, right = entry

        if is_change:
            if current_change_context and len(unconsumed_context) <= context:
                # Merge change with preceding change as contexts overlap
                current_change_context.extend(unconsumed_context)
            else:
                if current_change_context:
                    # We already left the context of the preceding change,
                    #   wrap-up and make ready for new change
                    yield (current_change_left_line_idx,
                           current_change_right_line_idx,
                           current_change_context)

                # New change context, add preceding lines
                current_change_context = unconsumed_context[-context:]

                current_change_left_line_idx = max(0, left_line_idx - context)
                current_change_right_line_idx = max(0, right_line_idx - context)

            current_change_context.append(entry)

            current_change_needs_context_lines_append = context
            unconsumed_context = []
        else:
            # Not a change, but a possible context line

            if (current_change_context
                and current_change_needs_context_lines_append > 0):
                    current_change_context.append(entry)
                    current_change_needs_context_lines_append -= 1
                    unconsumed_context = []
            else:
                # Remember the last bit context for following changes, keep one
                #   more to test if we exceded last change's context
                unconsumed_context = unconsumed_context[-context:] + [entry]

        if left is not None:
            left_line_idx += 1
        if right is not None:
            right_line_idx += 1

    if current_change_context:
        yield (current_change_left_line_idx,
                current_change_right_line_idx,
                current_change_context)
