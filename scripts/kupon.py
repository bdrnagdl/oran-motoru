"""Günlük kupon motoru.
Seçimler: birebir aynı 1-X-2 kapanış oranlı geçmiş maçlar + bültendeki her bahis türü (geçmiş skorlardan hesaplanabilenler).
Kullanım:
  1) uygun maç listesi:  python3 kupon.py <kapanis_maclar.csv> <fikstur.txt> <GG/AA/YYYY> <uygun.json> [simdi 'YYYY-MM-DD HH:MM']
  2) kuponlar:           python3 kupon.py <kapanis_maclar.csv> <fikstur.txt> <GG/AA/YYYY> <kuponlar.json> <simdi> <bulten.json>
"""
import sys, json, io, math, itertools, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

DB, FIX, GUN, OUT = sys.argv[1:5]
SIMDI = dt.datetime.strptime(sys.argv[5], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Istanbul")) if len(sys.argv) > 5 else None
IDD = json.load(open(sys.argv[6], encoding="utf-8")) if len(sys.argv) > 6 else None
HAVUZ = sys.argv[7] if len(sys.argv) > 7 else None   # kupon oluşturma için seçenek havuzu
BANKO_MIN, BANKO_MAX = 2.0, 3.5
SURPRIZ_MIN, SURPRIZ_MAX = 200.0, 3000.0
MIN_N = 20          # birebir aynı oranlı en az bu kadar geçmiş maç yoksa o maç kupona alınmaz
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
s1, s2 = g1 - h1, g2 - h2                      # ikinci yarı golleri
top, ht, st = g1 + g2, h1 + h2, s1 + s2


def sonuc(a, b):
    return np.where(a > b, "1", np.where(a < b, "2", "X"))


ms, iy, y2 = sonuc(g1, g2), sonuc(h1, h2), sonuc(s1, s2)
kg, iykg, y2kg = (g1 > 0) & (g2 > 0), (h1 > 0) & (h2 > 0), (s1 > 0) & (s2 > 0)
X = {"1": "1", "0": "X", "2": "2"}
AU = {"Alt": "alt", "Üst": "üst"}


def au(dizi, cizgi, n):
    return dizi < cizgi if n == "Alt" else dizi > cizgi


def katalog(key, sov, n):
    """Bültendeki bir bahis seçeneğini geçmiş skorlardan hesaplanabilir hale getirir.
    Dönüş: (Türkçe ad, sonuç dizisi, ilk yarı skoru gerekir mi) ya da None."""
    try:
        c = float(sov) if sov not in (None, "") else None
    except ValueError:
        c = None
    ev = {"Evet": True, "Hayır": False}
    if key == "1_1" and n in X: return f"Maç sonucu {X[n]}", ms == X[n], False
    if key == "2_92":
        d = {"1 ve 0": ("1-X", ms != "2"), "1 ve 2": ("1-2", ms != "X"), "0 ve 2": ("X-2", ms != "1")}
        if n in d: return f"Çifte şans {d[n][0]}", d[n][1], False
    if key == "2_101" and c is not None and n in AU: return f"Toplam {sov} gol {AU[n]}", au(top, c, n), False
    if key == "2_89" and n in ("Var", "Yok"): return f"Karşılıklı gol {n.lower()}", kg if n == "Var" else ~kg, False
    if key == "2_60" and c is not None and n in AU: return f"İlk yarı {sov} gol {AU[n]}", au(ht, c, n), True
    if key == "2_90" and n and "/" in n:
        a, b = n.split("/")
        if a in X and b in X: return f"İlk yarı / maç sonu {X[a]}/{X[b]}", (iy == X[a]) & (ms == X[b]), True
    if key == "2_88" and n in X: return f"İlk yarı sonucu {X[n]}", iy == X[n], True
    if key == "2_36" and n in X: return f"2. yarı sonucu {X[n]}", y2 == X[n], True
    if key == "2_720" and n in ("Var", "Yok"): return f"İlk yarı karşılıklı gol {n.lower()}", iykg if n == "Var" else ~iykg, True
    if key == "2_821" and n in ("Var", "Yok"): return f"2. yarı karşılıklı gol {n.lower()}", y2kg if n == "Var" else ~y2kg, True
    if key == "2_866" and n and " / " in n:
        a, b = n.split(" / ")
        if a in ev and b in ev:
            return (f"1. yarı KG {'var' if ev[a] else 'yok'} / 2. yarı KG {'var' if ev[b] else 'yok'}",
                    (iykg == ev[a]) & (y2kg == ev[b]), True)
    if key == "2_730" and n in ev: return f"Her iki yarıda 1.5 üst: {n.lower()}", ((ht >= 2) & (st >= 2)) == ev[n], True
    if key == "2_729" and n in ev: return f"Her iki yarıda 1.5 alt: {n.lower()}", ((ht <= 1) & (st <= 1)) == ev[n], True
    if key in ("2_7", "2_698", "2_699", "2_724", "2_700") and n and " ve " in n:
        a, b = n.split(" ve ")
        if key == "2_7" and a in X and b in AU and c is not None:
            return f"Maç sonucu {X[a]} ve {sov} {AU[b]}", (ms == X[a]) & au(top, c, b), False
        if key == "2_698" and a in X and b in ("Var", "Yok"):
            return f"Maç sonucu {X[a]} ve KG {b.lower()}", (ms == X[a]) & (kg if b == "Var" else ~kg), False
        if key == "2_699" and a in X and b in ("Var", "Yok"):
            return f"İlk yarı {X[a]} ve İY KG {b.lower()}", (iy == X[a]) & (iykg if b == "Var" else ~iykg), True
        if key == "2_724" and a in X and b in AU and c is not None:
            return f"İlk yarı {X[a]} ve İY {sov} {AU[b]}", (iy == X[a]) & au(ht, c, b), True
        if key == "2_700" and a in AU and b in ("Var", "Yok") and c is not None:
            return f"Toplam {sov} {AU[a]} ve KG {b.lower()}", au(top, c, a) & (kg if b == "Var" else ~kg), False
    if key == "2_6":
        d = {"1.": ht > st, "Eşit": ht == st, "2.": st > ht}
        if n in d: return f"En çok gol: {'1. yarı' if n == '1.' else '2. yarı' if n == '2.' else 'eşit'}", d[n], True
    if key in ("2_84", "2_85"):
        a, b = (h1, s1) if key == "2_84" else (h2, s2)
        kim = "Ev sahibi" if key == "2_84" else "Deplasman"
        d = {"1.": a > b, "Eşit": a == b, "2.": b > a}
        if n in d: return f"{kim} en çok golü: {'1. yarı' if n == '1.' else '2. yarı' if n == '2.' else 'eşit'}", d[n], True
    if key == "2_4":
        d = {"0-1 gol": top <= 1, "2-3 gol": (top >= 2) & (top <= 3), "4-5 gol": (top >= 4) & (top <= 5), "6+ gol": top >= 6}
        if n in d: return f"Toplam gol {n}", d[n], False
    if key in ("2_603", "2_604") and c is not None and n in AU:
        return f"{'Ev sahibi' if key == '2_603' else 'Deplasman'} {sov} gol {AU[n]}", au(g1 if key == "2_603" else g2, c, n), False
    if key in ("2_722", "2_723") and c is not None and n in AU:
        return f"{'Ev sahibi' if key == '2_722' else 'Deplasman'} ilk yarı {sov} gol {AU[n]}", au(h1 if key == "2_722" else h2, c, n), True
    if key == "2_91" and n in ("Tek", "Çift"): return f"Toplam gol {n.lower()}", (top % 2 == 1) == (n == "Tek"), False
    if key == "2_719" and n in ("Tek", "Çift"): return f"İlk yarı gol {n.lower()}", (ht % 2 == 1) == (n == "Tek"), True
    if key in ("2_69", "2_72") and n in ev:
        a = (h1 > h2) & (s1 > s2) if key == "2_69" else (h2 > h1) & (s2 > s1)
        return f"{'Ev sahibi' if key == '2_69' else 'Deplasman'} iki yarıyı da kazanır: {n.lower()}", a == ev[n], True
    if key in ("2_727", "2_728") and n in ev:
        a = (h1 > h2) | (s1 > s2) if key == "2_727" else (h2 > h1) | (s2 > s1)
        return f"{'Ev sahibi' if key == '2_727' else 'Deplasman'} en az bir yarıyı kazanır: {n.lower()}", a == ev[n], True
    if key in ("2_861", "2_862") and n in ev:
        a = (h1 > 0) & (s1 > 0) if key == "2_861" else (h2 > 0) & (s2 > 0)
        return f"{'Ev sahibi' if key == '2_861' else 'Deplasman'} iki yarıda da gol atar: {n.lower()}", a == ev[n], True
    if key == "2_11":
        f = g1 - g2
        d = {"Ev 3+": f >= 3, "Ev 2": f == 2, "Ev 1": f == 1, "0": f == 0, "Dep 1": f == -1, "Dep 2": f == -2, "Dep 3+": f <= -3}
        if n in d: return f"Fark: {n if n != '0' else 'beraberlik'}", d[n], False
    if key == "2_100" and c is not None and n in X:
        hs = sonuc(g1 + c, g2)
        return f"Handikaplı maç sonucu (ev sahibi {c:+g}) {X[n]}", hs == X[n], False
    return None


_ON = {}
def katalog_onbellek(key, sov, n):
    k = (key, sov, n)
    if k not in _ON: _ON[k] = katalog(key, sov, n)
    return _ON[k]


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
fx = [dict(lig=r["Div"], saat=r["Time"], ev=r["HomeTeam"], dep=r["AwayTeam"], row=r, ht=True) for _, r in fm.iterrows()]
fx += [dict(lig=ULKE.get(r["Country"], r["Country"]), saat=r["Time"], ev=r["Home"], dep=r["Away"], row=r, ht=False) for _, r in fxx.iterrows()]


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
# Geçmiş maçlar kapanış oranıyla kayıtlı; yaklaşan maçın kapanış oranı henüz yok. Fikstürdeki oran günler önce
# alınmış olabilir. Bültendeki güncel 1-X-2 oranı belirgin farklıysa (piyasa en az 5 puan oynamışsa) "yakın oranlı
# maçlar" grubunu onun uluslararası karşılığının çevresinde kurarız: büro payı çıkarılıp uluslararası paya (MARJ) çevrilir.
# Birebir aynı oranlı grup (yalnızca bilgi amaçlı) fikstür oranıyla kalır.
MARJ = 1.074
_say = pd.Series(np.concatenate([O["1"], O["X"], O["2"]])).value_counts()
MERDIVEN = np.array(sorted(v for v, c in _say.items() if v > 1 and c >= 30))
def yuvarla(v): return float(MERDIVEN[np.abs(MERDIVEN - v).argmin()])
def guncel_oran(idd, o):
    x = {n: v for key, sov, n, v, mb in (idd or {}).get("secenekler", []) if key == "1_1"}
    if not all(k in x for k in ("1", "0", "2")): return o, False
    pi = [1 / x["1"], 1 / x["0"], 1 / x["2"]]; si = sum(pi)
    pf = [1 / v for v in o]; sf = sum(pf)
    if max(abs(a / si - b / sf) for a, b in zip(pi, pf)) < 0.05: return o, False
    return tuple(yuvarla(1 / (a / si * MARJ)) for a in pi), True
for f in fx:
    r = f["row"]; o = tuple(fnum(r.get(c)) for c in ("B365H", "B365D", "B365A"))
    if None in o: continue
    bas = tr_saat(f["saat"])
    if SIMDI and bas <= SIMDI: continue
    incelenen += 1
    oy, degisti = guncel_oran(IDX.get((f["ev"], f["dep"])), o)
    msk = (O["1"] == round(o[0], 2)) & (O["X"] == round(o[1], 2)) & (O["2"] == round(o[2], 2))
    n = int(msk.sum())
    if n < MIN_N: yetersiz += 1; continue
    for t in (0.03, 0.05, 0.08, 0.12, 0.20):
        yak = (np.abs(O["1"] / oy[0] - 1) <= t) & (np.abs(O["X"] / oy[1] - 1) <= t) & (np.abs(O["2"] / oy[2] - 1) <= t)
        if yak.sum() >= 150: break
    uygun.append(dict(ev=f["ev"], dep=f["dep"], utc=bas.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M")))
    idd = IDX.get((f["ev"], f["dep"]))
    if IDD is None or not idd: continue
    skorlar = pd.Series([f"{int(a)}-{int(b)}" for a, b in zip(g1[msk], g2[msk])]).value_counts().head(3)
    mac = dict(idd_id=idd.get("id"), mbc=idd.get("mbc", 1), idd_ad=f"{idd['idd_ev']} – {idd['idd_dep']}", mac=f"{f['ev']} – {f['dep']}",
               lig=LIG.get(f["lig"], f["lig"]), saat=bas.strftime("%d.%m %H:%M"), oran=o, n=n, t=int(bas.timestamp()), oran_guncel=[round(v, 2) for v in oy] if degisti else None,
               fd_ev=f["ev"], fd_dep=f["dep"],
               skorlar=", ".join(f"{s} ({c} kez)" for s, c in skorlar.items()))
    for key, sov, ad_n, oran, mbc in idd.get("secenekler", []):
        k = katalog_onbellek(key, sov, ad_n)
        if not k: continue
        ad, dizi, ht_gerek = k
        if ht_gerek and not f["ht"]: continue   # bu ligde ilk yarı skoru tutulmuyor, sonucu kontrol edilemez
        mm = msk & hasHT if ht_gerek else msk
        nn = int(mm.sum())
        if nn < MIN_N: continue
        hits = int(dizi[mm].sum()); p = hits / nn
        ym = yak & hasHT if ht_gerek else yak
        if ym.sum() < 50: continue
        base = float(dizi[ym].mean())
        tahmin = base   # testte gerçek tutma oranı birebir aynı oranlı % değil, yakın oranlı % ile örtüştü
        adaylar.append(dict(mac=mac, ad=ad, tur=key, n=nn, hits=hits, p=p, wl=wilson_alt(hits, nn), base=base, yak_n=int(ym.sum()),
                            tol=t, tahmin=tahmin, oran=float(oran), deger=tahmin * float(oran), mbc=max(mac["mbc"], mbc or 1),
                            sov=sov, sec=ad_n))
if IDD is None:
    json.dump(uygun, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"uygun maç: {len(uygun)} -> {OUT}"); sys.exit(0)


if HAVUZ:
    ML, MI, SEC = [], {}, []
    for c in adaylar:
        if c["hits"] < 3 or not 1.05 <= c["oran"] <= 40: continue
        mc = c["mac"]
        if mc["mac"] not in MI:
            MI[mc["mac"]] = len(ML)
            ML.append(dict(ad=mc["idd_ad"], id=mc["idd_id"], lig=mc["lig"], saat=mc["saat"], t=mc["t"], n=mc["n"], oran=[round(v, 2) for v in mc["oran"]],
                           skorlar=mc["skorlar"]))
        SEC.append([MI[mc["mac"]], c["ad"], round(c["oran"], 2), int(c["mbc"]), c["hits"], c["n"], round(c["base"], 3), round(c["tahmin"], 3), c["tur"], c["sov"], c["sec"]])
    json.dump(dict(tarih=GUN, maclar=ML, secenekler=SEC), open(HAVUZ, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"havuz: {len(ML)} maç, {len(SEC)} seçenek -> {HAVUZ}")


def aciklama(c):
    mc = c["mac"]
    t = (f"Bu maçın uluslararası 1-X-2 oranları {mc['oran'][0]:.2f} – {mc['oran'][1]:.2f} – {mc['oran'][2]:.2f}. Geçmişte birebir aynı oranlarla "
         f"oynanmış {mc['n']} maç var. ")
    t += f"Bunların ilk yarı skoru bilinen {c['n']} tanesinin " if c["n"] != mc["n"] else "Bunların "
    t += (f"{c['hits']} tanesinde ({pct(c['p'])}) \"{c['ad']}\" oldu. Oranı buna yakın (her biri ±%{c['tol']*100:.0f}) {c['yak_n']} maçta "
          f"bu sonuç {pct(c['base'])} çıkmış")
    t += (". Gerçekçi ihtimal olarak yakın oranlı maçlardaki yüzdeyi kullanıyoruz: 2,5 yıllık testte gerçek sonuçlar ona uydu, "
          "birebir aynı oranlı az sayıda maçtan çıkan yüzde ise çoğunlukla şanstan dolayı fazla görünüyordu.")
    t += f" Bültendeki oranı {c['oran']:.2f}; bu oran bu sonuca yaklaşık {pct(1 / c['oran'])} ihtimal veriyor."
    t += f" Bu oranlı maçlarda en sık skorlar: {mc['skorlar']}."
    if c["n"] < 40: t += f" Not: örnek sayısı ({c['n']}) az, sonuç şanstan etkilenmiş olabilir."
    return t


def kur(havuz, anahtar, kullanildi, hedef=None, tavan=None, adet=None, en_cok=8, ayni_tur=2):
    """Farklı maçlardan seçim yapar. hedef: toplam oran bu değere ulaşınca dur; adet: bu kadar seçimde dur."""
    out, toplam = [], 1.0
    for c in sorted(havuz, key=anahtar, reverse=True):
        if c["mac"]["mac"] in kullanildi or any(x["mac"]["mac"] == c["mac"]["mac"] for x in out): continue
        if tavan and toplam * c["oran"] > tavan: continue
        if sum(x["tur"] == c["tur"] for x in out) >= ayni_tur: continue
        out.append(c); toplam *= c["oran"]
        if hedef and toplam >= hedef and len(out) >= max(x["mbc"] for x in out): break
        if adet and len(out) == adet: break
        if len(out) >= en_cok: break
    for c in out: kullanildi.add(c["mac"]["mac"])
    return out


def satir(c):
    return dict(mac=c["mac"]["mac"], idd_ad=c["mac"]["idd_ad"], mbs=c["mbc"], lig=c["mac"]["lig"], saat=c["mac"]["saat"], secim=c["ad"],
                oran=round(c["oran"], 2), gecmis=round(c["p"], 3), ortalama=round(c["base"], 3), yakin_n=c["yak_n"],
                olasilik=round(c["tahmin"], 3), n=c["n"], hits=c["hits"], aciklama=aciklama(c),
                key=c["tur"], sov=c["sov"], sec=c["sec"], fd_ev=c["mac"]["fd_ev"], fd_dep=c["mac"]["fd_dep"], gun=GUN, t=c["mac"]["t"], idd_id=c["mac"]["idd_id"])


# banko: hem birebir hem geniş grupta yüksek tutan, düşük oranlı seçimler; toplam oran 2.00-3.50
kul = set()
bh = [c for c in adaylar if c["base"] >= 0.65 and 1.15 <= c["oran"] <= 1.75]
banko = kur(bh, lambda c: math.log(c["oran"]) / -math.log(c["tahmin"]), kul, hedef=BANKO_MIN, tavan=BANKO_MAX, en_cok=5)

# DEĞER: tahmini ihtimal x bülten oranı. 1'in üstü = geçmişe göre oran, sonucun gerçek sıklığından yüksek.
# sürpriz: oranı 3-25 arası, birebir grupta en az 5 kez görülmüş ve yakın oranlardakinin belirgin üstünde çıkmış,
# değeri en yüksek seçimler; toplam oran en az 200.
sh = [c for c in adaylar if 3.0 <= c["oran"] <= 25 and c["hits"] >= 3 and c["deger"] >= 0.95]
surpriz = kur(sh, lambda c: c["deger"], set(kul), hedef=SURPRIZ_MIN, tavan=SURPRIZ_MAX, en_cok=6, ayni_tur=1)

# sistem: oranı 2.5-15 arası, değeri yüksek 6 seçim (her biri tek başına da yüksek oranlı)
yh = [c for c in adaylar if 2.5 <= c["oran"] <= 15 and c["hits"] >= 3 and c["deger"] >= 0.95]
sistem = kur(yh, lambda c: c["deger"], {c["mac"]["mac"] for c in surpriz} | set(kul), adet=6, ayni_tur=2)
if len(sistem) < 6:
    sistem = kur(yh, lambda c: c["deger"], set(kul), adet=6, ayni_tur=2)

# iki yarı 1.5 üst: aynı oranlı maçlarda "ilk yarı 1.5 üst ve 2. yarı 1.5 üst" en sık olan 3 maç, sistem 2-3
yari = kur([c for c in adaylar if c["tur"] == "2_730" and c["sec"] == "Evet" and c["hits"] >= 3],
           lambda c: c["tahmin"], set(), adet=3, ayni_tur=3)

# İY/MS: ilk yarı ile maç sonunun farklı bittiği sonuçlar (1/X, X/1, 2/X, X/2, 1/2, 2/1), değeri en yüksek 3 maç
DONUS = {"1/0", "0/1", "2/0", "0/2", "1/2", "2/1"}
iyms = kur([c for c in adaylar if c["tur"] == "2_90" and c["sec"] in DONUS and c["hits"] >= 3],
           lambda c: c["deger"], set(), adet=3, ayni_tur=3)


def kupon_ozet(s):
    return dict(toplam_oran=round(float(np.prod([c["oran"] for c in s])), 2) if s else None,
                tutma_olasiligi=round(float(np.prod([c["tahmin"] for c in s])), 5) if s else 0)


def sistem_ozet(s):
    ps = [c["tahmin"] for c in s]; od = [c["oran"] for c in s]; nn = len(s)
    kombo = [cmb for k in range(2, nn + 1) for cmb in itertools.combinations(range(nn), k)]
    dag = [1.0] + [0.0] * nn
    for p in ps: dag = [dag[i] * (1 - p) + (dag[i - 1] * p if i else 0) for i in range(nn + 1)]
    tablo = []
    for t in range(nn + 1):
        kaz = [sum(float(np.prod([od[i] for i in cmb])) for cmb in kombo if set(cmb) <= set(tt))
               for tt in itertools.combinations(range(nn), t)]
        tablo.append(dict(tutan=t, olasilik=round(dag[t], 4), en_az=round(min(kaz), 2), en_cok=round(max(kaz), 2)))
    return dict(kolon=len(kombo), tablo=tablo)


# en başarılı 5'li: her maç için yakın oranlı maçlarda en sık tutan bahis (oran en az 1.30), en yüksek 5 maç
def en_iyi_tek(L, kosul, anahtar):
    L = [c for c in L if kosul(c)]
    return max(L, key=anahtar) if L else None
MACLAR = {}
for c in adaylar: MACLAR.setdefault(c["mac"]["mac"], []).append(c)
enb = [en_iyi_tek(L, lambda c: c["oran"] >= 1.30, lambda c: (c["base"], c["p"])) for L in MACLAR.values()]
enb = sorted([c for c in enb if c], key=lambda c: (c["base"], c["p"]), reverse=True)[:5]

# en yakın 4 maç: banko (oran en az 1.20, en sık tutan) ve sürpriz (oran en az 3.00, değeri en yüksek)
yakin = sorted(MACLAR.values(), key=lambda L: L[0]["mac"]["t"])[:4]
y4b, y4s = [], []
for L in yakin:
    b = en_iyi_tek(L, lambda c: c["oran"] >= 1.20, lambda c: (c["base"], c["p"]))
    s = (en_iyi_tek(L, lambda c: c["oran"] >= 3 and c["deger"] >= 0.95 and (not b or c["ad"] != b["ad"]), lambda c: c["tahmin"] * c["oran"])
         or en_iyi_tek(L, lambda c: c["oran"] >= 3 and (not b or c["ad"] != b["ad"]), lambda c: c["tahmin"] * c["oran"]))
    if b: y4b.append(b)
    if s: y4s.append(s)

uyari = []
if not banko or float(np.prod([c["oran"] for c in banko])) < BANKO_MIN: uyari.append("Banko kupon 2,00 toplam orana ulaşamadı.")
if not surpriz or float(np.prod([c["oran"] for c in surpriz])) < SURPRIZ_MIN: uyari.append("Sürpriz kupon 200 toplam orana ulaşamadı.")
if len(sistem) < 6: uyari.append("Sistem kuponu için 6 uygun seçim bulunamadı.")
if len(yari) < 3: uyari.append("İki yarı 1.5 üst kuponu için 3 uygun maç bulunamadı.")
if len(iyms) < 3: uyari.append("İY/MS kuponu için 3 uygun maç bulunamadı.")
uyari = " ".join(uyari) or None

sonuc_json = dict(
    tarih=GUN, hazirlandi=dt.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M"),
    mac_sayisi=incelenen, uygun_mac=incelenen - yetersiz, eslesen=len(IDD), min_n=MIN_N, uyari=uyari,
    kuponlar=[
        dict(ad="Banko kupon", tur="banko", secimler=[satir(c) for c in banko], **kupon_ozet(banko),
             not_="Oranı buna yakın geçmiş maçlarda en sık tutan, düşük oranlı seçimler; toplam oran 2,00 ve üzeri. Hepsinin birden tutması gerekir."),
        dict(ad="Sürpriz kupon", tur="sürpriz", secimler=[satir(c) for c in surpriz], **kupon_ozet(surpriz),
             not_="Gerçekçi ihtimaline göre oranı en cömert görünen yüksek oranlı seçimler; toplam oran 200 ve üzeri. Tutma ihtimali çok düşük, eğlencelik."),
        dict(ad="Sistem 2-3-4-5-6", tur="sistem", secimler=[satir(c) for c in sistem], **sistem_ozet(sistem),
             not_="Gerçekçi ihtimaline göre oranı cömert görünen, her biri yüksek oranlı 6 seçimden 2'li, 3'lü, 4'lü, 5'li ve 6'lı bütün kombinasyonlar. 2 seçim tutsa bile bir kolon kazanır."),
        dict(ad="İki yarı 1.5 üst · Sistem 2-3", tur="sistem", secimler=[satir(c) for c in yari], **sistem_ozet(yari),
             not_="Oranı buna yakın geçmiş maçlarda hem ilk yarıda hem ikinci yarıda 2 ve üzeri golün en sık görüldüğü 3 maç. 2'li ve 3'lü kombinasyonlar (4 kolon); 2 maç tutsa bir kolon kazanır."),
        dict(ad="İY/MS kuponu", tur="iyms", secimler=[satir(c) for c in iyms], **kupon_ozet(iyms),
             not_="İlk yarı ile maç sonunun farklı bittiği (1/X, X/1, 2/X gibi) sonuçlardan oranı en cömert görünen 3 tanesi. Tutma ihtimali çok düşük. 3 maçın hepsinin tutması gerekir."),
        dict(ad="En başarılı 5'li", tur="banko", secimler=[satir(c) for c in enb], **kupon_ozet(enb),
             not_="Her maçın, oranı buna yakın geçmiş maçlarda en sık tutan bahsi (oran en az 1,30); en sık tutan 5 maç. Hepsinin birden tutması gerekir."),
        dict(ad="En yakın 4 maç: banko", tur="banko", secimler=[satir(c) for c in y4b], **kupon_ozet(y4b),
             not_="Günün ilk başlayan 4 maçında, yakın oranlı geçmiş maçlarda en sık tutan bahis (oran en az 1,20)."),
        dict(ad="En yakın 4 maç: sürpriz", tur="sürpriz", secimler=[satir(c) for c in y4s], **kupon_ozet(y4s),
             not_="Günün ilk başlayan 4 maçında, gerçekçi ihtimaline göre oranı en cömert görünen yüksek oranlı bahis (oran en az 3,00)."),
    ])
json.dump(sonuc_json, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(dict(incelenen=incelenen, uygun=incelenen - yetersiz, aday=len(adaylar), uyari=uyari), ensure_ascii=False))
for k in sonuc_json["kuponlar"]:
    print("\n==", k["ad"], {a: k[a] for a in ("toplam_oran", "tutma_olasiligi", "kolon") if a in k})
    for s in k["secimler"]:
        print(f"  {s['saat']} {s['mac']} [{s['lig']}] -> {s['secim']} oran={s['oran']} gecmis={s['hits']}/{s['n']}={s['gecmis']} yakın={s['ortalama']} tahmin={s['olasilik']}")
