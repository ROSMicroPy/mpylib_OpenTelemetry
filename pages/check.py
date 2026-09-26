#!/usr/bin/env python3
"""Check rendered documentation links, anchors, metadata, and Python syntax."""
import ast
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent / '_site'


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids = set()
        self.links = []
        self.python = []
        self.in_python = False
        self.snippet = ''
        self.current = 0
        self.h1 = 0
        self.title = False
        self.description = False
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'{self.path.name}: duplicate ID {attrs["id"]}'
            self.ids.add(attrs['id'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'title':
            self.title = True
        if tag == 'meta' and attrs.get('name') == 'description':
            self.description = bool(attrs.get('content'))
        if attrs.get('aria-current') == 'page':
            self.current += 1
        for attr in ('href', 'src'):
            if attr in attrs:
                self.links.append(attrs[attr])
        if tag == 'code' and 'language-python' in attrs.get('class', '').split():
            self.in_python = True
            self.snippet = ''

    def handle_data(self, data):
        if self.in_python:
            self.snippet += data

    def handle_endtag(self, tag):
        if tag == 'code' and self.in_python:
            self.python.append(self.snippet)
            self.in_python = False


def check():
    paths = sorted(ROOT.glob('*.html'))
    assert paths, 'Build the site first: python3 pages/build.py'
    docs = {path.resolve(): Document(path) for path in paths}
    snippets = 0
    for path, doc in docs.items():
        assert doc.h1 == 1 and doc.title and doc.description, f'{path.name}: missing page metadata/heading'
        assert doc.current == 1, f'{path.name}: expected one current navigation link'
        assert '{{' not in path.read_text(), f'{path.name}: unresolved template variable'
        for link in doc.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            assert not url.path.startswith('/'), f'{path.name}: root-relative link breaks project Pages: {link}'
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.is_relative_to(ROOT.resolve()), f'{path.name}: link outside site: {link}'
            assert target.is_file(), f'{path.name}: missing target: {link}'
            if url.fragment and target in docs:
                assert unquote(url.fragment) in docs[target].ids, f'{path.name}: missing anchor: {link}'
        for snippet in doc.python:
            ast.parse(snippet, filename=path.name)
            snippets += 1
    print(f'Checked {len(docs)} pages: local links, anchors, metadata, navigation, and {snippets} Python examples.')


if __name__ == '__main__':
    check()
