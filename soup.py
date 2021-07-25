import html.parser

class Tag:
    def __init__(self):
        self.children = []

    def __repr__(self):
        return ''.join(map(str, self.children))

    def find(self, tag, **kwargs):
        for child in self.children:
            if isinstance(child, Tag):
                yield from child.find(tag, **kwargs)

    def next(self, tag, **kwargs):
        try:
            return next(self.find(tag, **kwargs))
        except StopIteration:
            return None

    def text(self):
        result = ''
        for child in self.children:
            if isinstance(child, Tag):
                result += child.text()
            elif isinstance(child, str):
                result += child
        return result

class Element(Tag):
    def __init__(self, parent, tag, attrs):
        Tag.__init__(self)
        parent.children.append(self)
        self.parent = parent
        self.tag = tag
        self.attrs = { k: v for k, v in attrs }

    def __repr__(self):
        attrs = ''.join(f' {k}={v!r}' for k, v in self.attrs.items())
        return f'<{self.tag}{attrs}>{Tag.__repr__(self)}</{self.tag}>'

    def find(self, tag, **kwargs):
        if self.tag == tag and self.has(**kwargs):
            yield self
        yield from Tag.find(self, tag, **kwargs)

    def has(self, **kwargs):
        for k, v in kwargs.items():
            if k not in self.attrs:
                return False
            if type(v) is list:
                for vv in v:
                    if vv not in self.attrs[k].split(' '):
                        return False
            elif type(v) is str:
                if v != self.attrs[k]:
                    return False
            else:
                return False
        return True

class Parser(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.stack = [Tag()]

    def handle_starttag(self, tag, attrs):
        self.stack.append(Element(self.stack[-1], tag, attrs))

    def handle_endtag(self, tag):
        last_tag = None
        while last_tag != tag:
            last_tag = self.stack.pop().tag

    def handle_data(self, data):
        self.stack[-1].children.append(data)

def parse(text):
    parser = Parser()
    parser.feed(text)
    return parser.stack[0]