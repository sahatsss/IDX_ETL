# Query analitik

Satu file per pertanyaan di README utama, misalnya `01_return_harian.sql`.
Tulis sendiri. Di atas setiap file, beri komentar: pertanyaan apa yang dijawab dan cara membaca hasilnya.

Petunjuk konsep (bukan jawaban):
- Return harian butuh harga tutup hari sebelumnya → cari tahu `LAG()` dengan `PARTITION BY` dan `ORDER BY`.
- Moving average → window frame `ROWS BETWEEN n PRECEDING AND CURRENT ROW`.
- Hati-hati: hari libur bursa bukan "baris hilang"; 20 baris ≠ 20 hari kalender.
