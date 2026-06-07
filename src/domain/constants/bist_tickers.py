# src/domain/constants/bist_tickers.py

from typing import Optional

# Borsa İstanbul (BIST) bünyesinde işlem gören güncel pay senetlerinin kodları.
# Harf sırasına göre dizilmiştir.
BIST_TICKERS = {
    "A1CAP", "ACSEL", "ADEL", "ADESE", "AEFES", "AFYON", "AGESA", "AGHOL", "AGROT", "AHGAZ", "AKCNS", "AKENR", "AKFGY",
    "AKFYE", "AKGRT", "AKMGY", "AKSA", "AKSEN", "ALARK", "ALBRK", "ALCAR", "ALCTL", "ALFAS", "ALMAD", "ALTNY",
    "ALVES", "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE", "ARCLK", "ARDYZ", "ARENA", "ARSAN", "ARTMS", "ASGYO", "ASELS",
    "ASUZU", "ATAGY", "ATAKP", "ATATP", "ATEKS", "ATLAS", "ATSYH", "AVGYO", "AVHOL", "AVOD", "AYCES", "AYDEM", "AYEN",
    "AYES", "AYGAZ", "AZTEK", "BAGFS", "BAKAB", "BALAT", "BANVT", "BARMA", "BASGZ", "BAYRK", "BEGYO", "BERA", "BEYAZ",
    "BFREN", "BIENY", "BIGCH", "BIMAS", "BINHO", "BIOEN", "BIZIM", "BJKAS", "BLCYT", "BMSCH", "BMSEL", "BNTAS", "BOBET",
    "BORLS", "BOSSA", "BRISA", "BRKO", "BRKSN", "BRMEN", "BRSAN", "BRYAT", "BSOKE", "BTCIM", "BUCIM", "BURCE", "BURVA",
    "BVSAN", "BYDNR", "CANTE", "CASA", "CATES", "CCOLA", "CELHA", "CEMAS", "CEMTS", "CIMSA", "CLEBI", "CMBTN", "CMENT",
    "CONSE", "COSMO", "CRDFA", "CVKMD", "DAGHL", "DAGI", "DAPGM", "DARDL", "DGATE", "DGGYO", "DGNMO", "DIRIT", "DITAS",
    "DMRGD", "DMSAS", "DNISI", "DOAS", "DOCO", "DOGUB", "DOHOL", "DOKTA", "DURDO", "DYOBY", "DZGYO", "EBEBK",
    "ECILC", "ECZYT", "EDATA", "EDIP", "EGEEN", "EGEPO", "EGERP", "EGPRO", "EGSER", "EKGYO", "EKIZ", "EKOS", "EKTAM",
    "ELITE", "EMKEL", "ENJSA", "ENKAI", "EPLAS", "ERBOS", "EREGL", "ERCB", "ERSU", "ESCAR", "ESCOM", "ESEN", "ETILR",
    "ETYAT", "EUHOL", "EUKYO", "EUPWR", "EUREN", "EYGYO", "FADE", "FENER", "FLAP", "FMIZP", "FONET", "FRIGO", "FROTO",
    "FZLGY", "GARAN", "GENTS", "GEREL", "GESAN", "GIPTA", "GLBMD", "GLRYH", "GLYHO", "GMTAS", "GOKNR", "GOLTS",
    "GOODY", "GOZDE", "GRNYO", "GRSEL", "GRTRK", "GSDDE", "GSDHO", "GSRAY", "GUBRF", "GWIND", "GZNMI", "HALKB", "HATEK",
    "HATSN", "HEKTS", "HKTM", "HLGYO", "HRKET", "HUBVC", "HUNER", "HURGZ", "ICBCT", "IDEAS", "IDGYO", "IEYHO", "IHAAS",
    "IHEVA", "IHGZT", "IHLAS", "IHLGM", "IHYAY", "IMASM", "INDES", "INFO", "INGRM", "INTEM", "IPEKE", "ISATR",
    "ISBTR", "ISCTR", "ISDMR", "ISFIN", "ISGSY", "ISGYO", "ISKPL", "ISMEN", "ISYAT", "ITTFH", "IZENR", "IZFAS", "IZMDC",
    "JANTS", "KAPLM", "KARYE", "KATMR", "KAYSE", "KCAER", "KCHOL", "KENT", "KERVN", "KERVT", "KFEIN", "KGYO", "KIMMR",
    "KLGYO", "KLMSN", "KLNMA", "KLRYT", "KLSYN", "KMPUR", "KNFRT", "KOCAER", "KONTR", "KONYA", "KOPOL", "KORDS", "KOTON",
    "KOZAA", "KOZAL", "KPOWR", "KRDMA", "KRDMB", "KRDMD", "KRGYO", "KRONT", "KRPLS", "KRTEK", "KRTGY", "KRVGD", "KSTUR",
    "KTSKR", "KUTPO", "LIDER", "LIDFA", "LINK", "LKMNH", "LMKDC", "LOGO", "LUKSK", "MAALT", "MACKOL", "MAGEN", "MAKIM",
    "MAKTK", "MANAS", "MARKA", "MARTI", "MAVI", "MEDTR", "MEGAP", "MEGMT", "MEPET", "MERCN", "MERIT", "MERKO", "METUR",
    "METRO", "MHRGY", "MIATK", "MIPAZ", "MOBTL", "MNDRS", "MNDTR", "MOGAN", "MPARK", "MRGYO", "MRSHL", "MSGYO", "MTRKS",
    "MTRYO", "MZHLD", "NIBAS", "NETAS", "NUGYO", "NUHCM", "OBAMS", "ODAS", "ONCSM", "ORGE", "ORMA", "OSMEN",
    "OSTIM", "OTKAR", "OYAKY", "OYAYO", "OYLUM", "OYYAT", "OZSUB", "OZGYO", "OZKGY", "OZRDN", "PAGYO", "PAMEL",
    "PAPIL", "PARSN", "PASEU", "PATGO", "PCILT", "PEGYO", "PEKGY", "PENTA", "PETKM", "PETUN", "PGSUS", "PINSU", "PKART",
    "PKENT", "PLTUR", "PNLSN", "PNSUT", "POLHO", "POLTK", "PRKAB", "PRKME", "PRDGS", "PRIENE", "PRZMA",
    "PSDTC", "PSGYO", "QNBFB", "QNBFL", "QUAGR", "RALYH", "RAYSG", "REEDR", "RGYO", "RNPOL", "RODRG", "RTALB", "RUBNS",
    "RYGYO", "RYSAS", "SAFKR", "SAHOL", "SAMAT", "SANEL", "SANFM", "SANKO", "SARKY", "SASA", "SAYAS", "SDTTR", "SEKFK",
    "SEKUR", "SELEC", "SELGD", "SENK", "SERVE", "SEYKM", "SILVR", "SNGYO", "SMRTG", "SNDTR", "SNICA",
    "SNKRN", "SOKE", "SOKM", "SONME", "SRVGY", "SUMAS", "SUNTK", "SURGY", "TABGD", "TARKM", "TATGD", "TAVHL", "TBORG",
    "TCELL", "TDGYO", "TEKTU", "TERA", "TETMT", "TEZOL", "TGSAS", "THYAO", "TKFEN", "TKNSA", "TLMAN", "TMPOL", "TMSN",
    "TOASO", "TRGYO", "TRILC", "TSKB", "TSGYO", "TSPOR", "TTKOM", "TTRAK", "TUCLK", "TUKAS", "TUPRS", "TUREX", "TURGG",
    "TURSG", "UFUK", "ULAS", "ULUSE", "ULUFA", "ULUOY", "UMAS", "USAK", "VAKFN", "VAKKO", "VAKWY", "VANGD", "VBTYZ",
    "VERTU", "VERUS", "VESBE", "VESTL", "VKFYO", "VKGYO", "VKING", "YAPRK", "YAYLA", "YBTAS", "YEOTK", "YGGYO",
    "YGYO", "YKBNK", "YKGYO", "YKSLN", "YONGA", "YUNSA", "YYLGD", "YYGYO", "ZEDUR", "ZOREN", "ZRGYO"
}


def is_valid_bist_ticker(ticker: str, fetched_name: Optional[str] = None) -> bool:
    """
    Hisse kodunun BIST listesinde olup olmadığını kontrol eder.
    Lokal listede yoksa, online sorgu tarafından getirilmiş geçerli bir
    şirket ismi (fetched_name) varsa bunu çevrimiçi olarak doğrulanmış kabul eder.
    """
    if not ticker:
        return False
    
    normalized = ticker.strip().upper()
    # .IS uzantısı varsa temizle
    clean = normalized.replace(".IS", "")
    
    # 1. Lokal listeyi kontrol et
    if clean in BIST_TICKERS:
        return True
        
    # 2. Çevrimiçi doğrulanmış mı? (fetched_name ticker'dan farklı ve doluysa)
    if fetched_name and fetched_name.strip():
        name_clean = fetched_name.strip().upper()
        if name_clean != normalized and name_clean != clean:
            return True
            
    return False
