# Kualiti Udara MRSM Kuala Kubu Bharu

Halaman awam yang memaparkan bacaan Indeks Pencemar Udara (IPU) untuk kawasan
MRSM Kuala Kubu Bharu, bersama ramalan cuaca MET Malaysia dan panduan aktiviti
sekolah semasa jerebu.

Halaman langsung: <https://aizuddin13.github.io/IPU-MRSM-KKB>

## Nota penting tentang sumber bacaan

**Tiada stesen pemantauan APIMS di Kuala Kubu Bharu.** Rangkaian Jabatan Alam
Sekitar hanya mempunyai 68 stesen dan tiada satu pun di daerah Hulu Selangor.

Oleh itu halaman ini menggunakan **Tanjung Malim (CA14A)** sebagai stesen
rujukan utama — kira-kira 21 km ke utara, di cerun barat Banjaran Titiwangsa
yang sama seperti KKB, jadi coraknya paling hampir. Empat stesen lain
dipaparkan sekali supaya pembaca tidak bergantung pada satu angka tunggal:

| Stesen | ID | Jarak dari KKB | Arah |
|---|---|---|---|
| Tanjung Malim, Perak | CA14A | ~21 km | utara (rujukan utama) |
| Batu Muda, WP KL | CA15W | ~39 km | selatan |
| Petaling Jaya, Selangor | CA19B | ~48 km | barat daya |
| Cheras, WP KL | CA16W | ~51 km | selatan |
| Kuala Selangor, Selangor | CA18B | ~52 km | barat, pantai |

Halaman memaparkan julat min–maks merentas kelima-lima stesen. Apabila beza
antara stesen mencapai 40 mata atau lebih, satu amaran dipaparkan bahawa angka
tunggal kurang boleh dipegang.

Angka di halaman ini ialah **anggaran**, bukan bacaan di tapak MRSM.

## Fail

- `index.html` — halaman itu sendiri, tiada kebergantungan luar. Carta dilukis
  sebagai SVG.
- `data/ipu.json` — bacaan IPU sejam bagi stesen rujukan, tetingkap bergolek
  tujuh hari (168 bacaan).
- `data/berdekatan.json` — bacaan semasa kelima-lima stesen, disusun mengikut
  jarak, berserta julat min/maks/purata.
- `data/cuaca.json` — ramalan cuaca tujuh hari bagi pekan Kuala Kubu Bharu.
- `scripts/kemaskini.py` — penulis data. Pustaka standard Python sahaja.

## Kemas kini

Workflow GitHub Actions (`kemaskini.yml`) menulis semula data setiap jam pada
minit ke-25 dan menerbitkan halaman ke GitHub Pages. Dua perlindungan:

- Jika bacaan terbaharu melebihi tiga jam, larian gagal dan tidak menulis data
  basi secara senyap.
- Setiap larian mengambil tetingkap 25 jam supaya jam yang tertinggal diisi
  semula oleh larian kemudian.

Larian juga boleh dicetus secara manual dari tab Actions.

## Panduan aktiviti sekolah

Halaman memaparkan cadangan tindakan berdasarkan bacaan **tertinggi** antara
stesen rujukan dan stesen berdekatan, bukan hanya stesen rujukan:

| IPU | Tindakan |
|---|---|
| 0–100 | Aktiviti luar seperti biasa |
| 101–200 | Hentikan aktiviti luar bilik darjah |
| 201–300 | Ambang penutupan sekolah, tadika dan taska |
| >300 | Berbahaya — kekal dalam bangunan tertutup |

## Sumber

Bacaan IPU dari sistem APIMS, Jabatan Alam Sekitar. Ramalan cuaca dari
MET Malaysia melalui data.gov.my.

## Penafian

Halaman ini bukan terbitan rasmi mana-mana agensi. Untuk keputusan kesihatan
atau keselamatan pelajar, rujuk portal APIMS serta arahan rasmi MARA, KPM dan
Kementerian Kesihatan.
