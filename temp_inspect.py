import pandas as pd
import sys

def inspect_excel(file1, file2):
    try:
        xl1 = pd.ExcelFile(file1)
        xl2 = pd.ExcelFile(file2)
        
        for sheet in set(xl1.sheet_names).intersection(set(xl2.sheet_names)):
            df1 = pd.read_excel(file1, sheet_name=sheet)
            df2 = pd.read_excel(file2, sheet_name=sheet)
            print(f"\n[{sheet}] Columns in {file1}: {list(df1.columns)}")
            
            # Find any column that might have 'MERKO'
            merko_df1 = pd.DataFrame()
            for col in df1.columns:
                try:
                    if df1[col].astype(str).str.contains('MERKO', na=False).any():
                        merko_df1 = df1[df1[col].astype(str).str.contains('MERKO', na=False)]
                        print(f"MERKO rows in {file1} [{sheet}] (col: {col}):")
                        print(merko_df1)
                except: pass
                
            merko_df2 = pd.DataFrame()
            for col in df2.columns:
                try:
                    if df2[col].astype(str).str.contains('MERKO', na=False).any():
                        merko_df2 = df2[df2[col].astype(str).str.contains('MERKO', na=False)]
                        print(f"MERKO rows in {file2} [{sheet}] (col: {col}):")
                        print(merko_df2)
                except: pass
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_excel('portfoy_takip.xlsx', 'portfoy_takip08-05-26.xlsx')
