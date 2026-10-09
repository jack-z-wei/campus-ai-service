import csv
import hashlib
import json
from pathlib import Path

root = Path('.')
package = root / 'submission'
manifest = json.loads((package / 'package_manifest.json').read_text(encoding='utf-8'))
rows = manifest['files']
actual_files = [p for p in package.rglob('*') if p.is_file() and p.name != 'package_manifest.json']
assert manifest['directory_count'] == 6
assert manifest['file_count'] == len(actual_files) == len(rows)
assert not manifest['contains_dotenv'] and not manifest['contains_virtual_environment']
assert not manifest['coze_platform_tested'] and not manifest['manual_ratings_completed']
assert manifest['ai_assisted_ratings_present']
assert not any(p.name == '.env' for p in package.rglob('*') if p.is_file())
assert not (package / '03_AI_Coding_Version' / 'checkpoints.db').exists()
assert not any(p.name in {'.venv', '__pycache__', '.pytest_cache', '.ruff_cache'} for p in package.rglob('*') if p.is_dir())

ai_path = root / 'reports' / 'AI辅助评分表_V1_V2.csv'
with ai_path.open(encoding='utf-8-sig', newline='') as stream:
    ai_rows = list(csv.DictReader(stream))
assert len(ai_rows) == 10
for row in ai_rows:
    assert [row[k] for k in ('correctness_0_2', 'faithfulness_0_2', 'citation_accuracy_0_2')] == ['2', '2', '2']
    assert all(row[k].strip() for k in ('correctness_reason', 'faithfulness_reason', 'citation_accuracy_reason'))
    assert row['reviewer'] == 'Codex AI辅助评估（非人工评分）'
assert sum(1 for row in ai_rows if row['prompt_version'].lower() == 'v1') == 5
assert sum(1 for row in ai_rows if row['prompt_version'].lower() == 'v2') == 5

pairs = [
    ('reports/AI辅助评分表_V1_V2.csv', '04_Evaluation/reports/AI辅助评分表_V1_V2.csv'),
    ('reports/campus_ui_home.png', '06_Demo/screenshots/campus_ui_home.png'),
    ('src/streamlit_app.py', '03_AI_Coding_Version/src/streamlit_app.py'),
]
for source, target in pairs:
    left = hashlib.sha256((root / source).read_bytes()).hexdigest()
    right = hashlib.sha256((package / target).read_bytes()).hexdigest()
    assert left == right, (source, target)

ui = (package / '03_AI_Coding_Version/src/streamlit_app.py').read_text(encoding='utf-8')
for forbidden in ('Agent Service Toolkit', 'JoshuaC215', 'AcmeTech', 'LangSmith'):
    assert forbidden not in ui
assert (package / '03_AI_Coding_Version/LICENSE').is_file()
assert (package / '03_AI_Coding_Version/UPSTREAM.md').is_file()
print('Windows delivery verification passed: files=', len(rows), 'AI rows=', len(ai_rows), 'human_ratings_completed=', manifest['manual_ratings_completed'])
