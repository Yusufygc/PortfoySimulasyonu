# scripts/migrate_ui_strings.py
import os
import re
import tokenize
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Turkish casing helpers
def turkish_upper(s: str) -> str:
    mapping = {
        'a': 'A', 'b': 'B', 'c': 'C', 'ç': 'Ç', 'd': 'D', 'e': 'E', 'f': 'F',
        'g': 'G', 'ğ': 'Ğ', 'h': 'H', 'ı': 'I', 'i': 'İ', 'j': 'J', 'k': 'K',
        'l': 'L', 'm': 'M', 'n': 'N', 'o': 'O', 'ö': 'Ö', 'p': 'P', 'r': 'R',
        's': 'S', 'ş': 'Ş', 't': 'T', 'u': 'U', 'ü': 'Ü', 'v': 'V', 'y': 'Y',
        'z': 'Z', 'q': 'Q', 'w': 'W', 'x': 'X'
    }
    return "".join(mapping.get(c, c) for c in s)

def turkish_lower(s: str) -> str:
    mapping = {
        'A': 'a', 'B': 'b', 'C': 'c', 'Ç': 'ç', 'D': 'd', 'E': 'e', 'F': 'f',
        'G': 'g', 'Ğ': 'ğ', 'H': 'h', 'I': 'ı', 'İ': 'i', 'J': 'j', 'K': 'k',
        'L': 'l', 'M': 'm', 'N': 'n', 'O': 'o', 'Ö': 'ö', 'P': 'p', 'R': 'r',
        'S': 's', 'Ş': 'ş', 'T': 't', 'U': 'u', 'Ü': 'ü', 'V': 'v', 'Y': 'y',
        'Z': 'z', 'Q': 'q', 'W': 'w', 'X': 'x'
    }
    return "".join(mapping.get(c, c) for c in s)

def turkish_capitalize(s: str) -> str:
    if not s:
        return s
    return turkish_upper(s[0]) + turkish_lower(s[1:])

# Word-based corrections dictionary
CORRECTIONS = {
    "yatirim": "yatırım",
    "toleransi": "toleransı",
    "tecrube": "tecrübe",
    "lutfen": "lütfen",
    "tum": "tüm",
    "sorularini": "sorularını",
    "cevaplayin": "cevaplayın",
    "icin": "için",
    "secin": "seçin",
    "duzenle": "düzenle",
    "silin": "silin",
    "ekleyin": "ekleyin",
    "portfoy": "portföy",
    "simulasyonu": "simülasyonu",
    "islem": "işlem",
    "tarih": "tarih",
    "fiyat": "fiyat",
    "goster": "göster",
    "ayarlar": "ayarlar",
    "hata": "hata",
    "uyari": "uyarı",
    "basarili": "başarılı",
    "deger": "değer",
    "grafik": "grafik",
    "gun": "gün",
    "yil": "yıl",
    "analizi": "analizi",
    "optimizasyon": "optimizasyon",
    "orani": "oranı",
    "getiri": "getiri",
    "riski": "riski",
    "maliyet": "maliyet",
    "tutar": "tutar",
    "adet": "adet",
    "kar": "kâr",
    "zarar": "zarar",
    "bakiye": "bakiye",
    "nakit": "nakit",
    "baslangic": "başlangıç",
    "bitis": "bitiş",
    "tarihli": "tarihli",
    "veriler": "veriler",
    "olustur": "oluştur",
    "guncelle": "güncelle",
    "kaydet": "kaydet",
    "iptal": "iptal",
    "emin": "emin",
    "misiniz": "misiniz",
    "bulunmadi": "bulunmadı",
    "gecersiz": "geçersiz",
    "yuklenemedi": "yüklenemedi",
    "basariyla": "başarıyla",
    "tamamlandi": "tamamlandı",
    "olusturuldu": "oluşturuldu",
    "silindi": "silindi",
    "guncellendi": "güncellendi",
    "eklendi": "eklendi",
    "cikarildi": "çıkarıldı",
    "kaydedilemedi": "kaydedilemedi",
    "guncellenemedi": "güncellenemedi",
    "silinemedi": "silinemedi",
    "eklenemedi": "eklenemedi",
    "cikarilamedi": "çıkarılamadı",
}

# Helper to correct word
def correct_word(word: str) -> str:
    match = re.match(r"^(\W*)(.*?)(\W*)$", word)
    if not match:
        return word
    prefix, core, suffix = match.groups()
    if not core:
        return word
    
    t_lower = turkish_lower(core)
    if t_lower in CORRECTIONS:
        corrected_core = CORRECTIONS[t_lower]
        # Preserve capitalization
        if core.isupper():
            corrected_core = turkish_upper(corrected_core)
        elif core[0].isupper():
            corrected_core = turkish_capitalize(corrected_core)
        return prefix + corrected_core + suffix
    return word

# Helper to correct full text
def correct_turkish(text: str) -> str:
    words = re.split(r'(\s+)', text)
    corrected_words = []
    for w in words:
        if w.strip():
            corrected_words.append(correct_word(w))
        else:
            corrected_words.append(w)
    return "".join(corrected_words)

# Candidate filter
KNOWN_ICONS = {
    "plus", "pencil", "trash-2", "bookmark", "wallet", "target", "trending-up",
    "line-chart", "shield-check", "clipboard-list", "arrow-left", "arrow-right",
    "refresh-cw", "layout-dashboard", "list", "wallet", "zap", "save", "bot",
    "help-circle", "external-link", "download", "eye", "settings"
}

KNOWN_TECHNICAL_STRINGS = {
    "cssClass", "cssState", "optionValue", "objectName", "detail_text", "icon",
    "top", "bottom", "left", "right", "center", "result", "error", "success",
    "warning", "info", "action", "items", "name", "ticker", "item", "role",
    "content", "timestamp", "seconds", "messages", "title", "description",
    "notes", "message", "reply", "option", "value", "id", "status",
    "Ignored CSSStyleSheet.insertRule error", "_ToastWidget"
}

def is_docstring(token_idx: int, tokens: list) -> bool:
    i = token_idx - 1
    while i >= 0:
        t = tokens[i]
        if t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            i -= 1
            continue
        if t.string == ':':
            return True
        break
    if i < 0:
        return True
    return False

def is_user_facing_string(text: str, context_line: str) -> bool:
    # Strip quotes
    val = text
    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
        val = val[1:-1]
    if (val.startswith("'''") and val.endswith("'''")) or (val.startswith('"""') and val.endswith('"""')):
        val = val[3:-3]
        
    val_strip = val.strip()
    if not val_strip:
        return False
        
    # Ignore log statements
    if "logger." in context_line:
        return False
        
    # Ignore QSS / stylesheet attributes
    if "setProperty" in context_line and ("cssClass" in context_line or "cssState" in context_line):
        return False
    if "setObjectName" in context_line:
        return False
    if "setStyleSheet" in context_line:
        return False
        
    # Ignore colors and icon names
    if val_strip.startswith("@") or val_strip in KNOWN_ICONS or val_strip in KNOWN_TECHNICAL_STRINGS:
        return False
        
    # Ignore paths, formats, technical keys
    if re.search(r'\.(png|ico|jpg|jpeg|svg|css|sql|db|ini|csv|xlsx)$', val_strip, re.I):
        return False
    if "/" in val_strip or "\\" in val_strip:
        if " / " not in val_strip: # "Puan: - / 100" is UI text, "settings/key" is not
            return False
            
    # Ignore database columns, tickers, variables, SQL commands
    if val_strip.isupper() and len(val_strip) <= 6: # Tickers like "AAPL", "BIST"
        return False
        
    # Ignore snake_case identifier keys (e.g. display_content)
    if re.match(r'^[a-z_][a-z0-9_]*$', val_strip):
        if val_strip not in CORRECTIONS:
            return False
            
    # Must contain Turkish spelling errors OR be Turkish text
    has_letters = any(c.isalpha() for c in val_strip)
    if not has_letters:
        return False
        
    # If it is inside typical UI widgets constructors/calls
    ui_indicators = [
        "QLabel", "QPushButton", "AnimatedButton", "QRadioButton", "QCheckBox", 
        "QGroupBox", "QTableWidgetItem", "Toast", "QMessageBox", "QInputDialog", 
        "setWindowTitle", "setHeaderLabels", "self.page_title", "setTabText",
        "self.lbl_", "self.btn_", "display_name", "title", "text", "description",
        "notes", "message", "reply"
    ]
    if any(ind in context_line for ind in ui_indicators):
        return True
        
    # Or contains spaces and Turkish characters/words
    if " " in val_strip and len(val_strip) > 5:
        return True
        
    # Check if a word in the text needs correction
    for word in re.split(r'\W+', val_strip):
        if turkish_lower(word) in CORRECTIONS:
            return True
            
    return False

# Generate snake_case constant name
def make_constant_name(text: str) -> str:
    # Clean text to alphanumeric uppercase
    # Turkish character translations to English for variable name
    tr_map = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
    }
    clean = "".join(tr_map.get(c, c) for c in text)
    clean = re.sub(r'[^a-zA-Z0-9\s_]', '', clean)
    words = clean.strip().split()
    # Limit length to 4-5 words max
    words = words[:5]
    name = "_".join(w.upper() for w in words)
    if not name:
        name = "STR_CONST"
    # Ensure it starts with letter
    if name[0].isdigit():
        name = "K_" + name
    return name

def process_file(filepath: str, dry_run: bool = True):
    print(f"Processing: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Parse tokens
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
    except Exception as e:
        print(f"Error tokenizing {filepath}: {e}")
        return {}
        
    replacements = [] # list of tuples: (start_line, start_col, end_line, end_col, original_raw, corrected_val)
    
    for idx, token in enumerate(tokens):
        if token.type == tokenize.STRING:
            if is_docstring(idx, tokens):
                continue
            raw_string = token.string
            
            # Ignore f-strings as they cannot be statically localized easily
            if raw_string.lower().startswith('f'):
                continue
                
            # Check context line
            line_content = token.line
            
            if is_user_facing_string(raw_string, line_content):
                # Extract clean string value
                # Check quote type
                quote_type = ""
                for qt in ['"""', "'''", '"', "'"]:
                    if raw_string.startswith(qt) and raw_string.endswith(qt):
                        quote_type = qt
                        break
                
                if quote_type:
                    val = raw_string[len(quote_type):-len(quote_type)]
                else:
                    val = raw_string
                    
                corrected_val = correct_turkish(val)
                
                # Check if it was modified or is already correct but needs to be localized
                replacements.append({
                    'start': token.start,
                    'end': token.end,
                    'original_raw': raw_string,
                    'original_val': val,
                    'corrected_val': corrected_val,
                    'quote_type': quote_type
                })
                
    if not replacements:
        return {}
        
    # Print candidates
    print(f"Found {len(replacements)} candidates in {filepath}:")
    for r in replacements:
        diff_str = f"'{r['original_val']}' -> '{r['corrected_val']}'" if r['original_val'] != r['corrected_val'] else f"'{r['original_val']}'"
        print(f"  Line {r['start'][0]}: {diff_str}")
        
    return {filepath: replacements}


def main():
    dry_run = "--run" not in sys.argv
    if dry_run:
        print("DRY RUN MODE. Run with '--run' to apply changes.")
    else:
        print("LIVE RUN MODE. Applying changes...")
        
    ui_dir = "d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui"
    
    # Files to process
    files_to_process = []
    # main window
    files_to_process.append(os.path.join(ui_dir, "main_window.py"))
    
    # Pages directory
    pages_dir = os.path.join(ui_dir, "pages")
    for root, dirs, files in os.walk(pages_dir):
        for f in files:
            if f.endswith(".py") and f != "__init__.py" and f != "base_page.py":
                files_to_process.append(os.path.join(root, f))
                
    # Widgets directory
    widgets_dir = os.path.join(ui_dir, "widgets")
    for root, dirs, files in os.walk(widgets_dir):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                files_to_process.append(os.path.join(root, f))
                
    all_candidates = {}
    for fp in files_to_process:
        if os.path.exists(fp):
            res = process_file(fp, dry_run=dry_run)
            all_candidates.update(res)
            
    if not all_candidates:
        print("No candidates found.")
        return
        
    # Generate mapping and L10N keys
    # Map original_val to L10N key
    l10n_mapping = {}
    
    # Standard common mappings first
    l10n_mapping["Geri"] = "BACK"
    l10n_mapping["Devam"] = "NEXT"
    l10n_mapping["İptal"] = "CANCEL"
    l10n_mapping["Sil"] = "DELETE"
    l10n_mapping["Düzenle"] = "EDIT"
    l10n_mapping["Yeni"] = "NEW"
    l10n_mapping["Kaydet"] = "SAVE"
    l10n_mapping["Uyarı"] = "WARNING"
    l10n_mapping["Hata"] = "ERROR"
    l10n_mapping["Başarılı"] = "SUCCESS"
    l10n_mapping["Bilgi"] = "INFO"
    l10n_mapping["Ayarlar"] = "SETTINGS"
    l10n_mapping["Portföy Simülasyonu"] = "APP_TITLE"
    
    generated_keys = set(l10n_mapping.values())
    
    for fp, replacements in all_candidates.items():
        for r in replacements:
            corr_val = r['corrected_val']
            if corr_val not in l10n_mapping:
                # Generate unique key
                key = make_constant_name(corr_val)
                # handle collisions
                orig_key = key
                counter = 1
                while key in generated_keys:
                    key = f"{orig_key}_{counter}"
                    counter += 1
                l10n_mapping[corr_val] = key
                generated_keys.add(key)
                
    # Update locale_tr.py
    locale_file = os.path.join(ui_dir, "shared", "locale_tr.py")
    
    # Read existing locale_tr.py class L10N content if any
    existing_keys = {}
    if os.path.exists(locale_file):
        with open(locale_file, 'r', encoding='utf-8') as lf:
            lf_content = lf.read()
            # Extract existing class fields
            for m in re.finditer(r'^\s+([A-Z0-9_]+)\s*=\s*(["\'])(.*?)\2', lf_content, re.M):
                existing_keys[m.group(1)] = m.group(3)
                
    # Merge existing and new keys
    for corr_val, key in l10n_mapping.items():
        if key not in existing_keys:
            existing_keys[key] = corr_val
            
    # Write updated locale_tr.py
    if not dry_run:
        with open(locale_file, 'w', encoding='utf-8') as lf:
            lf.write('# src/ui/shared/locale_tr.py\n')
            lf.write('"""\nBu modül arayüzdeki tüm kullanıcıya dönük sabit metinleri (lokalizasyon) içerir.\n"""\n\n')
            lf.write('class L10N:\n')
            # Write sorted fields
            for key in sorted(existing_keys.keys()):
                val = existing_keys[key]
                # Escape double quotes
                escaped_val = val.replace('"', '\\"')
                lf.write(f'    {key} = "{escaped_val}"\n')
        print(f"Updated {locale_file} with {len(existing_keys)} keys.")
        
    # Replace in code files
    if not dry_run:
        for fp, replacements in all_candidates.items():
            with open(fp, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Replace from bottom of file to top to avoid offset shifting
            # Replacements must be sorted by line (descending) and column (descending)
            sorted_repl = sorted(replacements, key=lambda x: (x['start'][0], x['start'][1]), reverse=True)
            
            for r in sorted_repl:
                start_line_idx = r['start'][0] - 1
                start_col = r['start'][1]
                end_line_idx = r['end'][0] - 1
                end_col = r['end'][1]
                
                corr_val = r['corrected_val']
                l10n_key = l10n_mapping[corr_val]
                replacement_text = f"L10N.{l10n_key}"
                
                # Check if it's a single line replacement
                if start_line_idx == end_line_idx:
                    line = lines[start_line_idx]
                    new_line = line[:start_col] + replacement_text + line[end_col:]
                    lines[start_line_idx] = new_line
                else:
                    # Multi-line string replacements
                    first_line = lines[start_line_idx]
                    last_line = lines[end_line_idx]
                    
                    new_first_line = first_line[:start_col] + replacement_text
                    new_last_line = last_line[end_col:]
                    
                    lines[start_line_idx] = new_first_line + new_last_line
                    # Delete intermediate lines
                    for idx in range(start_line_idx + 1, end_line_idx + 1):
                        lines[idx] = "" # Mark for removal
            
            # Remove empty strings marked during multi-line removal
            lines = [l for l in lines if l != ""]
            
            # Check if we need to add the import statement
            has_import = False
            for line in lines:
                if "from src.ui.shared.locale_tr import L10N" in line or "import L10N" in line:
                    has_import = True
                    break
                    
            if not has_import:
                # Find the right place to insert the import: after __future__ or at start of file
                insert_idx = 0
                for idx, line in enumerate(lines):
                    if "from __future__" in line:
                        insert_idx = idx + 1
                        break
                lines.insert(insert_idx, "from src.ui.shared.locale_tr import L10N\n")
                
            # Write back
            with open(fp, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"Updated source file: {fp}")
            
    print("Done!")

if __name__ == "__main__":
    main()
