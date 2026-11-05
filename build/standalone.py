"""Give each published page the document skeleton that claude.ai adds when it hosts an artifact,
so the same file works on GitHub Pages: doctype, charset, mobile viewport and a small reset
(including [hidden] { display: none !important }, which the pages rely on)."""
import glob, sys
HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
:root { color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
body { margin: 0; font: 14px system-ui, -apple-system, "Segoe UI", sans-serif; }
img { max-width: 100%; }
[hidden] { display: none !important; }
</style>
'''
for p in sys.argv[1:] or glob.glob('versions/*/index.html'):
    s = open(p, encoding='utf-8').read()
    if s.lstrip().lower().startswith('<!doctype'): continue
    open(p, 'w', encoding='utf-8').write(HEAD + '</head>\n<body>\n' + s + '\n</body>\n</html>\n')
    print('wrapped', p)
