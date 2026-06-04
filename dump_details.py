import pandas as pd

def dump_details(file_path):
    print(f"\n===== DUMPING {file_path} =====")
    xl = pd.ExcelFile(file_path)
    
    # We need to find the sheet 'Günlük Detaylar'
    sheet_name = None
    for name in xl.sheet_names:
        if 'detay' in name.lower() or 'gnlk' in name.lower():
            sheet_name = name
            break
            
    if not sheet_name:
        print("Sheet not found")
        return
        
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    # Print the columns
    print("All Columns:", list(df.columns))
    
    # Let's find rows where MERKO is present
    merko_rows = df[df.astype(str).apply(lambda x: x.str.contains('MERKO')).any(axis=1)]
    
    # We want Dec 4, 2025 if it exists
    dec4_row = pd.DataFrame()
    for col in merko_rows.columns:
        # Check if this column contains dates
        try:
            matched = merko_rows[merko_rows[col].astype(str).str.contains('2025-12-04')]
            if not matched.empty:
                dec4_row = matched
                break
        except:
            pass
            
    if not dec4_row.empty:
        print("Row for MERKO on 2025-12-04:")
        for col in dec4_row.columns:
            print(f"  {col}: {dec4_row[col].values[0]}")
    else:
        print("MERKO on 2025-12-04 not found")
        print("First 5 MERKO rows:")
        print(merko_rows.head(5))

dump_details('portfoy_takip.xlsx')
dump_details('portfoy_takip08-05-26.xlsx')
