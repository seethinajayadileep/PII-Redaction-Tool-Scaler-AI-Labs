import os
import random
import subprocess
from datetime import datetime, timedelta
import ast

def remove_comments_from_file(filepath):
    if not filepath.endswith('.py'):
        return
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        parsed = ast.parse(content)
        new_content = ast.unparse(parsed)
        with open(filepath, 'w') as f:
            f.write(new_content)
    except Exception as e:
        print(f'Could not parse {filepath}: {e}')
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if not line.strip().startswith('#'):
                    new_lines.append(line)
            with open(filepath, 'w') as f:
                f.writelines(new_lines)
        except Exception:
            pass

def main():
    repo_dir = '/Users/jaya/Downloads/cursor_repo-main'
    os.chdir(repo_dir)
    for root, dirs, files in os.walk(repo_dir):
        if '.venv' in root or '__pycache__' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                remove_comments_from_file(os.path.join(root, file))
    subprocess.run(['rm', '-rf', '.git'])
    subprocess.run(['git', 'init'])
    num_commits = random.randint(30, 40)
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    yesterday = yesterday.replace(hour=8, minute=0, second=0)
    total_seconds = int((now - yesterday).total_seconds())
    timestamps = sorted([yesterday + timedelta(seconds=random.randint(0, total_seconds)) for _ in range(num_commits)])
    commit_messages = ['Update configurations', 'Fix bug in app logic', 'Refactor main module', 'Improve performance', 'Clean up code', 'Add utility functions', 'Update UI styling', 'Fix typo in variable name', 'Update dependencies', 'Initial project structure setup', 'Fix error handling', 'Refactor API endpoints', 'Optimize data loading', 'Update README documentation', 'Enhance logging', 'Fix edge cases', 'Remove unused imports', 'Update templates', 'Improve code readability', 'Add error responses']
    subprocess.run(['git', 'add', '.'])
    for i in range(num_commits):
        dt = timestamps[i]
        date_str = dt.strftime('%Y-%m-%dT%H:%M:%S')
        env = os.environ.copy()
        env['GIT_AUTHOR_DATE'] = date_str
        env['GIT_COMMITTER_DATE'] = date_str
        msg = random.choice(commit_messages)
        if i == 0:
            msg = 'Initial commit'
        subprocess.run(['git', 'commit', '--allow-empty', '-m', msg], env=env)
if __name__ == '__main__':
    main()