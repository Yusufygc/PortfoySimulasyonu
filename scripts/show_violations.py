import json

with open('docs/wiki/code_quality_baseline_2026-06-13.json') as f:
    d = json.load(f)

fns = d['violations']['functions']
print(f'total violating_functions: {len(fns)}')
src = [f for f in fns if f['layer'] == 'src']
print(f'src violations: {len(src)}')

src_cc = sorted(src, key=lambda x: x.get('cyclomatic_complexity', 0), reverse=True)
print('\nTop 15 complexity:')
for x in src_cc[:15]:
    cc = x.get('cyclomatic_complexity', 0)
    p = x.get('effective_param_count', 0)
    l = x.get('effective_code_lines', 0)
    fn = x['name']
    fi = x['path']
    print(f'  cc={cc} p={p} l={l} {fi}::{fn}')

src_p = sorted(src, key=lambda x: x.get('effective_param_count', 0), reverse=True)
print('\nTop 15 params:')
for x in src_p[:15]:
    cc = x.get('cyclomatic_complexity', 0)
    p = x.get('effective_param_count', 0)
    l = x.get('effective_code_lines', 0)
    fn = x['name']
    fi = x['path']
    print(f'  p={p} cc={cc} l={l} {fi}::{fn}')
