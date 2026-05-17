import os
import requests
import time

def get_token():
    return os.popen('gh auth token').read().strip()

def upload_file(session, url, file_path, token, max_retries=10):
    for attempt in range(max_retries):
        try:
            print(f"Uploading {file_path} (Attempt {attempt+1}/{max_retries})...")
            with open(file_path, 'rb') as f:
                response = session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/octet-stream",
                        "Accept": "application/vnd.github+json"
                    },
                    data=f,
                    timeout=3600 # 1 hour timeout
                )
            if response.status_code < 400:
                print(f"Success! {file_path} uploaded.")
                return True
            else:
                print(f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Network error: {e}")
        time.sleep(5)
    return False

def main():
    token = get_token()
    repo = "luogangan7-lgtm/ai-memory-os"
    release_id = "320141573" # The ID of v4.0.0-release
    
    # Check existing assets
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    res = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
    existing_assets = [a['name'] for a in res.json()] if res.status_code == 200 else []
    print(f"Existing assets: {existing_assets}")

    files = [
        ("desktop/dist/AI-Memory-OS-1.0.0-arm64.dmg", "AI-Memory-OS-1.0.0-arm64.dmg"),
        ("desktop/dist/AI-Memory-OS-1.0.0-x64.dmg", "AI-Memory-OS-1.0.0-x64.dmg"),
        ("desktop/dist/AI-Memory-OS-Setup-1.0.0.exe", "AI-Memory-OS-Setup-1.0.0.exe")
    ]

    session = requests.Session()
    
    for local_file, remote_name in files:
        if remote_name in existing_assets:
            print(f"Asset {remote_name} already exists. Skipping.")
            continue
            
        if not os.path.exists(local_file):
            print(f"File not found: {local_file}")
            continue
            
        url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={remote_name}"
        upload_file(session, url, local_file, token)

if __name__ == "__main__":
    main()
