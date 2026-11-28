"""Günün kuponlarını yayınlar: her kupon, ilk maçına 1 saatten az kaldığında BİR KEZ site/arsiv/YYYY-MM-DD.json'a eklenir
ve bir daha hiç değişmez (sonuçları dışında). Henüz zamanı gelmemiş kuponlar bir sonraki çalışmada yeniden seçilir.
Kullanım: python3 scripts/yayinla.py <kupon_bugun.json> <site/arsiv>
"""
import sys, os, json, time, urllib.request, datetime as dt
from zoneinfo import ZoneInfo

# Telefon bildirimi: ntfy uygulamasında bu konuya abone olan herkese "yeni kupon" bildirimi gider.
NTFY_KONU = os.environ.get("NTFY_KONU", "oran-motoru-2ff4f1e5")
SITE = "https://bdrnagdl.github.io/oran-motoru/#kuponlar"


def bildir(k):
    saat = dt.datetime.fromtimestamp(k["ilk_mac"], ZoneInfo("Europe/Istanbul")).strftime("%H:%M")
    oran = f"toplam oran {k['toplam_oran']:.2f}".replace(".", ",") if k.get("toplam_oran") else f"{k.get('kolon')} kolon"
    satirlar = [f"{s.get('idd_ad') or s['mac']}: {s['secim']} ({s['oran']:.2f})" for s in k["secimler"]]
    govde = dict(topic=NTFY_KONU, title=f"Yeni kupon: {k['ad']}", click=SITE, tags=["soccer"],
                 message=f"İlk maç {saat}, {oran}.\n" + "\n".join(satirlar))
    try:
        req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(govde).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        print("bildirim gönderildi:", k["ad"])
    except Exception as e:  # noqa: BLE001  bildirim gitmese de kupon yayınlanır
        print("bildirim gönderilemedi:", e)


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
        bildir(k)
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
