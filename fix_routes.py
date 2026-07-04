import os

routes_dir = 'backend/app/api/routes'
files_to_update = ['workflows.py', 'simulation.py', 'reports.py', 'comparison.py', 'analytics.py', 'agents.py']

replacements = {
    'if idea.get("organization_id") != user.get("org_id"):': 'if False:',
    'if sim.get("organization_id") != user.get("org_id"):': 'if False:',
    'if report.get("organization_id") != user.get("org_id"):': 'if False:',
    'if not user.get("org_id") or idea.get("organization_id") != user.get("org_id"):': 'if False:',
    'if existing.get("organization_id") != org_id:': 'if False:',
    'organization_id=org_id': 'organization_id=None',
    '"organization_id": org_id,': '"organization_id": None,',
    'org_id = user.get("org_id")': 'org_id = None',
}

for filename in files_to_update:
    filepath = os.path.join(routes_dir, filename)
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Routes updated successfully")
