"""Günlük kupon motoru (birebir aynı oran + geniş bahis türleri).
Kullanım: python3 -I kupon.py <kapanis_maclar.csv> <fikstur.txt> <GG/AA/YYYY> <cikti.json> [simdi_TR 'YYYY-MM-DD HH:MM']
"""
import sys, json, io, math, itertools, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

DB, FIX, GUN, OUT = sys.argv[1:5]
SIMDI = dt.datetime.strptime(sys.argv[5], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Istanbul")) if len(sys.argv) > 5 else None
IDD = json.load(open(sys.argv[6], encoding="utf-8")) if len(sys.argv) > 6 else None   # bülten oranları (yoksa sadece uygun maç listesi yazılır)
BANKO_MIN, SURPRIZ_MIN = 2.0, 200.0
MIN_N = 20          # birebir aynı oranlı en az bu kadar geçmiş maç yoksa o maç kupona alınmaz
AYNI_TUR = 2        # bir kuponda aynı bahis türü en fazla bu kadar
SHRINK = 10         # tutma ihtimali tahmininde az örneğe aşırı güvenmemek için
ULKE = {"Argentina": "ARG", "Austria": "AUT", "Brazil": "BRA", "China": "CHN", "Denmark": "DNK", "Finland": "FIN",
        "Ireland": "IRL", "Japan": "JPN", "Mexico": "MEX", "Norway": "NOR", "Poland": "POL", "Romania": "ROU",
        "Russia": "RUS", "Sweden": "SWE", "Switzerland": "SWZ", "USA": "USA"}
LIG = {"E0": "İngiltere Premier Lig", "E1": "İngiltere Championship", "E2": "İngiltere League One", "E3": "İngiltere League Two",
       "EC": "İngiltere National League", "SC0": "İskoçya Premiership", "SC1": "İskoçya Championship", "SC2": "İskoçya League One",
       "SC3": "İskoçya League Two", "D1": "Almanya Bundesliga", "D2": "Almanya 2. Bundesliga", "I1": "İtalya Serie A",
       "I2": "İtalya Serie B", "SP1": "İspanya La Liga", "SP2": "İspanya Segunda", "F1": "Fransa Ligue 1", "F2": "Fransa Ligue 2",
       "N1": "Hollanda Eredivisie", "B1": "Belçika Pro League", "P1": "Portekiz Liga", "T1": "Türkiye Süper Lig",
       "G1": "Yunanistan Super League", "ARG": "Arjantin", "AUT": "Avusturya", "BRA": "Brezilya", "CHN": "Çin", "DNK": "Danimarka",
       "FIN": "Finlandiya", "IRL": "İrlanda", "JPN": "Japonya J1", "MEX": "Meksika", "NOR": "Norveç", "POL": "Polonya",
       "ROU": "Romanya", "RUS": "Rusya", "SWE": "İsveç", "SWZ": "İsviçre", "USA": "ABD MLS"}

# ---- veritabanı
db = pd.read_csv(DB)
O = {"1": db.b365ch.round(2).to_numpy(), "X": db.b365cd.round(2).to_numpy(), "2": db.b365ca.round(2).to_numpy()}
g1, g2 = db.fthg.to_numpy(), db.ftag.to_numpy()
hasHT = db.hthg.notna().to_numpy()
h1, h2 = db.hthg.fillna(0).to_numpy(), db.htag.fillna(0).to_numpy()
top, ht, st = g1 + g2, h1 + h2, (g1 + g2) - (h1 + h2)
ms = np.where(g1 > g2, "1", np.where(g1 < g2, "2", "X"))
iy = np.where(h1 > h2, "1", np.where(h1 < h2, "2", "X"))

# ---- bahis türleri: (ad, kısa, sonuç dizisi, ilk yarı skoru gerekir mi, fikstürdeki oran sütunu)
M = [("Maç sonucu 1", "MS 1", ms == "1", False, "B365H"), ("Maç sonucu X", "MS X", ms == "X", False, "B365D"),
     ("Maç sonucu 2", "MS 2", ms == "2", False, "B365A"),
     ("Çifte şans 1-X", "ÇŞ 1X", ms != "2", False, None), ("Çifte şans X-2", "ÇŞ X2", ms != "1", False, None),
     ("Toplam 1.5 gol üstü", "1.5 Üst", top >= 2, False, None), ("Toplam 1.5 gol altı", "1.5 Alt", top <= 1, False, None),
     ("Toplam 2.5 gol üstü", "2.5 Üst", top >= 3, False, "B365>2.5"), ("Toplam 2.5 gol altı", "2.5 Alt", top <= 2, False, "B365<2.5"),
     ("Toplam 3.5 gol üstü", "3.5 Üst", top >= 4, False, None), ("Toplam 3.5 gol altı", "3.5 Alt", top <= 3, False, None),
     ("Toplam 4.5 gol üstü", "4.5 Üst", top >= 5, False, None),
     ("Karşılıklı gol var", "KG Var", (g1 > 0) & (g2 > 0), False, None), ("Karşılıklı gol yok", "KG Yok", (g1 == 0) | (g2 == 0), False, None),
     ("İlk yarı 0.5 gol üstü", "İY 0.5 Üst", ht >= 1, True, None), ("İlk yarı 1.5 gol üstü", "İY 1.5 Üst", ht >= 2, True, None),
     ("İlk yarı 1.5 gol altı", "İY 1.5 Alt", ht <= 1, True, None),
     ("2. yarı 0.5 gol üstü", "2Y 0.5 Üst", st >= 1, True, None), ("2. yarı 1.5 gol üstü", "2Y 1.5 Üst", st >= 2, True, None),
     ("2. yarı 1.5 gol altı", "2Y 1.5 Alt", st <= 1, True, None)]
for i in "1X2":
    for j in "1X2":
        M.append((f"İlk yarı / maç sonu {i}/{j}", f"İY/MS {i}/{j}", (iy == i) & (ms == j), True, None))
BASE = {m[1]: float(m[2][hasHT].mean() if m[3] else m[2].mean()) for m in M}

def wilson_alt(h, n, z=1.64):
    if n == 0: return 0.0
    p = h / n; d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d

# ---- fikstür
def bolumler(txt):
    out, cur = {}, None
    for line in txt.splitlines():
        if line.startswith("### "): cur = line[4:].strip(); out[cur] = []
        elif cur: out[cur].append(line)
    return {k: pd.read_csv(io.StringIO("\n".join(v)), dtype=str) for k, v in out.items()}
bl = bolumler(open(FIX, encoding="utf-8").read())
fm = bl["/fixtures.csv"]; fm = fm[fm.Date == GUN]
fxx = bl["/new_league_fixtures.csv"]; fxx = fxx[fxx.Date == GUN]
fx = [dict(lig=r["Div"], saat=r["Time"], ev=r["HomeTeam"], dep=r["AwayTeam"], row=r) for _, r in fm.iterrows()]
fx += [dict(lig=ULKE.get(r["Country"], r["Country"]), saat=r["Time"], ev=r["Home"], dep=r["Away"], row=r) for _, r in fxx.iterrows()]

def fnum(v):
    try:
        v = float(v); return v if v > 1 else None
    except (TypeError, ValueError): return None

def tr_saat(saat):
    d = dt.datetime.strptime(GUN + " " + saat, "%d/%m/%Y %H:%M").replace(tzinfo=ZoneInfo("Europe/London"))
    return d.astimezone(ZoneInfo("Europe/Istanbul"))

def pct(v): return f"%{v*100:.0f}"

adaylar, incelenen, yetersiz, uygun = [], 0, 0, []
IDX = {(x["fd_ev"], x["fd_dep"]): x for x in (IDD or [])}
for f in fx:
    r = f["row"]; o = tuple(fnum(r.get(c)) for c in ("B365H", "B365D", "B365A"))
    if None in o: continue
    bas = tr_saat(f["saat"])
    if SIMDI and bas <= SIMDI: continue
    incelenen += 1
    msk = (O["1"] == round(o[0], 2)) & (O["X"] == round(o[1], 2)) & (O["2"] == round(o[2], 2))
    n = int(msk.sum())
    if n < MIN_N: yetersiz += 1; continue
    for t in (0.03, 0.05, 0.08, 0.12, 0.20):
        yak = (np.abs(O["1"] / o[0] - 1) <= t) & (np.abs(O["X"] / o[1] - 1) <= t) & (np.abs(O["2"] / o[2] - 1) <= t)
        if yak.sum() >= 150: break
    utc = bas.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M")
    uygun.append(dict(ev=f["ev"], dep=f["dep"], utc=utc))
    idd = IDX.get((f["ev"], f["dep"]))
    if IDD is not None and not idd: continue
    nh = int((msk & hasHT).sum())
    skorlar = pd.Series([f"{int(a)}-{int(b)}" for a, b in zip(g1[msk], g2[msk])]).value_counts().head(3)
    mac = dict(mbc=(idd or {}).get("mbc", 1), idd_ad=(f"{idd['idd_ev']} – {idd['idd_dep']}" if idd else None), mac=f"{f['ev']} – {f['dep']}", lig=LIG.get(f["lig"], f["lig"]), saat=bas.strftime("%d.%m %H:%M"), oran=o, n=n, nh=nh,
               skorlar=", ".join(f"{s} ({c} kez)" for s, c in skorlar.items()))
    for ad, kisa, sonuc, ht_gerek, ocol in M:
        mm = msk & hasHT if ht_gerek else msk
        nn = int(mm.sum())
        if nn < MIN_N: continue
        hits = int(sonuc[mm].sum()); p = hits / nn
        ym = yak & hasHT if ht_gerek else yak
        base = float(sonuc[ym].mean()) if ym.sum() >= 50 else BASE[kisa]
        adaylar.append(dict(mac=mac, ad=ad, kisa=kisa, n=nn, hits=hits, p=p, wl=wilson_alt(hits, nn), base=base, genel=BASE[kisa],
                            yak_n=int(ym.sum()), tol=t, tahmin=(hits + SHRINK * base) / (nn + SHRINK),
                            oran=(idd["oran"].get(kisa) if idd else None), mbc=max((idd or {}).get("mbc", 1), (idd or {}).get("mbc_m", {}).get(kisa, 1))))
if IDD is None:
    json.dump(uygun, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"uygun maç: {len(uygun)} -> {OUT}"); sys.exit(0)
adaylar = [c for c in adaylar if c["oran"] and c["oran"] > 1.0]

def aciklama(c):
    mc = c["mac"]
    t = (f"Bu maçın uluslararası 1-X-2 oranları {mc['oran'][0]:.2f} – {mc['oran'][1]:.2f} – {mc['oran'][2]:.2f}. Geçmişte birebir aynı oranlarla "
         f"oynanmış {mc['n']} maç var. ")
    if c["n"] != mc["n"]: t += f"Bunların ilk yarı skoru bilinen {c['n']} tanesinin "
    else: t += "Bunların "
    t += (f"{c['hits']} tanesinde ({pct(c['p'])}) \"{c['ad']}\" oldu. Oranı buna yakın (her biri ±%{c['tol']*100:.0f}) {c['yak_n']} maçta "
          f"bu sonuç {pct(c['base'])} çıkmış")
    kat = c["p"] / c["base"] if c["base"] else 0
    t += f"; yani birebir bu oranlarda {kat:.1f} kat daha sık görülmüş." if kat >= 1.3 else "."
    t += f" Bu oranlı maçlarda en sık skorlar: {mc['skorlar']}."
    if c["n"] < 40: t += f" Not: örnek sayısı ({c['n']}) az, sonuç şanstan etkilenmiş olabilir."
    return t

def sec(havuz, adet, anahtar, kullanildi):
    out = []
    for c in sorted(havuz, key=anahtar, reverse=True):
        if c["mac"]["mac"] in kullanildi: continue
        if sum(x["kisa"] == c["kisa"] for x in out) >= AYNI_TUR: continue
        out.append(c); kullanildi.add(c["mac"]["mac"])
        if len(out) == adet: break
    return out

def satir(c):
    return dict(mac=c["mac"]["mac"], idd_ad=c["mac"]["idd_ad"], mbs=c["mbc"], lig=c["mac"]["lig"], saat=c["mac"]["saat"], secim=c["ad"], kisa=c["kisa"],
                oran=round(c["oran"], 2) if c["oran"] else None, gecmis=round(c["p"], 3), ortalama=round(c["base"], 3), yakin_n=c["yak_n"],
                olasilik=round(c["tahmin"], 3), n=c["n"], hits=c["hits"], aciklama=aciklama(c))

def kur(havuz, hedef, anahtar, kullanildi, en_cok=8, tavan=None):
    """Havuzdan farklı maçlardan seçerek toplam bülten oranı hedefe ulaşana kadar ekle; MBS kuralına uy.
    tavan verilirse toplamı tavanın üstüne çıkaracak seçim atlanır."""
    out, toplam = [], 1.0
    for c in sorted(havuz, key=anahtar):
        if c["mac"]["mac"] in kullanildi or c["mac"]["mac"] in {x["mac"]["mac"] for x in out}: continue
        if tavan and toplam * c["oran"] > tavan: continue
        if sum(x["kisa"] == c["kisa"] for x in out) >= AYNI_TUR: continue
        out.append(c); toplam *= c["oran"]
        if toplam >= hedef and len(out) >= max(x["mbc"] for x in out): break
        if len(out) >= en_cok: break
    for c in out: kullanildi.add(c["mac"]["mac"])
    return out

# MANTIK KURALI: bir seçim ancak hem birebir aynı oranlı maçlarda hem de oranı yakın daha geniş maç grubunda
# destekleniyorsa kupona girer (küçük örnekteki şans eseri sonuçları elemek için).
# banko: birebir grupta en az %72, geniş grupta en az %62 tutan, oranı 1.15-1.75 arası seçimler; toplam oran 2.00-3.50
bh = [c for c in adaylar if c["p"] >= 0.72 and c["base"] >= 0.62 and c["tahmin"] >= 0.65 and 1.15 <= c["oran"] <= 1.75]
kul = set()
banko = kur(bh, BANKO_MIN, lambda c: -math.log(c["tahmin"]) / math.log(c["oran"]), kul, en_cok=5, tavan=3.5)
# sürpriz: oranı 2.5-12 arası, iki grupta da en az %8 görülen ve birebir grupta belirgin sık çıkan sonuçlar;
# hedef toplam oran 200, en fazla ~500'e kadar
sh = [c for c in adaylar if 2.5 <= c["oran"] <= 12 and c["base"] >= 0.08 and c["p"] >= 1.3 * c["base"] and c["hits"] >= 5]
surpriz = kur(sh, SURPRIZ_MIN, lambda c: -(c["tahmin"] * c["oran"]), set(kul), en_cok=6, tavan=SURPRIZ_MIN * 2.5)
# sistem: oranı 1.6-4.0 arası, iki grupta da en az %30 tutan 6 seçim
yh = [c for c in adaylar if 1.6 <= c["oran"] <= 4.0 and c["base"] >= 0.30 and c["p"] >= c["base"] and c["tahmin"] >= 0.35]
sistem = sec(yh, 6, lambda c: c["tahmin"] * c["oran"], {c["mac"]["mac"] for c in surpriz} | {c["mac"]["mac"] for c in banko})

def kupon_ozet(s):
    od = [c["oran"] for c in s]
    return dict(toplam_oran=round(float(np.prod(od)), 2) if s and all(od) else None,
                tutma_olasiligi=round(float(np.prod([c["tahmin"] for c in s])), 4) if s else 0)

def sistem_ozet(s):
    ps = [c["tahmin"] for c in s]; od = [c["oran"] for c in s]; nn = len(s)
    kombo = [cmb for k in range(2, nn + 1) for cmb in itertools.combinations(range(nn), k)]
    dag = [1.0] + [0.0] * nn
    for p in ps: dag = [dag[i] * (1 - p) + (dag[i - 1] * p if i else 0) for i in range(nn + 1)]
    tablo = []
    for t in range(nn + 1):
        row = dict(tutan=t, olasilik=round(dag[t], 4), en_az=None, en_cok=None)
        if all(od):
            kaz = [sum(float(np.prod([od[i] for i in cmb])) for cmb in kombo if set(cmb) <= set(tt))
                   for tt in itertools.combinations(range(nn), t)]
            row.update(en_az=round(min(kaz), 2), en_cok=round(max(kaz), 2))
        tablo.append(row)
    return dict(kolon=len(kombo), tablo=tablo)

uyari = []
if not banko or float(np.prod([c["oran"] for c in banko])) < BANKO_MIN: uyari.append("Banko kupon 2,00 toplam orana ulaşamadı.")
if not surpriz or float(np.prod([c["oran"] for c in surpriz])) < SURPRIZ_MIN: uyari.append("Sürpriz kupon 200 toplam orana ulaşamadı.")
if len(sistem) < 6: uyari.append("Sistem kuponu için 6 uygun seçim bulunamadı.")
uyari = " ".join(uyari) or None

sonuc = dict(tarih=GUN, hazirlandi=dt.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M"),
             mac_sayisi=incelenen, uygun_mac=incelenen - yetersiz, eslesen=len(IDD), min_n=MIN_N, uyari=uyari,
             kuponlar=[
                 dict(ad="Banko kupon", tur="banko", secimler=[satir(c) for c in banko], **kupon_ozet(banko),
                      not_="Hem birebir aynı oranlı maçlarda hem de benzer oranlı geniş maç grubunda en sık tutan seçimler; toplam oran 2,00 ve üzeri. Hepsinin birden tutması gerekir."),
                 dict(ad="Sürpriz kupon", tur="sürpriz", secimler=[satir(c) for c in surpriz], **kupon_ozet(surpriz),
                      not_="Oranı yüksek ama birebir aynı oranlı maçlarda beklenenden sık çıkmış sonuçlar; toplam oran 200 civarı. Tutma ihtimali çok düşük."),
                 dict(ad="Sistem 2-3-4-5-6", tur="sistem", secimler=[satir(c) for c in sistem], **sistem_ozet(sistem),
                      not_="6 seçimden 2'li, 3'lü, 4'lü, 5'li ve 6'lı bütün kombinasyonlar. 2 seçim tutsa bile bir kolon kazanır."),
             ])
json.dump(sonuc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(dict(incelenen=incelenen, uygun=incelenen - yetersiz, aday=len(adaylar), uyari=uyari), ensure_ascii=False))
for k in sonuc["kuponlar"]:
    print("\n==", k["ad"], {a: k[a] for a in ("toplam_oran", "tutma_olasiligi", "kolon") if a in k})
    for s in k["secimler"]:
        print(f"  {s['saat']} {s['mac']} [{s['lig']}] -> {s['kisa']} oran={s['oran']} gecmis={s['hits']}/{s['n']}={s['gecmis']} ort={s['ortalama']} tahmin={s['olasilik']}")
