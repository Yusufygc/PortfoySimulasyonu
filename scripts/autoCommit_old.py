import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import time

def get_api_key():
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.strip().split("=")[1].strip()
    except Exception as e:
        print(f"Error reading .env: {e}")
    return None

def get_changed_files():
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding="utf-8")
    files = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        filepath = line[3:].strip()
        files.append((status, filepath))
    return files

def get_diff(filepath, status):
    try:
        if "??" in status: # Untracked
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                return f"New untracked file:\n{content[:5000]}"
        else:
            if status[0] != ' ' and status[0] != '?':
                cmd = ["git", "diff", "--cached", "--", filepath]
            else:
                cmd = ["git", "diff", "--", filepath]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            diff = result.stdout
            if not diff and status[0] != ' ':
                result = subprocess.run(["git", "diff", "HEAD", "--", filepath], capture_output=True, text=True, encoding="utf-8")
                diff = result.stdout
            return diff[:8000]
    except Exception as e:
        print(f"Error getting diff for {filepath}: {e}")
        return ""

def generate_commit_message(api_key, diff_text, filepath, retries=3):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""Sen bir uzman yazılım mühendisisin. Aşağıdaki git diff çıktısına bakarak, projeye özel RULES.md commit kurallarına tamı tamına uyan bir commit mesajı yazacaksın.

KURALLAR:
1. Format kesinlikle aşağıdaki gibi olmalıdır:
<fiil>: <ne yapıldığı, tek satır, 72 karakter sınırı>

<gövde — neyin neden yapıldığını açıklar, boş satırla ayrılır>
- Madde 1
- Madde 2

Etkilenen modüller: {filepath}

2. Kullanılabilecek fiiller: ekle:, güncelle:, düzelt:, refaktör:, sil:, belge:, test:, yapılandır:
3. Mesaj tamamen düzgün, dilbilgisi kurallarına uygun TÜRKÇE olmalı ve Türkçe karakterler düzgün kullanılmalıdır.
4. Markdown code block işaretleri (```) KULLANMA. Doğrudan commit mesajı metnini ver.

Aşağıda dosyanın diff'i (değişiklikleri) verilmiştir:
{diff_text}

SADECE COMMIT MESAJINI METİN OLARAK DÖNDÜR, BAŞKA HİÇBİR AÇIKLAMA YAZMA.
"""
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2
        }
    }
    
    for attempt in range(retries):
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                msg = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if msg.startswith("```"):
                    msg = "\n".join(msg.split("\n")[1:])
                if msg.endswith("```"):
                    msg = "\n".join(msg.split("\n")[:-1])
                return msg.strip()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"Rate limit hit for {filepath}. Sleeping for 60 seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(60)
            else:
                print(f"API HTTP Error for {filepath}: {e.code} {e.reason}")
                return None
        except Exception as e:
            print(f"API Error for {filepath}: {e}")
            return None
    return None

def main():
    api_key = get_api_key()
    if not api_key:
        print("Could not find GEMINI_API_KEY in .env")
        return
        
    files = get_changed_files()
    if not files:
        print("No changed files found.")
        return
        
    print(f"Found {len(files)} files to commit.")
    
    for status, filepath in files:
        if filepath.startswith('"') and filepath.endswith('"'):
            filepath = filepath[1:-1]
        
        try:
            filepath = bytes(filepath, "ascii").decode("unicode_escape").encode("latin1").decode("utf-8")
        except:
            pass

        print(f"\nProcessing: {filepath}")
        diff = get_diff(filepath, status)
        if not diff.strip():
            print(f"No diff for {filepath}, skipping.")
            continue
            
        commit_msg = generate_commit_message(api_key, diff, filepath)
        if not commit_msg:
            print(f"Failed to generate commit message for {filepath}. Skipping.")
            continue
            
        print("--- Generated Message ---")
        print(commit_msg)
        print("-------------------------")
        
        subprocess.run(["git", "add", filepath])
        
        with open("temp_commit_msg.txt", "w", encoding="utf-8") as f:
            f.write(commit_msg)
            
        result = subprocess.run(["git", "commit", "-F", "temp_commit_msg.txt"])
        if result.returncode == 0:
            print(f"Successfully committed {filepath}")
        else:
            print(f"Failed to commit {filepath}")
            
        print("Sleeping 13 seconds to respect rate limits (max 5 requests per minute)...")
        time.sleep(13)
            
    if os.path.exists("temp_commit_msg.txt"):
        os.remove("temp_commit_msg.txt")
        
    print("\nAll files processed!")

if __name__ == "__main__":
    main()
