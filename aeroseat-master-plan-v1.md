# AeroSeat Certification OS — Baştan Sona Ana Plan (Master Plan v1)

**Bu belge nedir:** Önceki üç belgenin (ilk konsept plan → V1.0 System Design Spec → 5 Code Contract) yerini alan, **tek ve tam** kaynak. Şimdiye kadarki tüm kararları, düzeltmeleri ve netleşen mimariyi baştan sona, tek bir tutarlı anlatı halinde toplar. Bundan sonra bu belge referans alınmalı; öncekiler tarihsel taslak sayılabilir.

**Okuyucu kitlesi:** Hem mühendislik/kod geçmişi olmayan biri (vizyon, iş modeli, riskler) hem de doğrudan kodlamaya başlayacak bir geliştirici (şema, API, algoritma, contract) için yazıldı.

---

# BÖLÜM A — VİZYON VE İŞ BAĞLAMI

## A.1 Sorun

Havacılık koltuğu üreticileri, koltuklarını sertifikalandırmak için **14g/16g dinamik çarpma testleri** yaptırıyor (senin OTEST'te bizzat gözlemlediğin gibi). Bu testler:

- Pahalı ve genelde tek seferlik (prototip test sırasında hasar görüyor)
- Fail olursa yeniden tasarım + yeni prototip + yeniden test döngüsü doğuruyor
- Tasarım aşamasında erken geri bildirim vermiyor

## A.2 Fikrin ilk hali ve nasıl olgunlaştığı

**Başlangıç fikri:** "14g/16g testlerini bilgisayarda simüle eden bir program yazayım — CAD modeli + pulse eğrisi + dummy alıp, HIC/Nij/femur/deformasyon sonuçlarını ve pass/fail durumunu göstereyim."

**İlk kritik karar:** Fizik motorunu (LS-DYNA'nın yaptığı işi) sıfırdan yazmak, 10+ yıllık ayrı bir mühendislik problemi olduğu için **reddedildi**. Bunun yerine LS-DYNA/RADIOSS gibi sektörde zaten güvenilir solver'ların üzerine otomasyon katmanı kurma kararı alındı.

**Pazar analizi sonrası ikinci ve en önemli dönüşüm:** Piyasa araştırması, Oasys'in (LS-DYNA tabanlı) doğrudan "dynamic aircraft seat certification" iş akışını zaten pazarladığını, Humanetics'in FAA HIII-50M için hazır FE dummy modelleri sattığını, Simcenter Madymo'nun yolcu güvenliği simülasyonunda güçlü olduğunu ortaya çıkardı. Sonuç: **"Ben de crash simulation yaparım" pozisyonu zayıf** — çünkü bu araçlar zaten var ve güçlü.

**Nihai konumlandırma:** Ürün, bir "simülasyon programı" değil; **simülasyonu, fiziksel test korelasyonunu (ARP5765B metodolojisiyle), regülasyon gereksinim takibini ve kriptografik kanıt zincirini** tek bir mühendislik iş akışında birleştiren bir platform olarak tanımlandı:

> **AeroSeat Certification OS** — *Simulation → Validation/Correlation → Regulatory Evidence*, LS-DYNA/Radioss/Abaqus gibi solver'ların **üzerinde** çalışan bir mühendislik katmanı.

Buradaki "OS" bir işletim sistemi değil; **Requirement → Model → Simülasyon → Fiziksel Test → Korelasyon → Mühendislik Kararı → Regülasyon Kanıtı** zincirini yöneten bir mühendislik katmanı anlamındadır.

## A.3 Rakip haritası ve farklılaşma

| Araç | Güçlü olduğu alan | AeroSeat ile ilişki |
|---|---|---|
| **LS-DYNA / RADIOSS / Abaqus** | Explicit crash FEA çözücüsü | Rakip değil — **altyapı**; AeroSeat bunları orkestre eder |
| **Humanetics** | Sertifikalı FE dummy modelleri (çoklu solver desteği) | Rakip değil — **bileşen tedarikçisi** |
| **Simcenter Madymo** | Occupant safety, çoklu solver coupling | Kısmen rakip, kısmen tamamlayıcı |
| **Oasys (LS-DYNA Environment)** | LS-DYNA'yı kolaylaştıran CAE ortamı, havacılık koltuğu sertifikasyon workflow'u örnekleri | **En ciddi doğrudan rakip** |

**Oasys'e karşı fark:** Oasys, mühendise "LS-DYNA'yı daha kolay kullan" aracı verir. AeroSeat, mühendisin yaptığı işin kendisini (korelasyon, gereksinim takibi, kanıt paketleme) bir iş akışı olarak paketler — kullanıcı LS-DYNA kullandığını hissetmeyebilir. Uzun vadeli rekabet bariyeri (moat), tek bir özellik değil, zamanla biriken **test-simülasyon korelasyon veritabanı**dır — bu, bir rakibin parayla hemen satın alamayacağı bir varlıktır.

## A.4 Konumlandırmada dikkat edilmesi gereken sınır

Ürün asla **"sertifikasyon onayı verir"** diye pazarlanmamalı. FAA/EASA fiziksel testi hâlâ isteyecek. Doğru dil: **"Certification Readiness / Engineering Assessment"** — yani "sertifikasyona hazır olma değerlendirmesi", sertifikasyonun kendisi değil. Bu ayrım hem hukuki hem güven açısından zorunlu.

---

# BÖLÜM B — REGÜLASYON VE BİLİMSEL BAĞLAM

## B.1 İlgili standartlar

- **14 CFR § 25.562** (FAA) / **CS-25.562** (EASA) — "Emergency landing dynamic conditions", ana yasal gereksinim
- **SAE AS8049E** (Mayıs 2025 revizyonu) — koltuk performansı, qualification ve dokümantasyon gereksinimleri
- **SAE ARP5765B** — aircraft-seat modellerinin **güvenilirliğini (credibility)** ve test/simülasyon **korelasyonunu** değerlendirme metodolojisi — AeroSeat'in "Correlation Engine"i doğrudan buna dayanır

## B.2 Test senaryoları (V1.0 sadece birincisini kapsar)

1. **16g forward (yatay) pulse** — V1.0 kapsamında
2. **14g vertical (dikey) pulse** — V2.0+ için ertelendi

## B.3 Ölçülen kriterler ve limitler

| Kriter | Basit anlamı | Limit (özet) |
|---|---|---|
| **HIC15** | Baş darbesinin şiddeti | ≤ 1000 |
| **Nij** | Boyun zorlanması (4 alt türü: tension/compression × flexion/extension) | ≤ 1.0 |
| **Femur Load** | Bacak/diz çarpma yükü | ≤ ~10 kN |
| **Lumbar Load** | Bel omurga yükü (14g dikey testte) | ≤ ~6.67 kN |
| **Head/Knee Excursion** | Başın/dizin öne hareketi, öndeki objeye çarpma riski | Tanımlı sınır çizgisi |
| **Koltuk bütünlüğü** | Yapısal göçme olmamalı | PASS/FAIL |

## B.4 Bilimsel temel — açık dinamik sonlu elemanlar (explicit FE)

Zaman, mikro saniyelik dilimlere bölünür; her dilimde Newton'un F=ma yasası koltuğun binlerce noktasına uygulanır:

```
M · a(t) = F_ext(t) − F_int(t)
```

Zaman ilerletme: merkezi fark (central difference) yöntemi — hızlı ama zaman adımı (Δt ≈ 10⁻⁶–10⁻⁷ s) çok küçük tutulmalı.

**HIC formülü:**
```
HIC = max { [ (1/(t2−t1)) · ∫(t1→t2) a(t) dt ]^2.5 · (t2−t1) }   ,  t2−t1 ≤ 15 ms
```

**Nij formülü:**
```
Nij = Fz/Fzc + My/Myc     (dört kombinasyondan en yükseği: T-F, T-E, C-F, C-E)
```

Bu formüller literatürde/standartlarda sabit — AeroSeat bunları icat etmez, ham sensör verisine otomatik uygular.

**Malzeme davranışı:** Metal parçalar için elasto-plastik model (LS-DYNA `*MAT_024` gibi), kompozit parçalar için Hashin/Chang-Chang hasar kriterleri (`*MAT_054/055`). Bu malzeme kartları motor tarafından hazır sağlanır; AeroSeat doğru kartı seçip doğru katsayıları besler.

---

# BÖLÜM C — V1.0 ANAYASASI (değiştirilemez kurallar)

Aşağıdaki yedi kural, bu belgedeki her mimari kararın üstünde durur:

1. Fizik motoru yazılmaz — sadece **LS-DYNA adapter** yazılır (solver-agnostic arayüz arkasında).
2. V1'de sadece **16g forward** pulse desteklenir.
3. V1'de sadece **1 adet FAA HIII-50M** dummy desteklenir.
4. Mimari **modular monolith + async worker**; event-driven microservices V1'de yok.
5. Evrensel bir "%X güvenilirlik = geçti" eşiği yok; korelasyon **vektör** olarak sunulur, nihai kararı mühendis verir.
6. Blockchain yok; **SHA-256 tabanlı immutable kanıt zinciri** var.
7. Sistem "sertifikasyon onayı" vermez; **"Certification Readiness / Engineering Assessment"** üretir.

---

# BÖLÜM D — SİSTEM MİMARİSİ

## D.1 Dört mimari katman

```
┌──────────────────────────────┐
│ 1. ENGINEERING                │  Model / Simülasyon / Yaralanma metrikleri
├──────────────────────────────┤
│ 2. SCIENTIFIC                 │  Filtreleme / Hizalama / Korelasyon / Doğrulama
├──────────────────────────────┤
│ 3. EVIDENCE                   │  Hash / Revizyon / İzlenebilirlik / Denetim
├──────────────────────────────┤
│ 4. OPERATIONAL                │  Kuyruk / HPC / Retry / Sağlık (heartbeat)
└──────────────────────────────┘
```

## D.2 Master Pipeline (uçtan uca veri hattı)

```
CADUpload
   ↓
ModelRevision
   ↓
ModelQAResult
   ↓
SimulationConfiguration
   ↓
SolverJob
   ↓
SimulationResult
   ↓
InjuryMetrics
   ↓
CorrelationRun → CorrelationVector
   ↓
CredibilityAssessment      (mühendis onayı ZORUNLU)
   ↓
RequirementStatus
   ↓
EngineeringAssessment
   ↓
EvidenceArtifact
```

Her ok, veritabanında bir foreign-key ilişkisidir. Bu zincir bozulmadığı sürece 14g, Radioss, çoklu dummy, kompozit malzeme gibi genişlemeler çekirdek şemayı bozmadan eklenir.

## D.3 Bileşen mimarisi

```
                    Next.js (Frontend)
                         │
                         ▼
                    FastAPI (API Layer)
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Project Domain    Model QA Engine   Regulatory Engine
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                   PostgreSQL (source of truth, immutable revision'lar)
                         │
                         ▼
                    Redis + Celery (Job Queue)
        ┌────────────────┴────────────────┐
        ▼                                 ▼
 Simulation Worker                Correlation Worker
        │                                 │
        ▼                                 ▼
  LS-DYNA Adapter                 Python/NumPy/SciPy
        │
        ▼
   HPC / Cloud Compute + S3-uyumlu obje depolama
```

**Kod tabanı (monolith içinde mantıksal ayrım — bounded context):**
```
aeroseat/
├── api/            (FastAPI route'ları: projects, models, simulations, correlation, evidence)
├── domain/         (model_qa/, injury_metrics/, correlation/, regulatory/, evidence/)
├── adapters/solver/ (base.py, lsdyna.py)
├── workers/        (simulation_worker.py, correlation_worker.py, status_poller.py)
├── db/             (SQLAlchemy models, Alembic migrations)
└── storage/        (obje depolama erişim katmanı)
```

**Neden mikroservis değil:** Küçük bir ekip için ilk aylarda şema sık değişir; mikroservisler arası senkronizasyon bu aşamada hıza değil yavaşlığa yol açar. Gerçekten bağımsız ölçeklenmesi gereken parçalar (örn. simulation worker) V2/V3'te ayrılabilir.

---

# BÖLÜM E — VERİTABANI ŞEMASI

## E.1 Temel ilke: her şey immutable revision

Hiçbir kayıt üzerine yazılmaz. Değişiklik = yeni revizyon satırı. Bu, **veritabanı seviyesinde trigger ile zorlanır**, sadece uygulama kuralı olarak bırakılmaz:

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
-- Aynısı: material_dataset, dummy_configuration, pulse_definition,
-- regulatory_standard, requirement, evidence_artifact için tekrarlanır.
```

Sessiz no-op (`DO INSTEAD NOTHING`) **kullanılmaz** — mission-critical sistemde sessiz başarısızlık kabul edilemez; hata gürültülü şekilde fırlatılır ve ayrı bir audit kanalına (transaction içine değil, rollback riskini önlemek için) yazılır.

## E.2 Ana tablolar

```sql
-- Koltuk projesi
CREATE TABLE seat_architecture (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    customer_id UUID NOT NULL REFERENCES customer(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CAD revizyonu (immutable)
CREATE TABLE model_revision (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seat_architecture_id UUID NOT NULL REFERENCES seat_architecture(id),
    revision_label TEXT NOT NULL,
    cad_file_uri TEXT NOT NULL,
    cad_file_sha256 CHAR(64) NOT NULL,
    part_manifest JSONB NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Malzeme: FİZİKSEL KİMLİK ile SOLVER TEMSİLİ ayrılır (kritik tasarım kararı)
CREATE TABLE material_dataset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,               -- "Al-2024-T3"
    revision_label TEXT NOT NULL,
    mechanical_properties JSONB NOT NULL,  -- akma dayanımı, elastisite modülü — saf fiziksel veri
    sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE solver_material_representation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_dataset_id UUID NOT NULL REFERENCES material_dataset(id),
    solver_name TEXT NOT NULL,         -- "LSDYNA"
    solver_mat_card TEXT NOT NULL,      -- "*MAT_024" tanımı
    sha256 CHAR(64) NOT NULL
);
-- Aynı MaterialDataset, birden fazla SolverMaterialRepresentation'a sahip olabilir
-- (LS-DYNA + Radioss + Abaqus için ayrı temsiller) — bu, immutability'i bozmadan
-- çoklu-solver desteğini mümkün kılar.

-- Dummy, pulse (immutable)
CREATE TABLE dummy_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dummy_type TEXT NOT NULL,          -- "FAA_HIII_50M"
    fe_model_uri TEXT NOT NULL,
    fe_model_sha256 CHAR(64) NOT NULL,
    positioning_spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pulse_definition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('FORWARD_16G')),  -- V1: sabit
    curve_data JSONB NOT NULL,
    tolerance_band JSONB NOT NULL,
    sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Regülasyon (versiyonlu)
CREATE TABLE regulatory_standard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL,                -- "AS8049", "ARP5765B"
    revision TEXT NOT NULL,             -- "E"
    effective_date DATE,
    document_uri TEXT
);

CREATE TABLE requirement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_id UUID NOT NULL REFERENCES regulatory_standard(id),
    code TEXT NOT NULL,
    metric TEXT NOT NULL,               -- "HIC15" | "NIJ" | "FEMUR_LOAD" | ...
    limit_operator TEXT NOT NULL,
    limit_value NUMERIC NOT NULL,
    limit_unit TEXT NOT NULL
);

-- Simülasyon konfigürasyonu — genişletilmiş, her alt bileşen kendi immutable revizyonu
CREATE TABLE simulation_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_revision_id UUID NOT NULL REFERENCES model_revision(id),
    mesh_definition_id UUID NOT NULL REFERENCES mesh_definition(id),
    material_dataset_id UUID NOT NULL REFERENCES material_dataset(id),
    solver_material_representation_id UUID NOT NULL REFERENCES solver_material_representation(id),
    contact_definition_id UUID NOT NULL REFERENCES contact_definition(id),
    boundary_condition_set_id UUID NOT NULL REFERENCES boundary_condition_set(id),
    dummy_configuration_id UUID NOT NULL REFERENCES dummy_configuration(id),
    pulse_definition_id UUID NOT NULL REFERENCES pulse_definition(id),
    solver_name TEXT NOT NULL DEFAULT 'LSDYNA',
    solver_version TEXT NOT NULL,
    configuration_hash CHAR(64) NOT NULL,   -- bkz. Bölüm G.1
    created_by UUID NOT NULL REFERENCES app_user(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Model QA sonucu
CREATE TABLE model_qa_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_configuration_id UUID NOT NULL REFERENCES simulation_configuration(id),
    checks JSONB NOT NULL,
    overall_status TEXT NOT NULL CHECK (overall_status IN ('PASS','WARNING','BLOCKED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Solver işi — zengin durum modeli
CREATE TABLE solver_job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_configuration_id UUID NOT NULL REFERENCES simulation_configuration(id),
    execution_fingerprint CHAR(64) NOT NULL,   -- bkz. Bölüm G.1 — idempotency anahtarı
    status TEXT NOT NULL CHECK (status IN
        ('QUEUED','PREPARING','SUBMITTED','RUNNING','POST_PROCESSING','VALIDATING','COMPLETED',
         'SUBMISSION_FAILED','SOLVER_FAILED','TIMEOUT','POST_PROCESSING_FAILED',
         'VALIDATION_FAILED','CANCELLED')),
    hpc_job_id TEXT,
    last_polled_at TIMESTAMPTZ,
    last_heartbeat_at TIMESTAMPTZ,
    attempt_count INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT
);
CREATE UNIQUE INDEX idx_solver_job_fingerprint_completed
    ON solver_job(execution_fingerprint) WHERE status = 'COMPLETED';
    -- aynı fingerprint'e sahip tamamlanmış iş varsa yeniden çalıştırılmaz (idempotency)

-- Ham sonuç, yaralanma kriterleri
CREATE TABLE simulation_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    solver_job_id UUID NOT NULL REFERENCES solver_job(id),
    d3plot_uri TEXT NOT NULL,
    binout_uri TEXT NOT NULL,
    output_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE injury_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_result_id UUID NOT NULL REFERENCES simulation_result(id),
    hic15 NUMERIC, nij_max NUMERIC, nij_type TEXT,
    femur_load_left NUMERIC, femur_load_right NUMERIC, lumbar_load NUMERIC,
    head_excursion_mm NUMERIC, knee_excursion_mm NUMERIC,
    seat_structural_status TEXT,
    raw_timeseries JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fiziksel test: TestConfiguration'dan ayrılmış (kritik düzeltme)
CREATE TABLE test_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seat_architecture_id UUID NOT NULL REFERENCES seat_architecture(id),
    dummy_type TEXT NOT NULL,
    pulse_target TEXT NOT NULL,
    restraint_configuration JSONB NOT NULL,
    instrumentation_configuration JSONB NOT NULL,  -- sensör/kalibrasyon referansları
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE physical_test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_configuration_id UUID NOT NULL REFERENCES test_configuration(id),
    test_facility TEXT,               -- "OTEST"
    test_date DATE,
    raw_data_uri TEXT NOT NULL,
    raw_data_sha256 CHAR(64) NOT NULL,
    tema_video_uri TEXT,
    metadata JSONB
);

-- Korelasyon
CREATE TABLE correlation_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_result_id UUID NOT NULL REFERENCES simulation_result(id),
    physical_test_id UUID NOT NULL REFERENCES physical_test(id),
    processing_definition_id UUID NOT NULL REFERENCES processing_definition(id),
    method TEXT NOT NULL DEFAULT 'ARP5765B',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE correlation_vector (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_run_id UUID NOT NULL REFERENCES correlation_run(id),
    channel TEXT NOT NULL,
    magnitude_error NUMERIC, phase_error_ms NUMERIC,
    shape_metric_sprague_geers NUMERIC, peak_error NUMERIC, rms_error NUMERIC,
    engineering_note TEXT
);

CREATE TABLE credibility_assessment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_run_id UUID NOT NULL REFERENCES correlation_run(id),
    signal_correlation_status TEXT, model_verification_status TEXT,
    test_quality_status TEXT, parameter_confidence_status TEXT,
    overall_assessment TEXT,                -- açıklayıcı metin, TEK yüzde DEĞİL
    reviewed_by UUID NOT NULL REFERENCES app_user(id),  -- NULL olamaz — insan onayı zorunlu
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE requirement_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirement(id),
    injury_metrics_id UUID NOT NULL REFERENCES injury_metrics(id),
    measured_value NUMERIC NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS','FAIL')),
    margin_percent NUMERIC
);

CREATE TABLE engineering_assessment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_configuration_id UUID NOT NULL REFERENCES simulation_configuration(id),
    requirement_compliance_summary JSONB NOT NULL,
    model_credibility_id UUID REFERENCES credibility_assessment(id),
    overall_readiness TEXT NOT NULL,   -- "READY" | "CONDITIONALLY_READY" | "NOT_READY"
    engineer_comments TEXT,
    approved_by UUID NOT NULL REFERENCES app_user(id),
    approval_role TEXT NOT NULL,
    approved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Kanıt zinciri (immutable)
CREATE TABLE evidence_artifact (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engineering_assessment_id UUID NOT NULL REFERENCES engineering_assessment(id),
    parent_evidence_id UUID REFERENCES evidence_artifact(id),
    input_manifest_uri TEXT NOT NULL,       -- okunabilir manifest, sadece hash değil
    input_manifest_sha256 CHAR(64) NOT NULL,
    output_manifest_uri TEXT NOT NULL,
    output_manifest_sha256 CHAR(64) NOT NULL,
    package_pdf_uri TEXT NOT NULL,
    software_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only denetim izi
CREATE TABLE audit_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL, entity_id UUID NOT NULL,
    action TEXT NOT NULL, actor_id UUID REFERENCES app_user(id),
    payload JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

# BÖLÜM F — API TASARIMI (FastAPI, `/api/v1/`)

```
# Proje ve model
POST   /projects
POST   /projects/{id}/model-revisions
GET    /model-revisions/{id}
PATCH  /model-revisions/{id}/parts/{part_id}

# Referans veri
POST   /material-datasets
POST   /material-datasets/{id}/solver-representations
POST   /dummy-configurations
POST   /pulse-definitions
GET    /regulatory-standards
GET    /requirements?standard=AS8049&rev=E

# Simülasyon
POST   /simulation-configurations
POST   /simulation-configurations/{id}/qa
POST   /simulation-configurations/{id}/run     (fingerprint kontrolü → cache hit veya yeni job)
GET    /solver-jobs/{id}
WS     /solver-jobs/{id}/stream

# Korelasyon
POST   /test-configurations
POST   /physical-tests
POST   /correlation-runs
GET    /correlation-runs/{id}                  (CorrelationVector listesi, kanal başına)
POST   /correlation-runs/{id}/credibility-review

# Değerlendirme ve kanıt
GET    /simulation-configurations/{id}/requirement-status
POST   /engineering-assessments
POST   /engineering-assessments/{id}/evidence-package
GET    /evidence-artifacts/{id}
```

---

# BÖLÜM G — BEŞ CODE CONTRACT

**Not:** Aşağıdaki iki contract'ın belirli parametreleri ⚠️ **[GOLDEN-DATA BAĞIMLI]** olarak işaretli — yani gerçek bir fiziksel sled testi verisi gelene kadar "en iyi bilinen varsayım" statüsünde, kesin değil.

## G.1 Evidence & Immutability Contract

Üç ayrı hash kavramı:

```
Artifact Hash        = SHA256(dosyanın kendisi)                     — CAD, d3plot, CSV
Configuration Hash    = SHA256(ModelRevision + Mesh + Material +
                                SolverMaterialRepresentation + Contact +
                                BoundaryConditions + Dummy + Pulse + AnalysisSettings)
Execution Fingerprint  = SHA256(ConfigurationHash + SolverVersion + SolverBuild +
                                 AeroSeatEngineVersion + ProcessingDefinition.sha256)
```

Idempotency: aynı `execution_fingerprint`'e sahip `COMPLETED` bir iş varsa, yeni simülasyon çalıştırılmaz — mevcut sonuç döndürülür (HPC maliyeti tekrarlanmaz).

## G.2 Solver Adapter Contract

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

**Garanti:** Çekirdek sistem kodunda hiçbir yerde solver'a özgü bir kelime (`*MAT_024`, `d3plot` formatı, vb.) geçmez — bunlar yalnızca `LSDynaAdapter` içinde yaşar. `RadiossAdapter` eklendiğinde çekirdek kod değişmez.

## G.3 Scientific Processing Contract ⚠️ [GOLDEN-DATA BAĞIMLI]

Zorunlu işlem sırası (ProcessingDefinition olarak veride tutulur, koda gömülmez):

```
Raw Signal → Integrity Check → Unit Normalization → Channel Validation
→ Filter (SAE J211, kanal başına CFC — SignalDefinition tablosundan) → Time-Zero Detection
→ Window Selection → Common Analysis Grid → Resampling
```

Filtre CFC değerleri ve time-zero eşiği, literatürden başlangıç değeri alınabilir ama **gerçek golden dataset ile kalibre edilmeden kesinleşmez.**

## G.4 Correlation Contract ⚠️ [GOLDEN-DATA BAĞIMLI — toleranslar]

Çıktı, **tek skor değil, kanal başına vektör:**
```json
{"channel": "head_acceleration", "peak_error": 0.037, "sprague_geers_magnitude": 0.028,
 "sprague_geers_phase": 0.015, "rms_error": 0.041}
```
Tolerans eşikleri metrik-bazlı tanımlanır (HIC için bağıl, faz hatası için milisaniye cinsinden mutlak, vb.) — evrensel tek bir tolerans (`1e-5` gibi) kullanılmaz. Bu toleransların gerçek anlamı ancak birden fazla test-simülasyon çifti karşılaştırıldıktan sonra kalibre edilebilir.

## G.5 Golden Dataset / Scientific Regression Contract ⚠️ [TAMAMEN GOLDEN-DATA BAĞIMLI]

Üç katmanlı yapı: `raw/` (ham fiziksel + simülasyon verisi) → `intermediate/` (filtrelenmiş, hizalanmış sinyaller) → `final/` (HIC/Nij/korelasyon vektörleri). Her kod değişikliğinde CI, bu golden veriyi pipeline'dan geçirip her katmanda beklenen sonuçla karşılaştırır; hangi katmanda saptığını raporlar.

**Bu contract'ın gerçek durumu:** Şema ve pipeline mantığı tanımlı, **ama içerik boş** — gerçek bir OTEST (veya pilot müşteri) sled test verisi temin edilene kadar "yapısal olarak hazır, bilimsel olarak boş" statüsünde kalır. **Bu, teknik değil bir tedarik riskidir** ve yazılım takvimiyle paralel, ayrı bir iş akışı olarak yönetilmelidir.

---

# BÖLÜM H — MODEL QA GATE

Solver çalıştırılmadan önce (saatler sürecek maliyetli işi boşa harcamamak için):

```python
def run_model_qa(config: SimulationConfiguration) -> ModelQAResult:
    checks = {
        "mass_balance": ..., "free_rigid_body": ..., "negative_jacobian": ...,
        "penetration": ..., "material_assignment": ..., "unconnected_components": ...,
        "contact_completeness": ..., "boundary_conditions": ...,
        "dummy_positioning": ..., "pulse_definition": ...,
    }
    # herhangi biri FAIL → BLOCKED (simülasyon başlatılamaz)
    # herhangi biri WARNING → WARNING (mühendis onayıyla devam edilebilir)
    # hepsi PASS → PASS
```

AI'nin V1'deki tek görevi burada: deterministik kuralların yanına, geçmiş modellerle karşılaştırmalı bir anomali tespiti eklemek. Nihai kararı yine deterministik kural + mühendis verir.

---

# BÖLÜM I — WORKER / JOB YAŞAM DÖNGÜSÜ

İki aşamalı, polling-blocking olmayan mimari:

```
Submitter Worker → HPC'ye işi gönderir, hpc_job_id'yi DB'ye yazar, worker serbest kalır
        ↓
Status Poller (Celery Beat, periyodik) → HPC API'den toplu durum sorgusu →
   DB günceller (last_polled_at, last_heartbeat_at) → tamamlananları PostProcessor'a yönlendirir
        ↓
Post Processor Worker → InjuryMetrics hesaplar, sonucu kaydeder, frontend'e WebSocket bildirimi
```

Durum modeli: `QUEUED → PREPARING → SUBMITTED → RUNNING → POST_PROCESSING → VALIDATING → COMPLETED`, hata dalında `SUBMISSION_FAILED | SOLVER_FAILED | TIMEOUT | POST_PROCESSING_FAILED | VALIDATION_FAILED | CANCELLED` — "gerçek hata" ile "geçici altyapı sorunu" ayrımı `attempt_count`/`retry_count` ile yapılır.

---

# BÖLÜM J — FRONTEND

## J.1 Ana ekranlar

| Ekran | İçerik |
|---|---|
| Proje Panosu | Tüm projeler, durumları |
| CAD Yükleme & Önizleme | 3D önizleme, parça sınıflandırma sonucu, manuel doğrulama arayüzü |
| Senaryo Kurulumu | Pulse/dummy seçimi, malzeme/mesh/contact ayarları |
| Simülasyon İzleme | İlerleme, WebSocket ile canlı durum |
| Sonuç Dashboard'u | Requirement × ölçüm × limit × PASS/FAIL tablosu, kuvvet-zaman grafikleri |
| 3D Sonuç Görüntüleyici | Deformasyon animasyonu, zaman çubuğu, renk haritası |
| Korelasyon Ekranı | Kanal bazlı korelasyon vektörü, mühendis onay arayüzü (CredibilityAssessment) |
| Evidence & Rapor | PDF indirme, hash zinciri görüntüleme |

## J.2 Teknoloji yığını

React (Next.js) · Three.js/VTK.js (3D) · Recharts/D3.js (grafik) · React Query + Zustand (durum) · WebSocket (canlı bildirim)

---

# BÖLÜM K — GÜVENLİK

- Multi-tenant izolasyon (row-level security, her sorguda `customer_id` filtresi)
- Obje depolamada sunucu taraflı şifreleme, müşteri başına ayrı bucket/prefix
- Export-control farkındalığı — havacılık CAD verisi hassas olabilir; veri saklama bölgesi ve erişim politikaları ilk kurumsal müşteri görüşmesinde netleştirilmeli (bu belgede varsayım yapılmaz)
- Append-only audit_event tablosu — her durum değişikliği kim/ne zaman/ne yaptı bilgisiyle
- V1 sonrası genişleyecek alan: RBAC, MFA, secret management, key rotation, backup/DR politikası

---

# BÖLÜM L — RİSKLER

| Risk | Açıklama | Azaltma |
|---|---|---|
| **Golden-data tedariki** | Correlation/Golden Dataset contract'ları gerçek fiziksel test verisi olmadan doğrulanamaz | OTEST veya pilot müşteriden erken, yazılım takvimiyle paralel veri tedariki |
| **"Sertifikasyon" beklentisi** | Ürün adı/pazarlaması, müşteride "bize sertifika veriyor" yanılgısı yaratabilir | Tutarlı "readiness assessment" dili, satış materyalinde de |
| **LS-DYNA + Humanetics lisans maliyeti** | Bütçenin en büyük belirsizliği | Erken tedarik görüşmesi, somut teklif alınmadan taahhüt verilmemeli |
| **Aşırı spesifikasyon riski** | Dört baseline + beş contract'ı kodsuz %100 dondurmaya çalışmak, "önce solver yazalım" tuzağının incelmiş hali olabilir | Contract'ları taslak (v0.1) olarak dondurup ilk gerçek implementasyonla birlikte olgunlaştırmak |
| **Veri hassasiyeti / IP** | Müşteri CAD ve test verisi paylaşmaya çekinebilir — korelasyon veritabanı (asıl moat) buna bağlı | Veri paylaşımı sözleşmesel güvenceye bağlanmalı, pilot anlaşmada netleştirilmeli |
| **Doğrulama (validasyon)** | Sonuçların gerçek testle örtüştüğü henüz kanıtlanmadı | İlk pilot ile correlation study zorunlu adım |

---

# BÖLÜM M — YOL HARİTASI

## M.1 V1.0 kapsam tablosu

| Bileşen | V1.0 (kapsamda) | V2.0+ (ertelendi) |
|---|---|---|
| Pulse | Yalnızca 16g forward | 14g dikey, çoklu pulse |
| Koltuk tipi | Tekli/çiftli economy | Business, lie-flat |
| Dummy | 1× FAA HIII-50M | HIII-5F, çoklu dummy |
| Solver | LS-DYNA adapter (arayüz solver-agnostic) | Radioss, Abaqus adapter |
| Regülasyon | 14 CFR 25.562, AS8049E, ARP5765B | EASA farkları, askeri standartlar |
| AI | Sadece Model QA anomali tespiti | Surrogate ML, generative design |

## M.2 Fazlar (ilk ~6 ay)

1. **Ay 1:** Altyapı kurulumu (AWS/Azure), DB şeması + immutability trigger'ları, `BaseSolverAdapter` iskeleti, **golden-data tedarik görüşmelerinin başlatılması** (yazılımla paralel).
2. **Ay 2-3:** LS-DYNA adapter tamamlanır; CAD → mesh → simülasyon → sonuç uçtan uca (tek koltuk, tek dummy) bulutta çalışır hale gelir.
3. **Ay 4:** Post-processing — HIC/Nij/femur/lumbar otomatik hesaplama, requirement karşılaştırma.
4. **Ay 5:** Correlation Engine — ⚠️ bu adım gerçek/pilot fiziksel test verisine bağımlı; veri gelmemişse bu fazın kapsamı "iskelet + sentetik test verisiyle doğrulama" olarak daraltılmalı.
5. **Ay 6:** Evidence Package (PDF + hash zinciri) tamamlanır; ilk pilot müşteri ile uçtan uca deneme.

## M.3 V1.0 Definition of Done

```
CAD yükle → Model QA PASS → Simülasyon çalıştır → Injury metrics hesapla
→ Requirement status üret → Fiziksel test yükle → Korelasyon çalıştır
→ Credibility assessment (mühendis onayı) → Engineering assessment
→ Evidence package (PDF + hash zinciri) indir
```

Bu zincir **tek bir gerçek koltuk için, insan onaylarıyla ama yazılım hatasız** uçtan uca tamamlanabiliyorsa, V1.0 hedefine ulaşılmış sayılır.

## M.4 Sonraki versiyonlar (V2-V8, sıra ile)

```
V2 — Certification Engine: EASA + çoklu regülasyon versiyonlama
V3 — Validation Engine olgunlaşması: gerçek çoklu-test korelasyon veritabanı
V4 — Multi-fidelity: hızlı ön-tarama (multibody/ROM) + tam FE
V5 — Design Optimization: DOE + surrogate model önerileri
V6 — Multi-solver: Radioss + Abaqus adapter
V7 — AI Engineering Assistant: CAD sınıflandırma, setup asistanı, anomali tespiti
V8 — Tam Certification Digital Thread: requirement traceability + audit'in kurumsal ölçeği
```

---

Bu belge, projenin bugüne kadarki tüm kararlarını (ilk konsept → pazar/rakip analizi → V1 anayasası → veri modeli → beş contract) tek bir tutarlı akışta topluyor. Bundan sonraki her değişiklik, bu belgeye karşı bir "Baseline Change Request" olarak ele alınmalı — parça parça, ayrı belgelerde değil.
