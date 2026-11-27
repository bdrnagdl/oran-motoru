"""Geçmiş maç verisini indirir ve iki dosya üretir:
  veri/kapanis_maclar.csv  (kupon motoru için)
  site/maclar.json         (sitedeki arama için)
Ayrıca yaklaşan maç listesini veri/fikstur.txt olarak kaydeder.
Kullanım: python3 scripts/veri_guncelle.py
"""
import io, os, sys, json, time, datetime as dt, urllib.request
import pandas as pd

KOK = "https://www.football-data.co.uk"
ANA = ["E0", "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D1", "D2", "I1", "I2", "SP1", "SP2",
       "F1", "F2", "N1", "B1", "P1", "T1", "G1"]
EKSTRA = ["ARG", "AUT", "BRA", "CHN", "DNK", "FIN", "IRL", "JPN", "MEX", "NOR", "POL", "ROU", "RUS", "SWE", "SWZ", "USA"]
ILK_SEZON = 2019   # kapanış oranları 2019/20'den beri var
UA = {"User-Agent": "Mozilla/5.0 (oran-motoru veri guncelleme)"}


def indir(yol, deneme=4):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(KOK + yol, headers=UA), timeout=60) as r:
                b = r.read()
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    return b.decode(enc)
                except UnicodeDecodeError:
                    pass
        except Exception as e:  # noqa: BLE001
            print(f"  {yol}: {e} (deneme {i + 1})", flush=True)
            time.sleep(5 * (i + 1))
    return None


def oku(txt):
    if not txt or "," not in txt.split("\n", 1)[0]:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(txt), dtype=str, on_bad_lines="skip")


def sezonlar():
    bugun = dt.date.today()
    son = bugun.year if bugun.month >= 7 else bugun.year - 1
    return [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(ILK_SEZON, son + 1)]


def tarih(s):
    s = s.astype(str).str.strip()
    return pd.to_datetime(s, dayfirst=True, errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")


def main():
    os.makedirs("veri", exist_ok=True)
    os.makedirs("site", exist_ok=True)
    parcalar = []
    for s in sezonlar():
        for lg in ANA:
            d = oku(indir(f"/mmz4281/{s}/{lg}.csv"))
            if d.empty or "HomeTeam" not in d:
                continue
            p = pd.DataFrame(dict(src="M", league=lg, season=s, date=tarih(d["Date"]), home=d["HomeTeam"], away=d["AwayTeam"],
                                  fthg=d.get("FTHG"), ftag=d.get("FTAG"), hthg=d.get("HTHG"), htag=d.get("HTAG"),
                                  b365ch=d.get("B365CH"), b365cd=d.get("B365CD"), b365ca=d.get("B365CA")))
            parcalar.append(p)
        print("sezon", s, "tamam", flush=True)
    for lg in EKSTRA:
        d = oku(indir(f"/new/{lg}.csv"))
        if d.empty or "Home" not in d:
            continue
        yil = pd.to_numeric(d["Season"].astype(str).str[:4], errors="coerce")
        d = d[yil >= ILK_SEZON]
        p = pd.DataFrame(dict(src="X", league=lg + "|" + d["League"].astype(str), season=d["Season"], date=tarih(d["Date"]),
                              home=d["Home"], away=d["Away"], fthg=d.get("HG"), ftag=d.get("AG"), hthg=None, htag=None,
                              b365ch=d.get("B365CH"), b365cd=d.get("B365CD"), b365ca=d.get("B365CA")))
        parcalar.append(p)
    df = pd.concat(parcalar, ignore_index=True)
    for c in ["fthg", "ftag", "hthg", "htag", "b365ch", "b365cd", "b365ca"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["home", "away"]:
        df[c] = df[c].astype(str).str.replace(r'[",]', " ", regex=True).str.strip()
    df = df.dropna(subset=["date", "fthg", "ftag", "b365ch", "b365cd", "b365ca"])
    df = df[(df.b365ch > 1) & (df.b365cd > 1) & (df.b365ca > 1)]
    df = df.drop_duplicates(subset=["league", "date", "home", "away"]).sort_values(["date", "league"])
    if len(df) < 40000:
        sys.exit(f"HATA: beklenenden az maç ({len(df)}); veri indirme sorunlu, eski veri korunuyor.")
    df.to_csv("veri/kapanis_maclar.csv", index=False)

    # sitedeki arama için sade liste
    def n(x):
        return None if pd.isna(x) else int(x)
    d2 = df.sort_values("date", ascending=False)
    satir = [json.dumps([r.date, r.league if r.src == "M" else r.league.split("|")[0], r.home, r.away, n(r.fthg), n(r.ftag),
                         n(r.hthg), n(r.htag), round(r.b365ch, 2), round(r.b365cd, 2), round(r.b365ca, 2)],
                        ensure_ascii=False, separators=(",", ":")) for r in d2.itertuples()]
    with open("site/maclar.json", "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(satir) + "\n]\n")

    # yaklaşan maçlar
    fx = []
    for yol in ["/fixtures.csv", "/new_league_fixtures.csv"]:
        t = indir(yol)
        if not t:
            sys.exit(f"HATA: {yol} indirilemedi")
        fx.append("### " + yol + "\n" + t)
    with open("veri/fikstur.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(fx))
    print(f"maç sayısı: {len(df)} | büyük lig: {(df.src == 'M').sum()} | son tarih: {df.date.max()}")


if __name__ == "__main__":
    main()
