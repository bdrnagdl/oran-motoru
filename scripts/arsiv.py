"""Kupon arşivi.
1) Verilen günlük kupon dosyalarını site/arsiv/YYYY-MM-DD.json olarak kaydeder
   (üstüne_yaz=0 ise o günün kuponu zaten varsa dokunmaz).
2) Arşivdeki bütün kuponların seçimlerini geçmiş maç sonuçlarıyla karşılaştırır (tuttu / yattı / bekliyor).
3) site/arsiv/index.json yazar (sitedeki "Geçmiş kuponlar" sekmesi bunu okur).
Kullanım: python3 scripts/arsiv.py <kapanis_maclar.csv> <site/arsiv> [<kupon.json> <üstüne_yaz 0|1>] ...
"""
import sys, os, json, glob, itertools, datetime as dt
import numpy as np, pandas as pd

DB, ARS = sys.argv[1], sys.argv[2]
os.makedirs(ARS, exist_ok=True)
args = sys.argv[3:]
for i in range(0, len(args), 2):
    kaynak, yaz = args[i], args[i + 1] == "1"
    if not os.path.exists(kaynak):
        print("yok:", kaynak); continue
    k = json.load(open(kaynak, encoding="utf-8"))
    iso = dt.datetime.strptime(k["tarih"], "%d/%m/%Y").strftime("%Y-%m-%d")
    hedef = os.path.join(ARS, iso + ".json")
    if yaz or not os.path.exists(hedef):
        json.dump(k, open(hedef, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("arşive yazıldı:", hedef)
    else:
        print("zaten var, korunuyor:", hedef)

# ---- hızlı sonuçlar: bültenin kendi sonuç servisi (maç biter bitmez güncellenir).
# Sonucu bekleyen seçimlerin bülten maç numaralarıyla sonuçları alınır ve geçmiş maç listesine eklenir;
# bulunamazsa football-data sonuçları kullanılır.
import urllib.request
KESIN = ("tuttu", "yatti")
bekleyen, gunler = [], set()
for yol in glob.glob(os.path.join(ARS, "20*.json")):
    for k in json.load(open(yol, encoding="utf-8"))["kuponlar"]:
        for s in k["secimler"]:
            if s.get("idd_id") and s.get("durum") not in KESIN:
                g = dt.datetime.strptime(s["gun"], "%d/%m/%Y")
                if (dt.datetime.now() - g).days > 7: continue
                bekleyen.append(s)
                gunler.update((g + dt.timedelta(days=d)).strftime("%Y%m%d") for d in (-1, 0, 1))
SONUC = {}
for g in sorted(gunler):
    try:
        req = urllib.request.Request(f"https://statisticsv2.iddaa.com/live-results?sportId=1&date={g}",
                                     headers={"User-Agent": "Mozilla/5.0 (oran-motoru)", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            veri = json.loads(r.read().decode("utf-8"))["data"]
    except Exception as e:  # noqa: BLE001
        print("sonuç servisi alınamadı:", g, e); continue
    for k, sc in (veri.get("sc") or {}).items():
        ev, dep = sc.get("ht") or {}, sc.get("at") or {}
        if sc.get("s") == 6 and "r" in ev and "r" in dep:          # 6 = maç bitti
            SONUC[int(k)] = (ev["r"], dep["r"], ev.get("ht"), dep.get("ht"))
ekler = []
for s in bekleyen:
    r = SONUC.get(int(s["idd_id"]))
    if r:
        ekler.append(dict(src="I", league="IDD", season="", date=dt.datetime.strptime(s["gun"], "%d/%m/%Y").strftime("%Y-%m-%d"),
                          home=s["fd_ev"], away=s["fd_dep"], fthg=r[0], ftag=r[1], hthg=r[2], htag=r[3]))
print(f"bülten sonuç servisi: {len(SONUC)} biten maç, bekleyen {len(bekleyen)} seçimden {len(ekler)} tanesinin sonucu bulundu")
SUTUN = ["src", "league", "season", "date", "home", "away", "fthg", "ftag", "hthg", "htag", "b365ch", "b365cd", "b365ca"]
taban = pd.read_csv(DB) if os.path.exists(DB) else pd.DataFrame(columns=SUTUN)
pd.concat([taban, pd.DataFrame(ekler, columns=SUTUN)], ignore_index=True).to_csv("/tmp/arsiv_db.csv", index=False)
DB = "/tmp/arsiv_db.csv"

kod = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kupon.py"), encoding="utf-8").read()
exec(kod[kod.index("# ---- veritabanı"):kod.index("_ON = {}")])   # db, katalog(), hasHT ...

# ---- sonuçlar
tarihler = pd.to_datetime(db.date).dt.strftime("%Y-%m-%d").to_numpy()
IDX = {(d, h, a): i for i, (d, h, a) in enumerate(zip(tarihler, db.home.astype(str), db.away.astype(str)))}


def bul(s):
    g = dt.datetime.strptime(s["gun"], "%d/%m/%Y")
    for k in (0, -1, 1):
        i = IDX.get(((g + dt.timedelta(days=k)).strftime("%Y-%m-%d"), s["fd_ev"], s["fd_dep"]))
        if i is not None:
            return i
    return None


def degerlendir(s):
    if s.get("durum") in KESIN:            # sonucu kesinleşmiş seçim bir daha değişmez
        return s["durum"], s.get("skor")
    if "key" not in s:
        return "bilinmiyor", None
    i = bul(s)
    if i is None:
        return "bekliyor", None
    skor = f"İY {int(h1[i])}-{int(h2[i])} · MS {int(g1[i])}-{int(g2[i])}" if hasHT[i] else f"MS {int(g1[i])}-{int(g2[i])}"
    k = katalog(s["key"], s["sov"], s["sec"])
    if not k or (k[2] and not hasHT[i]):
        return "bilinmiyor", skor
    return ("tuttu" if bool(k[1][i]) else "yatti"), skor


def sistem_donus(secimler):
    n = len(secimler)
    kolon = [c for r in range(2, n + 1) for c in itertools.combinations(range(n), r)]
    return len(kolon), sum(float(np.prod([secimler[i]["oran"] for i in c])) for c in kolon
                           if all(secimler[i]["durum"] == "tuttu" for i in c))


ozet = []
for yol in sorted(glob.glob(os.path.join(ARS, "20*.json"))):
    K = json.load(open(yol, encoding="utf-8"))
    for k in K["kuponlar"]:
        for s in k["secimler"]:
            s["durum"], s["skor"] = degerlendir(s)
        d = [s["durum"] for s in k["secimler"]]
        if not d:
            k["durum"] = "yok"
        elif k["tur"] == "sistem":
            k["tutan"] = d.count("tuttu")
            if "bekliyor" in d:
                k["durum"] = "bekliyor"
            elif "bilinmiyor" in d:
                k["durum"] = "bilinmiyor"
            else:
                kol, don = sistem_donus(k["secimler"])
                k["donus"] = round(don, 2)
                k["durum"] = "tuttu" if don >= kol else "kismen" if don > 0 else "yatti"
        else:
            k["durum"] = ("yatti" if "yatti" in d else "tuttu" if all(x == "tuttu" for x in d)
                          else "bekliyor" if "bekliyor" in d else "bilinmiyor")
    json.dump(K, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ozet.append(dict(tarih=os.path.basename(yol)[:10], gun=K["tarih"], hazirlandi=K.get("hazirlandi"),
                     kuponlar=[dict(ad=k["ad"], tur=k["tur"], durum=k["durum"], toplam_oran=k.get("toplam_oran"),
                                    kolon=k.get("kolon"), donus=k.get("donus"), tutan=k.get("tutan"),
                                    secimler=[dict(mac=s.get("idd_ad") or s["mac"], secim=s["secim"], oran=s["oran"],
                                                   durum=s["durum"], skor=s["skor"], saat=s["saat"], lig=s["lig"])
                                              for s in k["secimler"]])
                               for k in K["kuponlar"]]))
ozet.sort(key=lambda x: x["tarih"], reverse=True)
json.dump(ozet, open(os.path.join(ARS, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
for o in ozet:
    print(o["tarih"], [(k["tur"], k["durum"]) for k in o["kuponlar"]])
