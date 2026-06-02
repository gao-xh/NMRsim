import os
import re

files = [
    'CHANGELOG.md',
    'PROJECT_OVERVIEW.md', 
    'QUICK_REFERENCE.md',
    'REORGANIZATION_COMPLETE.md',
    'dev_log.txt'
]

print("Checking Chinese characters in root files:")
print("=" * 60)

for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        chinese = re.findall(r'[\u4e00-\u9fa5]', content)
        print(f"{f:40} {len(chinese):4} Chinese characters")
    else:
        print(f"{f:40} NOT FOUND")

print("=" * 60)
