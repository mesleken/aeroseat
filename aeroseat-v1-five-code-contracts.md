# AeroSeat Certification OS — V1.0 Beş Code Contract

**Amaç:** Implementasyona geçmeden dondurulacak beş sözleşme. Her biri "ne, hangi sırada, hangi garanti ile" sorusuna cevap verir — *nasıl kodlanacağı* bir sonraki adım.

**Önemli okuma notu:** Bu belgede ⚠️ **[GOLDEN-DATA BAĞIMLI]** etiketli her madde, gerçek bir fiziksel sled testi verisi (sensör + video + kalibrasyon metadata) gelene kadar **taslak/v0.1** statüsündedir ve kesin değildir. Bu etiketler kaldırılmadan önce gerçek veriyle doğrulanmalı. Bu belge o bağımlılığı gizlemez, tam tersine açıkça işaretler.

---

## Contract 1 — Scientific Processing Contract

**Görev:** Ham sensör sinyaline (fiziksel veya simülasyon fark etmeksizin) ne yapılacağını, hangi sırada yapılacağını tanımlamak. Kodun içine gömülmez — veri olarak (ProcessingDefinition) saklanır.

### 1.1 Zorunlu işlem sırası

```
RAW SIGNAL
   ↓
1. Data Integrity Check      (örnekleme aralığı tutarlı mı, kayıp örnek var mı)
   ↓
2. Unit Normalization         (g / m/s² / N / lb hepsi SI'ya çevrilir)
   ↓
3. Channel Validation          (kanal tipine göre beklenen aralık kontrolü)
   ↓
4. Filter                       (⚠️ [GOLDEN-DATA BAĞIMLI] — bkz. 1.3)
   ↓
5. Time-Zero Detection            (⚠️ [GOLDEN-DATA BAĞIMLI] — bkz. 1.4)
   ↓
6. Window Selection                 (analiz penceresi: t1, t2)
   ↓
7. Common Analysis Grid              (bkz. 1.5)
   ↓
8. Resampling / Interpolation          (ortak grid'e oturtma)
```

Bu sıra sabittir. Adım eklenebilir ama sıra değiştirilemez; her ProcessingDefinition revizyonu bu sırayı referans alır.

### 1.2 ProcessingDefinition veri şeması

```json
{
  "id": "uuid",
  "revision_label": "PD-Rev1",
  "steps": [
    {"step": "integrity_check", "params": {"max_gap_ms": 1}},
    {"step": "unit_normalization", "params": {"target_units": "SI"}},
    {"step": "channel_validation", "params": {"expected_range": {"min": -500, "max": 500}}},
    {"step": "filter", "params": {"standard": "SAE_J211", "channel_frequency_class": null}},
    {"step": "time_zero", "params": {"method": "threshold_crossing", "threshold_g": 0.5}},
    {"step": "window", "params": {"start_offset_ms": -10, "end_offset_ms": 100}},
    {"step": "resample", "params": {"target_rate_hz": 10000, "interpolation": "linear"}}
  ],
  "sha256": "…"
}
```

`channel_frequency_class` gibi alanlar `null` bırakılabilir — gerçek değer, **SignalDefinition** tablosundan kanal tipine göre çözülür (hard-code yok, bkz. 1.3).

### 1.3 Filtre — kanala bağlı, koda gömülü değil ⚠️ [GOLDEN-DATA BAĞIMLI]

```json
// SignalDefinition tablosu
{"signal": "head_acceleration", "filter_standard": "SAE_J211", "channel_frequency_class": 1000},
{"signal": "femur_load",         "filter_standard": "SAE_J211", "channel_frequency_class": 600},
{"signal": "neck_moment",         "filter_standard": "SAE_J211", "channel_frequency_class": 600}
```

Bu CFC değerleri literatürden alınmış makul başlangıç noktalarıdır. **Kesinleştirilmesi**, gerçek dummy enstrümantasyon spesifikasyonu (Humanetics HIII-50M teknik dokümanı) ve ilk golden dataset ile çapraz doğrulama gerektirir. Bu tablo, gerçek veri gelene kadar "en iyi bilinen varsayım" statüsündedir.

### 1.4 Time-zero tespiti ⚠️ [GOLDEN-DATA BAĞIMLI]

Yöntem: filtrelenmiş sled/taban ivme sinyalinin belirli bir eşiği (`threshold_g`) geçtiği ilk an, t=0 kabul edilir.

**Kesinleştirilmemiş parametreler:**
- Eşik değeri (`threshold_g`) — literatür başlangıç değeri önerilebilir ama gerçek sled sinyali gürültü seviyesiyle kalibre edilmeli.
- Fiziksel test ile simülasyon arasında ayrı ayrı mı, yoksa ortak bir referans mı kullanılacağı — bu, ilk golden dataset üzerinde denenerek karara bağlanmalı.

### 1.5 Common Analysis Grid

```json
{
  "analysis_start_s": -0.010,
  "analysis_end_s": 0.100,
  "sample_rate_hz": 10000,
  "interpolation_method": "linear"
}
```

Bu grid, hem fiziksel test hem simülasyon sinyali için **aynı** uygulanır — "yüksek örnekleme hızı olan kazanır" gibi keyfi bir kural yok; grid parametreleri açıkça tanımlanır ve versiyonlanır.

### 1.6 Garanti (contract'ın verdiği söz)

> **Aynı ham girdi + aynı ProcessingDefinition revizyonu ⇒ bit-bit aynı ara çıktı.**

Bu garanti test edilebilir olmalı: aynı girdiyi iki kez işleyip sonuçları karşılaştıran bir determinism testi, CI'ya eklenir.

---

## Contract 2 — Correlation Contract

**Görev:** İşlenmiş (processed) fiziksel ve simülasyon sinyallerini karşılaştırıp bir **vektör** üretmek — tek skor değil.

### 2.1 Girdi

```json
{
  "correlation_run_id": "uuid",
  "processing_definition_id": "uuid",
  "analysis_grid": { "...": "bkz. 1.5" },
  "channels": ["head_acceleration", "femur_load_left", "femur_load_right", "neck_moment"]
}
```

### 2.2 Her kanal için hesaplanan metrik seti

```json
{
  "channel": "head_acceleration",
  "peak_error": 0.037,
  "time_to_peak_error_ms": 2.1,
  "rms_error": 0.041,
  "sprague_geers_magnitude": 0.028,
  "sprague_geers_phase": 0.015,
  "impulse_error": 0.019
}
```

Sprague-Geers formülleri (magnitude M, phase P bileşenleri) literatürde tanımlı ama **implementasyon ayrıntıları** (işaret konvansiyonu, sıfıra yakın payda davranışı, negatif sinyal ele alışı) golden dataset üzerinde doğrulanmadan production'a alınmaz — bu fonksiyonlar için ⚠️ **[GOLDEN-DATA BAĞIMLI]** etiketi geçerlidir.

### 2.3 Tolerans/eşik — metrik bazlı, tek sayı değil ⚠️ [GOLDEN-DATA BAĞIMLI]

```json
{
  "HIC15": {"relative_tolerance": 1e-4},
  "NIJ": {"absolute_tolerance": 1e-5},
  "femur_load": {"relative_tolerance": 1e-4},
  "sprague_geers_phase": {"absolute_tolerance_ms": 2.0},
  "sprague_geers_magnitude": {"absolute_tolerance": 0.05}
}
```

Bu sayılar **başlangıç varsayımıdır**; gerçek toleransların neyi ifade ettiği (numerik gürültü mü, mühendislik açısından anlamlı sapma mı) ancak birden fazla gerçek test-simülasyon çifti karşılaştırıldıktan sonra kalibre edilebilir.

### 2.4 Çıktı — asla tek skora indirgenmez

```json
{
  "correlation_run_id": "uuid",
  "vectors": [ /* 2.2'deki gibi, kanal başına bir obje */ ],
  "engineering_note_required": true
}
```

Sistem burada bir "PASS/FAIL" üretmez. Bir sonraki adım olan `CredibilityAssessment` her zaman bir mühendisin (`reviewed_by` alanı NULL olamaz) bu vektörü yorumlamasını gerektirir.

---

## Contract 3 — Solver Adapter Contract

**Görev:** Çekirdek sistemin hiçbir zaman LS-DYNA'ya (veya herhangi bir çözücüye) özel bilgi içermemesini garanti etmek.

### 3.1 Arayüz (önceki spec'teki `BaseSolverAdapter` ile birebir uyumlu, burada sözleşme netleştiriliyor)

```python
class BaseSolverAdapter(ABC):
    @abstractmethod
    def prepare_input(self, config: SimulationConfiguration) -> PreparedInput: ...

    @abstractmethod
    def submit_job(self, prepared: PreparedInput, compute: ComputeConfiguration) -> ExternalJobRef: ...

    @abstractmethod
    def poll_status(self, ref: ExternalJobRef) -> SolverStatus: ...

    @abstractmethod
    def parse_results(self, ref: ExternalJobRef) -> RawSimulationOutput: ...
```

### 3.2 Malzeme kimliği ile solver temsili ayrımı (kritik düzeltme)

```
MaterialDataset               (fiziksel kimlik — akma dayanımı, elastisite modülü, saf mühendislik verisi)
        │
        ▼
SolverMaterialRepresentation  (bu malzemenin belirli bir çözücüde nasıl ifade edildiği — örn. LS-DYNA *MAT_024)
```

Bu ayrım olmadan, ikinci bir solver adapter (Radioss) eklendiğinde `MaterialDataset` tablosu yeniden yazılmak zorunda kalır — bu, immutability ilkesini bozar. Ayrım yapıldığında, aynı `MaterialDataset`'e birden fazla `SolverMaterialRepresentation` bağlanabilir.

### 3.3 Çekirdeğin bilmediği, yalnızca adapter'ın bildiği şeyler

```
*MAT_024, *MAT_054/055
*BOUNDARY_PRESCRIBED_MOTION
*CONTACT_AUTOMATIC_...
d3plot / binout dosya formatları
qd-cae-python / lasso-python okuma detayları
```

Bu liste `LSDynaAdapter` sınıfının dışına asla sızmaz. Bir `RadiossAdapter` yazıldığında bu liste tamamen farklı olacak, ama çekirdek kod (`SimulationConfiguration`, `SolverJob`, vb.) tek satır değişmeyecek.

### 3.4 Garanti

> **Çekirdek sistem kodunda hiçbir yerde `"LSDYNA"` string'i dışında solver'a özgü bir kelime geçmez** (dosya uzantısı, keyword adı, format adı dahil).

Bu, kod review'da otomatik olarak grep ile denetlenebilir bir kuraldır.

---

## Contract 4 — Evidence & Immutability Contract

**Görev:** Herhangi bir sonucun "hangi girdiyle, hangi yazılım versiyonuyla, hangi işlem tanımıyla üretildiği" sorusuna her zaman kesin cevap verebilmek.

### 4.1 Üç hash kavramının kesin tanımı

```
Artifact Hash
    = SHA256(dosyanın kendisi)
    Örnek: CAD dosyası, d3plot, ham CSV

Configuration Hash
    = SHA256(
        ModelRevision.sha256
        + MeshDefinition.sha256
        + MaterialDataset.sha256
        + SolverMaterialRepresentation.sha256
        + ContactDefinition.sha256
        + BoundaryConditionSet.sha256
        + DummyConfiguration.sha256
        + PulseDefinition.sha256
        + AnalysisSettings.sha256
      )
    Simülasyonu tanımlayan TÜM parametrelerin özeti

Execution Fingerprint
    = SHA256(
        ConfigurationHash
        + SolverName + SolverVersion + SolverBuild
        + AeroSeatEngineVersion
        + ProcessingDefinition.sha256   (Contract 1'den)
      )
    Bu SONUCU üreten TAM yazılım+veri kombinasyonunun kimliği
```

### 4.2 Idempotency kuralı

```python
def get_or_create_simulation(config: SimulationConfiguration) -> SolverJob:
    fingerprint = compute_execution_fingerprint(config)
    existing = find_completed_job_by_fingerprint(fingerprint)
    if existing:
        return existing   # "Cache hit — mevcut sonuç kullanılıyor"
    return submit_new_job(config, fingerprint)
```

Aynı fingerprint'e sahip tamamlanmış bir iş varsa, HPC maliyeti tekrar harcanmaz.

### 4.3 Immutability — veritabanı seviyesinde zorunlu (uygulama kuralı değil)

```sql
CREATE OR REPLACE FUNCTION prevent_immutable_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Immutable record: UPDATE/DELETE not permitted on %', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_mutation
BEFORE UPDATE OR DELETE ON model_revision
FOR EACH ROW EXECUTE FUNCTION prevent_immutable_mutation();
-- Aynı trigger: material_dataset, dummy_configuration, pulse_definition,
-- regulatory_standard, requirement, evidence_artifact tabloları için de tekrarlanır.
```

Başarısız bir `UPDATE` denemesi **gürültülü şekilde reddedilir** (sessiz no-op değil) ve ayrı bir audit kanalına (aynı transaction içine değil — transaction rollback riskini önlemek için) kaydedilir.

### 4.4 Manifest saklama — sadece hash değil, içerik de

```
evidence_artifact/
  {id}/
    input_manifest.json     ← insan tarafından okunabilir, hash'i input_manifest_sha256
    output_manifest.json    ← insan tarafından okunabilir, hash'i output_manifest_sha256
    package.pdf
```

Hash tek başına "neyin hash'i" olduğunu göstermez; manifest dosyasının kendisi obje depolamada saklanarak denetçiye (auditor) okunabilir bağlam sağlanır.

---

## Contract 5 — Golden Dataset / Scientific Regression Contract

**Görev:** Kod değişikliklerinin, daha önce doğrulanmış bilimsel sonuçları sessizce bozmadığını garanti etmek. **Bu contract'ın tamamı, gerçek bir fiziksel sled testi verisi olmadan sadece bir iskelet olarak var olabilir** ⚠️ [GOLDEN-DATA BAĞIMLI — TÜM CONTRACT].

### 5.1 Üç katmanlı yapı

```
golden/
  raw/
    physical_test.csv          ← gerçek sled testinden (henüz temin edilmedi)
    simulation_output.binout   ← bilinen, elle doğrulanmış bir simülasyon çalışmasından
  intermediate/
    filtered_signals.json
    time_zero_aligned.json
    resampled_common_grid.json
  final/
    injury_metrics.json        ← {"HIC15": …, "Nij": …, "femur_load": …}
    correlation_vectors.json
    requirement_results.json
```

### 5.2 CI/CD regresyon akışı

```
Yeni kod commit edilir
   ↓
golden/raw/ verisi pipeline'dan geçirilir
   ↓
Her katmanın çıktısı, golden/{layer}/ ile karşılaştırılır
   ↓
Contract 2.3'teki metrik-bazlı toleranslar uygulanır
   ↓
Herhangi bir katman tolerans dışına çıkarsa: hangi katmanda kırıldığı raporlanır
   (örn. "raw: PASS, filter: PASS, time-zero: FAIL, downstream: invalidated")
   ↓
PASS ise: merge'e izin verilir. FAIL ise: engellenir.
```

### 5.3 Numerik regresyon ile mühendislik regresyonu ayrımı

```
Numerical regression   → "Kod değişince sonuç değişti mi?" (küçük toleranslar, örn. 1e-4 bağıl)
Engineering regression → "Değişiklik, requirement PASS/FAIL kararını etkiler mi?" (büyük, anlamlı sapmalar)
```

İkisi ayrı CI adımı olarak raporlanır — bir yuvarlama hatası ile koltuğun gerçekten farklı bir sonuç vermesi karıştırılmaz.

### 5.4 Bu contract'ın şu anki gerçek durumu

- Şema ve pipeline mantığı **tanımlanmıştır** (yukarıdaki gibi kodlanabilir).
- **Doldurulacak veri henüz yoktur.** `golden/raw/physical_test.csv` bomboş bir yer tutucu.
- Bu contract, gerçek bir OTEST (veya pilot müşteri) sled test seti temin edilene kadar **"yapısal olarak hazır, bilimsel olarak boş"** statüsünde kalır.
- V1.0'ın "Definition of Done"ı (önceki spec'teki Bölüm 12), pratikte bu contract'ın gerçek veriyle doldurulmasına bağlıdır — yani bu, teknik değil **tedarik** riskidir.

---

## Özet — Contract'lar Arası Bağımlılık Haritası

```
Contract 3 (Solver Adapter)         → bağımsız, hemen implemente edilebilir
Contract 4 (Evidence & Immutability) → bağımsız, hemen implemente edilebilir
Contract 1 (Scientific Processing)   → iskelet hemen yazılabilir, kalibrasyonu golden data gerektirir
Contract 2 (Correlation)              → iskelet hemen yazılabilir, kalibrasyonu golden data gerektirir
Contract 5 (Golden Dataset)            → şema hazır, İÇERİK golden data'ya %100 bağımlı
```

**Pratik sonuç:** Ekip, Contract 3 ve 4 üzerinde hemen kodlamaya başlayabilir. Contract 1, 2, 5'in iskeleti de paralel yazılabilir — ama bunların "doğru" olduğunu iddia etmek, gerçek bir fiziksel test verisi elinize geçene kadar mümkün değil. Bu yüzden **golden-data tedariki (OTEST veya bir pilot müşteri üzerinden), yazılım takvimiyle aynı öncelikte, ayrı bir iş akışı olarak yönetilmeli.**
