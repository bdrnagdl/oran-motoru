"""Günün kuponlarını yayınlar: her kupon, ilk maçına 1 saatten az kaldığında BİR KEZ site/arsiv/YYYY-MM-DD.json'a eklenir
ve bir daha hiç değişmez (sonuçları dışında). Henüz zamanı gelmemiş kuponlar bir sonraki çalışmada yeniden seçilir.
Kullanım: python3 scripts/yayinla.py <kupon_bugun.json> <site/arsiv>
"""
import sys, os, json, time, datetime as dt
from zoneinfo import ZoneInfo

kaynak, ARS = sys.argv[1], sys.argv[2]
if not os.path.exists(kaynak):
    print("kupon dosyası yok:", kaynak); sys.exit(0)
K = json.load(open(kaynak, encoding="utf-8"))
SIRA = [k["kod"] for k in K["kuponlar"]]
iso = dt.datetime.strptime(K["tarih"], "%d/%m/%Y").strftime("%Y-%m-%d")
hedef = os.path.join(ARS, iso + ".json")
os.makedirs(ARS, exist_ok=True)
A = json.load(open(hedef, encoding="utf-8")) if os.path.exists(hedef) else dict(tarih=K["tarih"], kuponlar=[])
var = {k.get("kod") for k in A["kuponlar"]}
simdi = time.time()
yeni = 0
for k in K["kuponlar"]:
    if k["kod"] in var or not k["secimler"] or not k.get("ilk_mac"):
        continue
    kalan = k["ilk_mac"] - simdi
    if kalan <= 60 * 60:
        k["yayinlandi"] = dt.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M")
        A["kuponlar"].append(k); yeni += 1
        print(f"yayınlandı: {k['ad']} (ilk maça {kalan / 60:.0f} dk)")
    else:
        print(f"bekliyor: {k['ad']} (ilk maça {kalan / 60:.0f} dk)")
if yeni or not os.path.exists(hedef):
    A["kuponlar"].sort(key=lambda k: SIRA.index(k["kod"]) if k.get("kod") in SIRA else 99)
    for a in ("mac_sayisi", "uygun_mac", "min_n"):
        A[a] = K.get(a)
    A["hazirlandi"] = A["kuponlar"][-1]["yayinlandi"] if A["kuponlar"] else None
    if A["kuponlar"]:
        json.dump(A, open(hedef, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("arşiv:", hedef, len(A["kuponlar"]), "kupon")
