import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import time

def get_api_key():
    """Gemini anahtarı: önce işletim sistemi sır deposu (Ayarlar sayfası oraya yazar), sonra ortam, sonra .env."""
    try:
        from config.secret_store import KeyringSecretStore

        stored = KeyringSecretStore().get("GEMINI_API_KEY")
        if stored:
            return stored
    except Exception:
        pass
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1].strip()
    except Exception as e:
        print(f"Error reading .env: {e}")
    return None

SENSITIVE_EXTENSIONS = {".env", ".pem", ".key", ".pfx", ".p12", ".crt", ".der", ".db", ".sqlite", ".sqlite3"}
SENSITIVE_NAME_PATTERNS = ["secret", "credential", "password", "token", "api_key", ".env"]


def is_sensitive_file(filepath: str) -> bool:
    """Hassas kimlik, anahtar veya ortam dosyalarının dış API'ye gitmesini engeller."""
    normalized = filepath.replace("\\", "/").lower()
    basename = os.path.basename(normalized)
    
    # 1. Uzantı kontrolü
    _, ext = os.path.splitext(basename)
    if ext in SENSITIVE_EXTENSIONS:
        return True
        
    # 2. .env veya gizli dosya kontrolü
    if basename == ".env" or basename.startswith(".env.") or basename.endswith(".env"):
        return True
        
    # 3. İsim içinde kritik kelime kontrolü
    for pattern in SENSITIVE_NAME_PATTERNS:
        if pattern in basename:
            return True
            
    return False


def get_changed_files():
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding="utf-8")
    files = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        filepath = line[3:].strip()
        
        if filepath.startswith('"') and filepath.endswith('"'):
            filepath = filepath[1:-1]
        try:
            filepath = bytes(filepath, "ascii").decode("unicode_escape").encode("latin1").decode("utf-8")
        except:
            pass
            
        # KRİTİK GÜNCELLEME: Eğer yol bir klasörse veya mevcut değilse listeye ekleme
        if os.path.isdir(filepath) or not os.path.exists(filepath):
            continue
            
        # GÜVENLİK FİLTRESİ: Hassas ortam/anahtar dosyalarını asla dış API'ye gönderme
        if is_sensitive_file(filepath):
            print(f"[GÜVENLİK] Hassas/gizli dosya dış API'ye gönderilmemesi için atlandı: {filepath}")
            continue

        files.append((status, filepath))
    return files

def get_diff(filepath, status):
    if is_sensitive_file(filepath):
        return ""
    try:
        if "??" in status:  # Untracked
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                return f"New untracked file:\n{content[:2000]}" # Güvenli sınır
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
            return diff[:3000] # Güvenli sınır
    except Exception as e:
        print(f"Error getting diff for {filepath}: {e}")
        return ""

def generate_batch_commit_messages(api_key, files_data, retries=3):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = """Sen bir uzman yazılım mühendisisin. Aşağıda sana JSON formatında birden fazla dosyanın git diff çıktıları verilmiştir.
Her bir dosya için projenin özel RULES.md kurallarına tamı tamına uyan bir commit mesajı yazacaksın.

KURALLAR:
1. Format kesinlikle aşağıdaki gibi olmalıdır:
<fiil>: <ne yapıldığı, tek satır, 72 karakter sınırı>

<gövde — neyin neden yapıldığını açıklar, boş satırla ayrılır>
- Madde 1
- Madde 2

Etkilenen modüller: <dosya_yolu>

2. Kullanılabilecek fiiller: ekle:, güncelle:, düzelt:, refaktör:, sil:, belge:, test:, yapılandır:
3. Mesaj tamamen düzgün, dilbilgisi kurallarına uygun TÜRKÇE olmalı ve Türkçe karakterler düzgün kullanılmalıdır.

Senden yanıtı SADECE geçerli bir JSON objesi olarak bekliyorum. JSON yapısı şu şekilde olmalıdır:
{
  "dosya_yolu_1": "üretilen_commit_mesaji_1",
  "dosya_yolu_2": "üretilen_commit_mesaji_2"
}

Asla markdown (```json) kullanma, fazladan açıklama yazma. Doğrudan ham JSON metnini döndür.

Değişiklik Listesi:
""" + json.dumps(files_data, ensure_ascii=False, indent=2)

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    for attempt in range(retries):
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"Rate limit hit. Sleeping for 20 seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(20)
            else:
                print(f"API HTTP Error: {e.code} {e.reason}")
                return None
        except Exception as e:
            print(f"API Error: {e}")
            return None
    return None

def main():
    api_key = get_api_key()
    if not api_key:
        print("Could not find GEMINI_API_KEY in .env")
        return
        
    changed_files = get_changed_files()
    if not changed_files:
        print("No changed files found.")
        return
        
    print(f"Found {len(changed_files)} valid files to process. Gathering diffs...")
    
    files_batch_data = {}
    valid_files = []
    
    for status, filepath in changed_files:
        diff = get_diff(filepath, status)
        if diff.strip():
            files_batch_data[filepath] = {
                "status": status,
                "diff": diff
            }
            valid_files.append(filepath)

    if not files_batch_data:
        print("No valid diffs found to send.")
        return

    # GÜNCELLEME: Dosyaları 20'şerli paketlere (chunk) bölüyoruz (Payload limitini aşmamak için)
    chunk_size = 20
    keys = list(files_batch_data.keys())
    all_commit_messages = {}

    for i in range(0, len(keys), chunk_size):
        chunk_keys = keys[i:i + chunk_size]
        chunk_data = {k: files_batch_data[k] for k in chunk_keys}
        
        print(f"Sending batch {i//chunk_size + 1} ({len(chunk_data)} files) to Gemini...")
        commit_messages_dict = generate_batch_commit_messages(api_key, chunk_data)
        
        if commit_messages_dict:
            all_commit_messages.update(commit_messages_dict)
            
        # API limitine takılmamak için batch'ler arası çok kısa mola (Opsiyonel)
        if i + chunk_size < len(keys):
            time.sleep(2)

    # Local commit işlemleri
    for filepath in valid_files:
        commit_msg = all_commit_messages.get(filepath)
        if not commit_msg:
            print(f"No commit message returned for {filepath}. Skipping.")
            continue
            
        print(f"\nCommitting: {filepath}")
        
        subprocess.run(["git", "add", filepath])
        
        with open("temp_commit_msg.txt", "w", encoding="utf-8") as f:
            f.write(commit_msg)
            
        result = subprocess.run(["git", "commit", "-F", "temp_commit_msg.txt"])
        if result.returncode == 0:
            print(f"Successfully committed {filepath}")
        else:
            print(f"Failed to commit {filepath}")
            
    if os.path.exists("temp_commit_msg.txt"):
        os.remove("temp_commit_msg.txt")
        
    print("\nAll files processed successfully!")

if __name__ == "__main__":
    main()