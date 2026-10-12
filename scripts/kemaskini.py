#!/usr/bin/env python3
"""Kemas kini fail data untuk halaman Kualiti Udara MRSM Kuala Kubu Bharu.

Tiada stesen APIMS di Kuala Kubu Bharu. Stesen rujukan utama ialah
Tanjung Malim (CA14A), kira-kira 21 km ke utara dan berada di cerun
barat Banjaran Titiwangsa yang sama. Empat stesen berdekatan lain
diambil sekali supaya pembaca nampak keadaan seluruh kawasan, bukan
satu bacaan tunggal.

Bacaan IPU diambil dari portal APIMS (Jabatan Alam Sekitar) dan ramalan
cuaca MET Malaysia melalui portal data terbuka kerajaan, kemudian fail
JSON dalam data/ ditulis semula.

Hanya pustaka standard Python digunakan. Dijalankan setiap jam oleh
.github/workflows/kemaskini.yml pada pelari GitHub.
"""

import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

MYT = timezone(timedelta(hours=8))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(AKAR, "data")

# Kuala Kubu Bharu, Hulu Selangor — titik rujukan untuk kiraan jarak.
KKB_LAT, KKB_LON = 3.5586, 101.6606

STESEN_RUJUKAN = "CA14A"     # Tanjung Malim, Perak
JAM_DISIMPAN = 168           # tetingkap bergolek tujuh hari
AMBANG_BASI_JAM = 3          # bacaan lebih lama daripada ini dikira basi
MAKS_TAMPAL = 8              # tetingkap lampau paling banyak setiap larian

# Stesen yang dipantau: rujukan utama dahulu, kemudian stesen berdekatan
# mengikut arah yang berbeza supaya corak jerebu kawasan kelihatan.
STESEN = {
    "CA14A": {"nama": "Tanjung Malim", "negeri": "Perak", "stateid": 8},
    "CA15W": {"nama": "Batu Muda", "negeri": "WP Kuala Lumpur", "stateid": 14},
    "CA19B": {"nama": "Petaling Jaya", "negeri": "Selangor", "stateid": 10},
    "CA18B": {"nama": "Kuala Selangor", "negeri": "Selangor", "stateid": 10},
    "CA16W": {"nama": "Cheras", "negeri": "WP Kuala Lumpur", "stateid": 14},
}
NEGERI_DIAMBIL = sorted({s["stateid"] for s in STESEN.values()})

APIMS = "https://eqms.doe.gov.my/api3/publicportalapims/apitablehourly"
BANDAR_MET = "Kuala Kubu Bharu"
CUACA = ("https://api.data.gov.my/weather/forecast?contains="
         + urllib.parse.quote(BANDAR_MET)
         + "@location__location_name&limit=20")

HARI_MELAYU = ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"]

SIMBOL_PENCEMAR = {
    "**": "PM2.5",
    "*": "PM10",
    "a": "SO2",
    "b": "NO2",
    "c": "O3",
    "d": "CO",
    "&": "2 pencemar atau lebih",
}


def kategori(ipu):
    if ipu <= 50:
        return "Baik"
    if ipu <= 100:
        return "Sederhana"
    if ipu <= 200:
        return "Tidak Sihat"
    if ipu <= 300:
        return "Sangat Tidak Sihat"
    return "Berbahaya"


def jarak_km(lat, lon):
    """Jarak bulatan besar dari Kuala Kubu Bharu, dibundarkan ke km."""
    r = 6371.0
    dlat = math.radians(lat - KKB_LAT)
    dlon = math.radians(lon - KKB_LON)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(KKB_LAT)) * math.cos(math.radians(lat))
         * math.sin(dlon / 2) ** 2)
    return round(2 * r * math.asin(math.sqrt(a)))


def ayat_biasa(teks):
    teks = (teks or "").strip()
    return teks[:1].upper() + teks[1:].lower() if teks else teks


def ambil_json(url, cubaan=3):
    """Ambil JSON dengan beberapa cubaan. Mengembalikan None jika gagal."""
    for i in range(cubaan):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "ipu-mrsm-kkb/1.0 (+github actions)",
                              "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as res:
                return json.loads(res.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, TimeoutError, OSError) as e:
            print(f"  cubaan {i + 1}/{cubaan} gagal: {e}", file=sys.stderr)
            if i + 1 < cubaan:
                time.sleep(5 * (i + 1))
    return None


def muat(nama, lalai):
    laluan = os.path.join(DATA, nama)
    try:
        with open(laluan, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return lalai


def simpan(nama, isi):
    laluan = os.path.join(DATA, nama)
    os.makedirs(DATA, exist_ok=True)
    with open(laluan, "w", encoding="utf-8") as f:
        json.dump(isi, f, ensure_ascii=False, indent=1)
        f.write("\n")


def jam_penuh(d):
    return d.replace(minute=0, second=0, microsecond=0)


def ambil_tetingkap(stateid, sehingga):
    """Satu tetingkap 25 jam bagi satu negeri, berakhir pada `sehingga`.

    `_r` menghalang jawapan lama daripada cache dihidangkan semula.
    """
    url = (f"{APIMS}?stateid={stateid}&datetime={sehingga}"
           f"&stn=all&_r={int(time.time())}")
    print(f"APIMS negeri {stateid} hingga {sehingga}")
    jawapan = ambil_json(url)
    if not jawapan:
        print(f"  negeri {stateid} gagal dibaca.", file=sys.stderr)
        return []
    baris = (jawapan.get("api_table_hourly")
             if isinstance(jawapan, dict) else jawapan)
    if not baris:
        return []
    bersih = []
    for r in baris:
        sid = r.get("STATION_ID")
        if sid not in STESEN:
            continue  # stesen lain dalam negeri sama — tidak berkaitan
        try:
            ipu = int(r["API"])
        except (KeyError, TypeError, ValueError):
            continue  # bacaan tiada atau rosak — langkau
        masa = str(r.get("DATETIME", ""))[:19]
        if len(masa) != 19:
            continue
        try:
            lat = float(r.get("LATITUDE"))
            lon = float(r.get("LONGITUDE"))
        except (TypeError, ValueError):
            lat = lon = None
        bersih.append({
            "id": sid,
            "nama": STESEN[sid]["nama"],
            "negeri": STESEN[sid]["negeri"],
            "masa": masa,
            "ipu": ipu,
            "jarak": jarak_km(lat, lon) if lat is not None else None,
            "pencemar": SIMBOL_PENCEMAR.get(
                str(r.get("PARAM_SYMBOL", "")).strip(), "PM2.5"),
        })
    return bersih


def ambil_apims(sekarang, hari_lalu=0):
    """Bacaan sejam bagi setiap negeri yang ada stesen dipantau.

    APIMS hanya memulangkan tingkap 25 jam setiap panggilan, berakhir pada
    `datetime` yang diminta. Dengan hari_lalu > 0 panggilan diulang setiap
    24 jam ke belakang, jadi sejarah lama boleh diisi semula sekali gus
    (lihat --isi-semula). Untuk lompang biasa, tampal_lompang menguruskan
    perkara itu sendiri dan jauh lebih jimat: ia meminta negeri stesen
    rujukan sahaja, bukan kesemua negeri.
    """
    jam_ini = jam_penuh(sekarang)
    bersih = []
    for d in range(hari_lalu + 1):
        sehingga = (jam_ini + timedelta(hours=1) - timedelta(days=d)
                    ).strftime("%Y-%m-%dT%H:00:00")
        for stateid in NEGERI_DIAMBIL:
            bersih.extend(ambil_tetingkap(stateid, sehingga))
    return bersih or None


def tampal_lompang(simpanan, dicuba, sekarang):
    """Tarik tetingkap lampau sehingga tempoh simpanan penuh.

    Satu panggilan APIMS memberi 25 jam sahaja, jadi larian yang terlepas
    lebih lama daripada itu meninggalkan lompang kekal dalam graf. Setiap
    tetingkap di sini berakhir 24 jam selepas jam terawal yang hilang,
    jadi ia merangkumi lompang itu dan bertindih sedikit dengan yang
    sudah ada. Hanya negeri stesen rujukan diminta.

    `dicuba` menyimpan hujung tetingkap yang pernah diminta. Tanpanya,
    jam yang memang tiada pada APIMS — stesen tutup, bacaan digugurkan —
    akan diminta semula setiap jam, selama-lamanya.
    """
    stateid = STESEN[STESEN_RUJUKAN]["stateid"]
    hujung = jam_penuh(sekarang)
    mula = hujung - timedelta(hours=JAM_DISIMPAN - 1)

    def hilang():
        t, keluar = mula, []
        while t <= hujung:
            if t.strftime("%Y-%m-%dT%H:00:00") not in simpanan:
                keluar.append(t)
            t += timedelta(hours=1)
        return keluar

    ditambah = 0
    for _ in range(MAKS_TAMPAL):
        tiada = hilang()
        if not tiada:
            break
        sasaran = min(tiada[0] + timedelta(hours=24), hujung)
        kunci = sasaran.strftime("%Y-%m-%dT%H:00:00")
        if kunci in dicuba:
            # Sudah diminta sebelum ini dan jam itu tetap tiada: anggap
            # ia memang tiada pada APIMS, dan cari lompang seterusnya.
            seterusnya = None
            for t in tiada:
                k = min(t + timedelta(hours=24), hujung).strftime("%Y-%m-%dT%H:00:00")
                if k not in dicuba:
                    seterusnya = k
                    break
            if seterusnya is None:
                break
            kunci = seterusnya
        dicuba.add(kunci)
        baris = ambil_tetingkap(stateid, kunci)
        if not baris:
            print(f"  tetingkap {kunci}: tiada jawapan", file=sys.stderr)
            continue
        baru = 0
        for b in baris:
            if b["id"] != STESEN_RUJUKAN or b["masa"] in simpanan:
                continue
            simpanan[b["masa"]] = {
                "masa": b["masa"], "ipu": b["ipu"],
                "kategori": kategori(b["ipu"]), "pencemar": b["pencemar"],
            }
            baru += 1
        ditambah += baru
        print(f"  tetingkap {kunci}: +{baru} jam")
        if baru:
            time.sleep(1)  # jangan pukul APIMS bertalu-talu
    return ditambah


def tulis_ipu(baris, sekarang):
    """Siri sejam bagi stesen rujukan, digabung dengan apa yang sudah ada."""
    rujukan = sorted([b for b in baris if b["id"] == STESEN_RUJUKAN],
                     key=lambda b: b["masa"])
    if not rujukan:
        print(f"Tiada baris {STESEN_RUJUKAN} dalam jawapan APIMS.", file=sys.stderr)
        return None

    terbaharu = rujukan[-1]
    umur = sekarang - datetime.strptime(
        terbaharu["masa"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=MYT)
    if umur > timedelta(hours=AMBANG_BASI_JAM):
        print(f"DATA BASI: bacaan terbaharu {terbaharu['masa']} "
              f"({umur.total_seconds() / 3600:.1f} jam lalu).", file=sys.stderr)
        return None

    sedia = muat("ipu.json", {"bacaan": []})
    simpanan = {b["masa"]: b for b in sedia.get("bacaan", [])}
    baharu = 0
    for b in rujukan:
        if b["masa"] not in simpanan:
            simpanan[b["masa"]] = {
                "masa": b["masa"], "ipu": b["ipu"],
                "kategori": kategori(b["ipu"]), "pencemar": b["pencemar"],
            }
            baharu += 1

    dicuba = set(sedia.get("tetingkap_dicuba", []))
    ditampal = tampal_lompang(simpanan, dicuba, sekarang)

    bacaan = [simpanan[m] for m in sorted(simpanan)][-JAM_DISIMPAN:]
    # Buang catatan tetingkap yang sudah jatuh di luar tempoh simpanan.
    if bacaan:
        had = bacaan[0]["masa"]
        dicuba = {k for k in dicuba if k >= had}
    simpan("ipu.json", {
        "lokasi": "MRSM Kuala Kubu Bharu",
        "stesen": STESEN[STESEN_RUJUKAN]["nama"],
        "id_stesen": STESEN_RUJUKAN,
        "negeri": STESEN[STESEN_RUJUKAN]["negeri"],
        "jarak_km": terbaharu["jarak"],
        "nota": ("Tiada stesen APIMS di Kuala Kubu Bharu. Bacaan ini dari "
                 "stesen rujukan terdekat."),
        "dikemaskini": terbaharu["masa"] + "+08:00",
        "sumber": "APIMS, Jabatan Alam Sekitar",
        "tetingkap_dicuba": sorted(dicuba),
        "bacaan": bacaan,
    })
    print(f"ipu.json: {baharu} bacaan baharu, {ditampal} jam ditampal, "
          f"{len(bacaan)} jam disimpan, terkini {terbaharu['masa']} = {terbaharu['ipu']}")
    return terbaharu


def tulis_berdekatan(baris):
    """Bacaan terkini semua stesen dipantau, disusun mengikut jarak."""
    terkini = {}
    for b in baris:
        ada = terkini.get(b["id"])
        if ada is None or b["masa"] > ada["masa"]:
            terkini[b["id"]] = b
    if not terkini:
        return
    stesen = sorted(terkini.values(),
                    key=lambda b: (b["jarak"] if b["jarak"] is not None else 9999))
    nilai = [b["ipu"] for b in stesen]
    simpan("berdekatan.json", {
        "dikemaskini": max(b["masa"] for b in stesen) + "+08:00",
        "sumber": "APIMS, Jabatan Alam Sekitar",
        "rujukan": STESEN_RUJUKAN,
        "julat": {"min": min(nilai), "maks": max(nilai),
                  "purata": round(sum(nilai) / len(nilai))},
        "stesen": [{
            "nama": b["nama"], "id": b["id"], "negeri": b["negeri"],
            "jarak": b["jarak"], "ipu": b["ipu"],
            "kategori": kategori(b["ipu"]), "pencemar": b["pencemar"],
            "masa": b["masa"],
        } for b in stesen],
    })
    print(f"berdekatan.json: {len(stesen)} stesen, "
          f"julat {min(nilai)}–{max(nilai)}")


def tulis_cuaca(sekarang):
    print(f"Cuaca: {CUACA}")
    rekod = ambil_json(CUACA)
    if not rekod:
        print("  gagal — fail cuaca dibiarkan seperti sedia ada.", file=sys.stderr)
        return
    hari_ini = sekarang.strftime("%Y-%m-%d")
    ramalan = []
    for r in rekod:
        tarikh = str(r.get("date", ""))[:10]
        if len(tarikh) != 10 or tarikh < hari_ini:
            continue
        try:
            d = datetime.strptime(tarikh, "%Y-%m-%d")
        except ValueError:
            continue
        ramalan.append({
            "tarikh": tarikh,
            "hari": HARI_MELAYU[d.weekday()],
            "ringkasan": ayat_biasa(r.get("summary_forecast") or r.get("summary")),
            "ringkasan_bila": ayat_biasa(r.get("summary_when")),
            "pagi": ayat_biasa(r.get("morning_forecast")),
            "petang": ayat_biasa(r.get("afternoon_forecast")),
            "malam": ayat_biasa(r.get("night_forecast")),
            "suhu_min": int(r.get("min_temp", 0)),
            "suhu_maks": int(r.get("max_temp", 0)),
        })
    if not ramalan:
        print("  tiada rekod Kuala Kubu Bharu — fail cuaca dibiarkan.", file=sys.stderr)
        return
    ramalan.sort(key=lambda x: x["tarikh"])
    simpan("cuaca.json", {
        "lokasi": "Kuala Kubu Bharu",
        "dikemaskini": sekarang.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "sumber": "MET Malaysia melalui data.gov.my",
        "ramalan": ramalan,
    })
    print(f"cuaca.json: {len(ramalan)} hari")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    hari_lalu = 0
    if "--isi-semula" in argv:
        i = argv.index("--isi-semula")
        try:
            hari_lalu = max(0, min(7, int(argv[i + 1])))
        except (IndexError, ValueError):
            print("Guna: --isi-semula N  (N hari, maksimum 7)", file=sys.stderr)
            return 2

    sekarang = datetime.now(MYT)
    print(f"Masa Malaysia: {sekarang:%Y-%m-%d %H:%M:%S}")
    if hari_lalu:
        print(f"Mod isi semula: {hari_lalu} hari ke belakang.")

    baris = ambil_apims(sekarang, hari_lalu)
    if baris is None:
        print("APIMS tidak dapat dibaca. Tiada fail ditulis.", file=sys.stderr)
        return 1

    terbaharu = tulis_ipu(baris, sekarang)
    if terbaharu is None:
        return 1
    tulis_berdekatan(baris)
    tulis_cuaca(sekarang)

    if terbaharu["ipu"] > 200:
        print(f"::warning::AMARAN: IPU rujukan {terbaharu['ipu']} — "
              f"ambang penutupan sekolah dilepasi")
    elif terbaharu["ipu"] > 100:
        print(f"::warning::AMARAN: IPU rujukan {terbaharu['ipu']} — "
              f"aktiviti luar bilik darjah patut dihentikan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
