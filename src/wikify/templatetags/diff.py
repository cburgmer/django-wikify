from django.template import Library, Node, TemplateSyntaxError, Variable, VariableDoesNotExist
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode

from wikify.diff_utils import side_by_side_diff, context_diff

register = Library()

class ContextualDiffNode(Node):
    def __init__(self, old_value, new_value, context_width=2):
        self.old_value = Variable(old_value)
        self.new_value = Variable(new_value)
        self.context_width = context_width

    def render(self, context):
        try:
            old_value = self.old_value.resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError('"cache" tag got an unknown variable: %r'
                                      % self.old_value)
        try:
            new_value = self.new_value.resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError('"cache" tag got an unknown variable: %r'
                                      % self.old_value)

        old_text = force_unicode(old_value) if old_value else ''
        new_text = force_unicode(new_value) if new_value else ''
        diff = side_by_side_diff(old_text, new_text)
        contextual_diff = context_diff(diff, context=self.context_width)

        context.push()
        diff_str = render_to_string('wikify/contextual_diff_tr.html',
                                    {'context_diff': contextual_diff},
                                    context)
        context.pop()
        return diff_str


def do_context_diff_tr(parser, token):
    """
    This will render a contextual diff between to values. Output needs to be
    surrounded by the <table> and <body> tags.

    Usage::

        {% load diff %}
        <table>
            <body>
                {% context_diff_tr old_value new_value [context_width]%}
            </body>
        </table>
    """
    parser.delete_first_token()
    tokens = token.contents.split()
    if len(tokens) < 3:
        raise TemplateSyntaxError(u"'%r' tag requires at least 2 arguments."
                                  % tokens[0])
    return ContextualDiffNode(tokens[1], tokens[2], *tokens[3:])

register.tag('context_diff_tr', do_context_diff_tr)
