# Draf 2.10 Metode MTI yang Digunakan: System Usability Scale (SUS)

Status: DRAF, menunggu persetujuan Badjradaka atas pemilihan SUS.
Dibuat: 13 November 2026, dari pemetaan rantai metode yang diminta pengguna
(Metode → Tahapan Penerapan → Data/Instrumen → Hasil → Interpretasi → Rekomendasi)
dan jawaban pembelaan yang sudah disiapkan di chat BI.
Aturan penulisan yang dipakai: bahasa Indonesia formal, istilah teknis dalam
bahasa Inggris, `perusahaan` untuk perusahaan klien KarirKu, tanpa kalimat
rencana atau catatan kerja.

## 2.10.1 Metode yang dipilih

Metode yang digunakan adalah System Usability Scale (SUS) dari Brooke (1996).
SUS adalah kuesioner standar berisi 10 butir pernyataan untuk mengukur persepsi
kemudahan penggunaan suatu sistem dari sudut pandang penggunanya. Hasilnya
satu skor 0 sampai 100 dengan skala interpretasi baku.

Pemilihan SUS didasarkan pada masalah yang sudah didokumentasikan dalam
dokumen UTS. Pemanfaatan data warehouse bergantung pada adopsi pengguna, dan
Divisi Bisnis serta Marketing terbiasa bekerja dengan rekap manual sehingga
peralihan ke dashboard membutuhkan penyesuaian. Risiko terbesar proyek ini
bukan pada sisi teknis warehouse, melainkan pada apakah dashboard benar-benar
dapat dan mau dipakai oleh penggunanya. SUS mengukur persis risiko tersebut,
karena penilainya adalah pengguna dashboard itu sendiri.

Dashboard adalah salah satu komponen utama penilaian UAS. SUS menilai
komponen tersebut secara langsung, sehingga hasilnya terhubung ke perbaikan
dashboard dan ke keputusan yang diambil dari dashboard.

Heuristic Evaluation tidak dipilih karena evaluatornya adalah pembuat dashboard
itu sendiri, sehingga hasilnya rawan bias. Technology Acceptance Model (TAM)
tidak dipilih karena TAM mengukur niat menerima teknologi dan membutuhkan
analisis konstruk dengan responden yang lebih banyak, sementara pertanyaan
penelitian ini lebih sempit, yaitu apakah dashboard ini mudah digunakan.

## 2.10.2 Tahapan penerapan

Penerapan SUS pada proyek ini mengikuti enam tahap berikut.

1. Adaptasi 10 butir SUS ke konteks dashboard KarirKu.
2. Penetapan minimal 20 responden sebagai pengguna uji dashboard.
3. Responden mencoba dashboard terlebih dahulu dengan menjalankan tugas
   berikut: membaca KPI, memakai filter, dan melakukan drill-down.
4. Responden mengisi kuesioner SUS.
5. Perhitungan skor per responden, lalu skor rata-rata.
6. Interpretasi skor dan perumusan rekomendasi perbaikan dashboard.

Tahap 1 sampai 3 dan instrumen pada subbab 2.10.3 dirancang di Bab II ini.
Pelaksanaannya ditulis di subbab 3.6, dan hasilnya ditulis di subbab 4.3.

## 2.10.3 Instrumen dan data

Instrumen yang digunakan adalah kuesioner SUS 10 butir dengan skala Likert
1 sampai 5. Butir ganjil menyatakan hal yang positif tentang sistem, dan
butir genap menyatakan hal yang negatif. Responden berjumlah minimal 20
orang dan bersifat bebas, yaitu pengguna uji yang mengoperasikan dashboard.

Data yang dikumpulkan adalah 20 responden dikali 10 jawaban, ditambah catatan
tugas yang dijalankan responden pada tahap 3. Data mentah kuesioner
dilampirkan pada Lampiran 6.

## 2.10.4 Perhitungan skor

Skor dihitung per responden dengan langkah berikut. Untuk butir ganjil, skor
butir sama dengan nilai jawaban dikurangi 1. Untuk butir genap, skor butir
sama dengan 5 dikurangi nilai jawaban. Seluruh skor butir dijumlahkan, lalu
hasilnya dikalikan 2,5 sehingga skor akhir berada pada rentang 0 sampai 100.

Skor rata-rata dari seluruh responden menjadi skor SUS dashboard. Skor per butir
juga dihitung untuk melihat butir mana yang paling lemah.

## 2.10.5 Interpretasi

Skor SUS dibandingkan dengan ambang baku berikut. Skor di bawah 50 berarti
tidak dapat diterima. Skor 50 sampai 68 berarti di bawah rata-rata. Skor 68
adalah rata-rata industri. Skor di atas 80,3 berarti Excellent, dan skor di
atas 90,9 berarti terbaik.

Interpretasi ini dipakai apa adanya dari skala baku SUS, bukan dari penilaian
penulis terhadap karyanya sendiri. Skor yang diperoleh nanti dibandingkan
dengan ambang 68 sebagai rata-rata dan ambang 80,3 sebagai Excellent.

## 2.10.6 Keterkaitan rantai metode dengan subbab lain

Metode ini tidak berhenti pada landasan teori. Rantai lengkapnya tersebar
pada subbab berikut.

| Mata rantai | Subbab |
| --- | --- |
| Metode dan alasan pemilihan | 2.10.1 |
| Tahapan penerapan dan instrumen | 2.10.2 dan 2.10.3 |
| Pelaksanaan | 3.6 |
| Hasil | 4.3 |
| Interpretasi | 4.3 |
| Rekomendasi | 4.5 dan Bab V |

Rekomendasi diturunkan dari butir SUS yang skornya paling rendah. Sebagai
contoh, butir konsistensi yang rendah mengarah pada penyeragaman format antar
dashboard, dan butir kebutuhan belajar yang rendah mengarah pada penambahan
label dan panduan singkat di dashboard. Perbaikan tersebut ditampilkan pada
slide 9 sebagai dashboard sesudah evaluasi.

## Catatan draf

- Subbab ini hanya berisi rancangan. Angka skor hasil pengukuran belum ada
  dan baru ditulis di subbab 4.3 setelah dashboard selesai dan kuesioner
  disebar pada Minggu 3.
- Kuesioner tidak disebar sebelum dashboard dapat dipakai, karena responden
  harus mencoba dashboard terlebih dahulu.
