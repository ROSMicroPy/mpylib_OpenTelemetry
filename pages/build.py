#!/usr/bin/env python3
"""Build the documentation using only Python 3.10+ standard library."""
import ast
import html
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUTPUT = ROOT / '_site'
SOURCE_URL = 'https://github.com/ROSMicroPy/mpylib_OpenTelemetry'
PAGES = [
    ('index', 'Project objective', 'Start here', 'Understand what mp_opentelemetry brings to MicroPython devices.'),
    ('getting-started', 'Getting started', 'Start here', 'Install otel and send your first traces, logs, and metrics.'),
    ('configuration', 'Configuration', 'Build with otel', 'Configure endpoints, resources, logging, and background export.'),
    ('instrumentation', 'Traces, logs & metrics', 'Build with otel', 'Instrument your application with correlated telemetry.'),
    ('propagation', 'Context & propagation', 'Build with otel', 'Carry trace context across HTTP and message boundaries.'),
    ('internals', 'Technical details', 'Go deeper', 'Understand processing, OTLP JSON, memory, and failure behavior.'),
    ('reference', 'API reference', 'Go deeper', 'Public API signatures generated from the current source code.'),
    ('troubleshooting', 'Troubleshooting', 'Go deeper', 'Diagnose missing telemetry, network failures, and device constraints.'),
]


def reference():
    init = ast.parse((REPO / 'src/__init__.py').read_text())
    exports = {}
    for node in init.body:
        if isinstance(node, ast.ImportFrom):
            for name in node.names:
                exports[name.name] = node.module
    sections = []
    for module in sorted(set(exports.values())):
        tree = ast.parse((REPO / 'src' / (module + '.py')).read_text())
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        def methods_for(node):
            methods = {}
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in classes:
                    methods.update(methods_for(classes[base.id]))
            methods.update({method.name: method for method in node.body
                            if isinstance(method, ast.FunctionDef)})
            return methods

        entries = []
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) or node.name not in exports:
                continue
            signatures = []
            if isinstance(node, ast.FunctionDef):
                signatures.append(node.name + '(' + ast.unparse(node.args) + ')')
            else:
                for method in methods_for(node).values():
                    if isinstance(method, ast.FunctionDef) and (not method.name.startswith('_') or method.name == '__init__'):
                        args = ast.unparse(method.args)
                        if args == 'self':
                            args = ''
                        elif args.startswith('self, '):
                            args = args[6:]
                        label = node.name if method.name == '__init__' else method.name
                        is_property = any(isinstance(d, ast.Name) and d.id == 'property' for d in method.decorator_list)
                        signatures.append(label if is_property else label + '(' + args + ')')
                if node.bases:
                    signatures.insert(0, 'Inherits: ' + ', '.join(ast.unparse(b) for b in node.bases))
            entries.append(f'<h3 id="{node.name}">{node.name}</h3><pre><code>{html.escape(chr(10).join(signatures))}</code></pre>')
        sections.append(f'<h2 id="{module}">otel.{module}</h2><p><a href="{SOURCE_URL}/blob/main/src/{module}.py">Read module source ↗</a></p>' + ''.join(entries))
    return '<p>Import these names from <code>otel</code>. Signatures are generated from this checkout on every build. Inherited methods from this module are included with each class. See the guides for lifecycle and return-value behavior.</p>' + ''.join(sections)


def build():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    shutil.copytree(ROOT / 'assets', OUTPUT / 'assets')
    version = html.escape(json.loads((REPO / 'package.json').read_text())['version'])
    template = (ROOT / 'template.html').read_text()
    for i, (slug, title, group, description) in enumerate(PAGES):
        body = reference() if slug == 'reference' else (ROOT / 'content' / (slug + '.html')).read_text()
        nav, last_group = [], None
        for target, label, category, _ in PAGES:
            if category != last_group:
                nav.append(f'<p class="nav-group">{category}</p>')
                last_group = category
            current = ' aria-current="page"' if target == slug else ''
            nav.append(f'<a href="{target}.html"{current}>{html.escape(label)}</a>')
        adjacent = []
        for offset, label in ((-1, 'Previous'), (1, 'Next')):
            if 0 <= i + offset < len(PAGES):
                target, name, _, _ = PAGES[i + offset]
                adjacent.append(f'<a href="{target}.html"><small>{label}</small>{html.escape(name)} <span aria-hidden="true">→</span></a>')
        values = {'title': html.escape(title), 'description': html.escape(description), 'group': group,
                  'version': version, 'navigation': ''.join(nav), 'content': body,
                  'pagination': ''.join(adjacent), 'source': SOURCE_URL,
                  'edit_path': 'pages/build.py' if slug == 'reference' else 'pages/content/' + slug + '.html'}
        page = template
        for key, value in values.items():
            page = page.replace('{{' + key + '}}', value)
        (OUTPUT / (slug + '.html')).write_text(page)
    (OUTPUT / '.nojekyll').touch()
    shutil.copyfile(REPO / 'LICENSE.txt', OUTPUT / 'LICENSE.txt')
    print(f'Built {len(PAGES)} pages in {OUTPUT}')


if __name__ == '__main__':
    build()
