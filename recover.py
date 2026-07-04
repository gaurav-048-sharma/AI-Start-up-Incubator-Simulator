import json
import sys

log_path = r'C:\Users\rohan\.gemini\antigravity-ide\brain\80019afd-a2f9-43e3-ade3-9520a4249f07\.system_generated\logs\transcript.jsonl'
target = 'security.py'

last_full_content = None
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            entry = json.loads(line)
            if entry.get('type') == 'TOOL_CALL':
                for call in entry.get('tool_calls', []):
                    name = call.get('name')
                    args = call.get('arguments', {})
                    if name == 'default_api:write_to_file' and target in args.get('TargetFile', ''):
                        print(f"Found write_to_file at step {entry.get('step_index')}")
                        last_full_content = args.get('CodeContent')
        except Exception as e:
            pass

if last_full_content:
    print("Writing recovered content to backend/app/middleware/security.py")
    with open(r'backend\app\middleware\security.py', 'w', encoding='utf-8') as f:
        f.write(last_full_content)
else:
    print("No write_to_file found for security.py!")
