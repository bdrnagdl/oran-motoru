#!/usr/bin/env bash
# Her gün: veriyi güncelle, yarının kuponlarını hazırla.
set -euo pipefail
export TZ=Europe/Istanbul
YARIN=$(date -d tomorrow +%d/%m/%Y)
SIMDI=$(date +"%Y-%m-%d %H:%M")
echo "Yarın: $YARIN  Şimdi: $SIMDI"
python3 scripts/veri_guncelle.py
python3 scripts/kupon.py veri/kapanis_maclar.csv veri/fikstur.txt "$YARIN" veri/uygun.json "$SIMDI"
python3 scripts/bulten_cek.py veri/uygun.json veri/bulten.json
python3 scripts/kupon.py veri/kapanis_maclar.csv veri/fikstur.txt "$YARIN" site/kuponlar.json "$SIMDI" veri/bulten.json
