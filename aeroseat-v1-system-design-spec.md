# AeroSeat Certification OS — V1.0 System Design Specification

**Durum:** Uygulamaya hazır teknik tasarım
**Kapsam:** 16g forward pulse, tek FAA HIII-50M dummy, LS-DYNA adapter, modular monolith
**Bu belge kimin için:** Doğrudan kod yazmaya başlayacak backend/frontend mühendisleri için

---

## 0. V1.0 Anayasası (değiştirilemez kurallar)

Bu yedi kural, aşağıdaki her tasarım kararının üstünde durur. Bir özellik bu kurallardan biriyle çelişiyorsa, o özellik V2/V3'e ertelenir.

1. Fizik motoru yazılmaz — sadece LS-DYNA adapter'ı yazılır (solver-agnostic arayüz arkasında).
2. V1'de sadece **16g forward** pulse desteklenir.
3. V1'de sadece **1 adet FAA HIII-50M** dummy desteklenir.
4. Mimari **modular monolith + async worker** olur; event-driven microservices yok.
5. Evrensel bir "%X güvenilirlik = geçti" eşiği yok; korelasyon bir **vektör** olarak sunulur, nihai karar mühendise bırakılır.
6. Blockchain yok; **SHA-256 tabanlı, değiştirilemez (immutable) kanıt zinciri** var.
7. Sistem "sertifikasyon onayı" vermez; **"Certification Readiness / Engineering Assessment"** üretir.

---

## 1. Uçtan Uca Veri Hattı (Master Pipeline)

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
CredibilityAssessment
   ↓
RequirementStatus
   ↓
EngineeringAssessment
   ↓
EvidenceArtifact
```

Her ok, veritabanında bir yabancı anahtar (foreign key) ilişkisine karşılık gelir. Bu zincir kırılmadığı sürece 14g, Radioss, çoklu dummy gibi genişlemeler çekirdek şemayı bozmadan eklenebilir.

---

## 2. Sistem Mimarisi

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
                   PostgreSQL (source of truth)
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
   HPC / Cloud Compute (S3-uyumlu obje depolama ile birlikte)
```

**Dizin/modül yapısı (kod tabanında, monolith içinde mantıksal ayrım):**

```
aeroseat/
├── api/                  # FastAPI route'ları
│   ├── projects.py
│   ├── models.py
│   ├── simulations.py
│   ├── correlation.py
│   └── evidence.py
├── domain/               # İş mantığı, DB modelinden bağımsız
│   ├── model_qa/
│   ├── injury_metrics/
│   ├── correlation/
│   ├── regulatory/
│   └── evidence/
├── adapters/
│   └── solver/
│       ├── base.py       # BaseSolverAdapter
│       └── lsdyna.py      # LSDynaAdapter
├── workers/
│   ├── simulation_worker.py
│   └── correlation_worker.py
├── db/
│   ├── models.py         # SQLAlchemy ORM
│   └── migrations/       # Alembic
└── storage/               # S3/obje depolama erişim katmanı
```

---

## 3. Veritabanı Şeması (PostgreSQL / SQLAlchemy)

### 3.1 Tasarım ilkesi: her şey "revision" (immutable — değiştirilemez)

Hiçbir kayıt üzerine yazma (UPDATE ile içerik değiştirme) yapılmaz. Bir CAD veya malzeme değiştiğinde, yeni bir **revision** satırı eklenir; eskisi silinmez. Bu, evidence chain'in anlamlı olmasının ön koşuludur.

### 3.2 Çekirdek tablolar

```sql
-- Proje / koltuk mimarisi
CREATE TABLE seat_architecture (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,               -- "AeroEco 2026"
    customer_id   UUID NOT NULL REFERENCES customer(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CAD / model revizyonları (immutable)
CREATE TABLE model_revision (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seat_architecture_id UUID NOT NULL REFERENCES seat_architecture(id),
    revision_label    TEXT NOT NULL,            -- "Rev C"
    cad_file_uri      TEXT NOT NULL,            -- obje depolama yolu (S3 vb.)
    cad_file_sha256   CHAR(64) NOT NULL,
    part_manifest     JSONB NOT NULL,           -- sınıflandırılmış parça listesi
    uploaded_by       UUID NOT NULL REFERENCES app_user(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Malzeme veri seti (immutable)
CREATE TABLE material_dataset (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,              -- "Al-2024-T3"
    revision_label  TEXT NOT NULL,              -- "Rev 7"
    lsdyna_mat_card TEXT NOT NULL,              -- *MAT_024 vb. tanım (metin/JSON)
    sha256          CHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Dummy konfigürasyonu (immutable)
CREATE TABLE dummy_configuration (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dummy_type    TEXT NOT NULL,                -- "FAA_HIII_50M"
    fe_model_uri  TEXT NOT NULL,                -- Humanetics FE model dosya yolu
    fe_model_sha256 CHAR(64) NOT NULL,
    positioning_spec JSONB NOT NULL,             -- koltuktaki konum/açı tanımı
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pulse tanımı (immutable)
CREATE TABLE pulse_definition (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,                -- "P16-STD-04"
    direction     TEXT NOT NULL CHECK (direction IN ('FORWARD_16G')),  -- V1: sabit
    curve_data    JSONB NOT NULL,               -- [{t, accel_g}, ...]
    tolerance_band JSONB NOT NULL,               -- üst/alt tolerans eğrileri
    sha256        CHAR(64) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Regülasyon / standart versiyonlama
CREATE TABLE regulatory_standard (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          TEXT NOT NULL,                -- "AS8049", "14CFR25.562", "ARP5765B"
    revision      TEXT NOT NULL,                -- "E"
    effective_date DATE,
    document_uri  TEXT
);

-- Somut gereksinim (bir standardın alt maddesi)
CREATE TABLE requirement (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_id   UUID NOT NULL REFERENCES regulatory_standard(id),
    code          TEXT NOT NULL,                -- "RQ-00217"
    description   TEXT NOT NULL,
    metric        TEXT NOT NULL,                -- "HIC15" | "NIJ" | "FEMUR_LOAD" | "LUMBAR_LOAD" | "EXCURSION"
    limit_operator TEXT NOT NULL,               -- "<=" 
    limit_value   NUMERIC NOT NULL,
    limit_unit    TEXT NOT NULL
);

-- Simülasyon konfigürasyonu (bir "test case" tanımı)
CREATE TABLE simulation_configuration (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_revision_id    UUID NOT NULL REFERENCES model_revision(id),
    material_dataset_id  UUID NOT NULL REFERENCES material_dataset(id),
    dummy_configuration_id UUID NOT NULL REFERENCES dummy_configuration(id),
    pulse_definition_id   UUID NOT NULL REFERENCES pulse_definition(id),
    solver_name           TEXT NOT NULL DEFAULT 'LSDYNA',
    solver_version         TEXT NOT NULL,        -- "R13.0"
    created_by             UUID NOT NULL REFERENCES app_user(id),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Model QA sonucu (simülasyon başlamadan önceki kapı)
CREATE TABLE model_qa_result (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_configuration_id UUID NOT NULL REFERENCES simulation_configuration(id),
    checks                   JSONB NOT NULL,     -- {"mass_balance": "PASS", "negative_jacobian": "FAIL", ...}
    overall_status            TEXT NOT NULL CHECK (overall_status IN ('PASS','WARNING','BLOCKED')),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Solver işi (Celery job)
CREATE TABLE solver_job (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_configuration_id UUID NOT NULL REFERENCES simulation_configuration(id),
    status                    TEXT NOT NULL CHECK (status IN
                               ('QUEUED','PREPARING','RUNNING','COMPLETED','FAILED','CANCELLED')),
    input_manifest_sha256      CHAR(64),          -- solver'a giden tüm dosyaların birleşik hash'i
    hpc_job_id                  TEXT,              -- bulut/HPC tarafındaki iş kimliği
    started_at                   TIMESTAMPTZ,
    finished_at                  TIMESTAMPTZ,
    error_message                 TEXT
);

-- Ham simülasyon sonucu (dosya referansı + özet)
CREATE TABLE simulation_result (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    solver_job_id    UUID NOT NULL REFERENCES solver_job(id),
    d3plot_uri       TEXT NOT NULL,               -- deformasyon/animasyon verisi
    binout_uri       TEXT NOT NULL,               -- sensör zaman serileri
    output_sha256    CHAR(64) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Yaralanma kriterleri (hesaplanmış)
CREATE TABLE injury_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_result_id UUID NOT NULL REFERENCES simulation_result(id),
    hic15               NUMERIC,
    nij_max              NUMERIC,
    nij_type              TEXT,                   -- hangi Nij türü en yüksekti
    femur_load_left       NUMERIC,
    femur_load_right      NUMERIC,
    lumbar_load           NUMERIC,
    head_excursion_mm      NUMERIC,
    knee_excursion_mm      NUMERIC,
    seat_structural_status  TEXT,                  -- "INTACT" | "FAILED"
    raw_timeseries          JSONB,                 -- gerekli kanallar için zaman serisi
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fiziksel test (sled testi) verisi
CREATE TABLE physical_test (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seat_architecture_id UUID NOT NULL REFERENCES seat_architecture(id),
    test_facility      TEXT,                      -- "OTEST"
    test_date           DATE,
    raw_data_uri         TEXT NOT NULL,            -- ham sensör CSV/binary
    raw_data_sha256       CHAR(64) NOT NULL,
    tema_video_uri         TEXT,
    metadata               JSONB                    -- kalibrasyon, kanal listesi vb.
);

-- Korelasyon çalışması (bir simülasyonu bir fiziksel testle eşleştirir)
CREATE TABLE correlation_run (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_result_id   UUID NOT NULL REFERENCES simulation_result(id),
    physical_test_id        UUID NOT NULL REFERENCES physical_test(id),
    method                    TEXT NOT NULL DEFAULT 'ARP5765B',
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Korelasyon vektörü — kanal bazında, TEK skor değil
CREATE TABLE correlation_vector (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_run_id  UUID NOT NULL REFERENCES correlation_run(id),
    channel              TEXT NOT NULL,           -- "head_acceleration", "femur_load_left", ...
    magnitude_error       NUMERIC,
    phase_error_ms          NUMERIC,
    shape_metric_sprague_geers NUMERIC,
    peak_error              NUMERIC,
    rms_error                 NUMERIC,
    engineering_note           TEXT
);

-- Model güvenilirlik değerlendirmesi (vektörden türetilen, açıklamalı, TEK sayı DEĞİL)
CREATE TABLE credibility_assessment (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_run_id   UUID NOT NULL REFERENCES correlation_run(id),
    signal_correlation_status TEXT,                -- "ACCEPTABLE" | "CONDITIONAL" | "UNACCEPTABLE"
    model_verification_status TEXT,
    test_quality_status         TEXT,
    parameter_confidence_status TEXT,
    overall_assessment            TEXT,             -- açıklayıcı metin, tek yüzde değil
    reviewed_by                     UUID REFERENCES app_user(id),
    created_at                        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Gereksinim durumu (her requirement için pass/fail)
CREATE TABLE requirement_status (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id       UUID NOT NULL REFERENCES requirement(id),
    injury_metrics_id      UUID NOT NULL REFERENCES injury_metrics(id),
    measured_value           NUMERIC NOT NULL,
    status                     TEXT NOT NULL CHECK (status IN ('PASS','FAIL')),
    margin_percent              NUMERIC              -- limite ne kadar yakın kaldığı
);

-- Nihai mühendislik değerlendirmesi (dört kavramı birbirinden ayırır)
CREATE TABLE engineering_assessment (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_configuration_id UUID NOT NULL REFERENCES simulation_configuration(id),
    requirement_compliance_summary JSONB NOT NULL,  -- her requirement'ın PASS/FAIL özeti
    model_credibility_id             UUID REFERENCES credibility_assessment(id),
    overall_readiness                  TEXT NOT NULL,  -- "READY" | "CONDITIONALLY_READY" | "NOT_READY"
    engineer_comments                    TEXT,
    approved_by                            UUID REFERENCES app_user(id),
    created_at                              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Kanıt zinciri (immutable, kriptografik)
CREATE TABLE evidence_artifact (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engineering_assessment_id UUID NOT NULL REFERENCES engineering_assessment(id),
    parent_evidence_id      UUID REFERENCES evidence_artifact(id),  -- zincirleme
    input_manifest_sha256     CHAR(64) NOT NULL,
    output_manifest_sha256      CHAR(64) NOT NULL,
    package_pdf_uri                TEXT NOT NULL,
    software_version                 TEXT NOT NULL,
    created_at                         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Değiştirilemez denetim izi (her önemli eylem loglanır)
CREATE TABLE audit_event (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type    TEXT NOT NULL,                -- "model_revision", "solver_job", ...
    entity_id       UUID NOT NULL,
    action           TEXT NOT NULL,               -- "CREATED", "STATUS_CHANGED", ...
    actor_id          UUID REFERENCES app_user(id),
    payload            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> Not: `customer`, `app_user` tabloları standart (id, name, email, org, roller) — burada yer kazanmak için atlandı.

---

## 4. API Tasarımı (FastAPI)

Tüm endpoint'ler `/api/v1/` altında. Kimlik doğrulama: Bearer token (JWT), her istek `customer_id` bazlı izole edilir (multi-tenant).

### 4.1 Proje ve model

```
POST   /projects                          → yeni SeatArchitecture oluştur
GET    /projects/{id}                      → proje detayları
POST   /projects/{id}/model-revisions       → CAD yükle, ModelRevision oluştur
                                              (arka planda: parça sınıflandırma job'ı tetiklenir)
GET    /model-revisions/{id}                 → parça manifestosu, sınıflandırma durumu
PATCH  /model-revisions/{id}/parts/{part_id} → mühendisin manuel parça doğrulaması
```

### 4.2 Referans veri (malzeme / dummy / pulse / regülasyon)

```
POST   /material-datasets                  → yeni malzeme kartı kaydı
POST   /dummy-configurations               → yeni dummy konfigürasyonu
POST   /pulse-definitions                  → pulse eğrisi yükle (CSV/JSON)
GET    /regulatory-standards                → mevcut standart/versiyon listesi
GET    /requirements?standard=AS8049&rev=E   → o standarda bağlı gereksinimler
```

### 4.3 Simülasyon

```
POST   /simulation-configurations           → model+material+dummy+pulse birleştir
POST   /simulation-configurations/{id}/qa    → Model QA Gate'i çalıştır (senkron, hızlı)
POST   /simulation-configurations/{id}/run    → Solver Job başlat (QA PASS/WARNING ise)
GET    /solver-jobs/{id}                        → durum (QUEUED/RUNNING/COMPLETED/FAILED)
GET    /solver-jobs/{id}/result                  → SimulationResult + InjuryMetrics
WS     /solver-jobs/{id}/stream                   → WebSocket ile canlı ilerleme
```

### 4.4 Korelasyon

```
POST   /physical-tests                        → fiziksel test verisi yükle
POST   /correlation-runs                        → bir SimulationResult + bir PhysicalTest eşleştir
GET    /correlation-runs/{id}                    → CorrelationVector listesi (kanal başına)
POST   /correlation-runs/{id}/credibility-review  → mühendisin CredibilityAssessment onayı
```

### 4.5 Değerlendirme ve kanıt

```
GET    /simulation-configurations/{id}/requirement-status  → her requirement için PASS/FAIL
POST   /engineering-assessments                              → nihai değerlendirmeyi oluştur/onayla
POST   /engineering-assessments/{id}/evidence-package          → PDF + hash zinciri üret
GET    /evidence-artifacts/{id}                                  → indirilebilir paket + hash geçmişi
```

**Örnek response — requirement-status:**
```json
{
  "simulation_configuration_id": "…",
  "results": [
    {"requirement": "HIC15 <= 1000", "measured": 823, "status": "PASS", "margin_percent": 17.7},
    {"requirement": "Nij <= 1.00",    "measured": 0.82, "status": "PASS", "margin_percent": 18.0},
    {"requirement": "Femur <= 10.0 kN", "measured": 9.1, "status": "PASS", "margin_percent": 9.0},
    {"requirement": "Lumbar <= 6.67 kN", "measured": 6.2, "status": "PASS", "margin_percent": 7.0}
  ]
}
```

---

## 5. Solver Adapter Sözleşmesi

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ModelData:
    model_revision_id: str
    part_manifest: dict
    material_dataset: dict
    dummy_configuration: dict

@dataclass
class PulseData:
    curve: list[tuple[float, float]]   # (t, accel_g)
    tolerance_band: dict

@dataclass
class SimulationResult:
    d3plot_uri: str
    binout_uri: str
    output_sha256: str
    solver_log_uri: str

class BaseSolverAdapter(ABC):
    """Tüm çözücüler bu sözleşmeyi uygular. Çekirdek sistem bu arayüzün
    ötesinde hiçbir çözücüye özel bilgiye sahip olmamalı."""

    @abstractmethod
    def prepare_input(self, model: ModelData, pulse: PulseData) -> str:
        """İç veri modelini solver'a özel girdi dosyasına (LS-DYNA için .k) çevirir.
        Döndürdüğü değer: hazırlanan girdi dosyasının depo yolu."""
        ...

    @abstractmethod
    def submit_job(self, input_file_uri: str, compute_config: dict) -> str:
        """HPC/cloud'a işi gönderir, sağlayıcıya özel job id döner."""
        ...

    @abstractmethod
    def poll_status(self, job_id: str) -> str:
        """QUEUED | RUNNING | COMPLETED | FAILED döner."""
        ...

    @abstractmethod
    def parse_results(self, job_id: str) -> SimulationResult:
        """Ham çıktıyı (d3plot/binout) okuyup standart SimulationResult'a çevirir."""
        ...


class LSDynaAdapter(BaseSolverAdapter):
    """V1.0'da doldurulan tek implementasyon."""
    # prepare_input: part_manifest + material_dataset → *KEYWORD deck (.k dosyası)
    #   - *MAT_024 / *MAT_054 kartları material_dataset.lsdyna_mat_card'dan doğrudan gömülür
    #   - dummy FE modeli *INCLUDE ile deck'e eklenir, positioning_spec'e göre *INITIAL_VELOCITY/
    #     transform komutlarıyla konumlandırılır
    #   - pulse curve, sled/taban parçasına *BOUNDARY_PRESCRIBED_MOTION olarak uygulanır
    # submit_job: HPC scheduler'a (Slurm/AWS Batch) mpi job olarak gönderir
    # poll_status: scheduler API/log dosyası kontrolü
    # parse_results: qd-cae-python / lasso-python ile d3plot ve binout okunur
    ...
```

**V2/V3 için:** `RadiossAdapter`, `AbaqusAdapter` aynı arayüzü uygulayarak eklenir; `SimulationConfiguration.solver_name` alanına göre `AdapterFactory` doğru sınıfı seçer. Çekirdek koda dokunulmaz.

---

## 6. Model QA Gate (Simülasyon Öncesi Kapı)

Solver çalıştırılmadan önce, saatler sürecek ve maliyetli bir işi boşa harcamamak için deterministik kontroller çalışır:

```python
def run_model_qa(model: ModelData) -> ModelQAResult:
    checks = {
        "mass_balance": check_mass_balance(model),
        "free_rigid_body": check_free_rigid_body(model),
        "negative_jacobian": check_negative_jacobian(model),
        "penetration": check_initial_penetration(model),
        "material_assignment": check_all_parts_have_material(model),
        "unconnected_components": check_connectivity(model),
        "contact_completeness": check_contact_definitions(model),
        "boundary_conditions": check_boundary_conditions(model),
        "dummy_positioning": check_dummy_position(model),
        "pulse_definition": check_pulse_validity(model),
    }
    if any(v == "FAIL" for v in checks.values()):
        overall = "BLOCKED"       # simülasyon başlatılamaz
    elif any(v == "WARNING" for v in checks.values()):
        overall = "WARNING"       # mühendis onayıyla devam edilebilir
    else:
        overall = "PASS"
    return ModelQAResult(checks=checks, overall_status=overall)
```

AI'nin V1'deki tek görevi burada: `negative_jacobian`, `penetration` gibi deterministik kuralların yanına, geçmiş modellerle karşılaştırmalı bir **anomali tespiti** (örn. "bu mesh yoğunluğu benzer projelere göre anormal düşük") eklemek — nihai kararı yine deterministik kural + mühendis verir.

---

## 7. Yaralanma Kriterleri Hesaplama (Post-Processing)

```python
import numpy as np

def compute_hic15(time: np.ndarray, accel_g: np.ndarray) -> float:
    """HIC15: 15 ms'lik kayan pencere içinde maksimum değer."""
    best = 0.0
    for i, t1 in enumerate(time):
        j_max = np.searchsorted(time, t1 + 0.015)
        for j in range(i + 1, min(j_max, len(time))):
            t2 = time[j]
            dt = t2 - t1
            if dt <= 0:
                continue
            integral = np.trapz(accel_g[i:j+1], time[i:j+1])
            hic = ((integral / dt) ** 2.5) * dt
            best = max(best, hic)
    return best

def compute_nij(fz: np.ndarray, my: np.ndarray, fzc: float, myc: float) -> tuple[float, str]:
    """Dört Nij türünden en yükseğini döndürür (tension/compression x flexion/extension)."""
    nij_series = fz / fzc + my / myc
    idx = np.argmax(np.abs(nij_series))
    return float(nij_series[idx]), classify_nij_type(fz[idx], my[idx])
```

Bu formüller literatürde/standartlarda sabit — kod, ham sensör zaman serisini formüle sokmaktan ibaret; formülün kendisi bizim icadımız değil.

---

## 8. Korelasyon Motoru (ARP5765B tabanlı)

### 8.1 İşlem sırası

```
Ham sinyal (fiziksel + simülasyon)
   ↓
Örnekleme doğrulaması
   ↓
Filtreleme (SAE J211 kanal frekans sınıfı — kanal tipine göre veritabanından okunur, hard-code YOK)
   ↓
Time-zero tespiti (eşik geçişi yöntemiyle)
   ↓
Pencere/hizalama
   ↓
Karşılaştırma metrikleri
```

### 8.2 Filtre tanımı — veri odaklı, koda gömülü değil

```json
{
  "signal": "head_acceleration",
  "filter_standard": "SAE_J211",
  "channel_frequency_class": 1000
}
{
  "signal": "femur_load",
  "filter_standard": "SAE_J211",
  "channel_frequency_class": 600
}
```

```python
def apply_cfc_filter(signal: np.ndarray, sample_rate: float, cfc: int) -> np.ndarray:
    """CFC değeri veritabanındaki SignalDefinition kaydından okunur; kodda sabit değildir."""
    ...
```

### 8.3 Karşılaştırma metrikleri

```python
def sprague_geers(sim: np.ndarray, test: np.ndarray) -> dict:
    """Magnitude + phase bileşenlerini ayrı ayrı döner — tek sayıya indirgenmez."""
    m = np.sqrt(np.sum(sim**2) / np.sum(test**2)) - 1
    # phase (correlation) bileşeni:
    p = (1 / np.pi) * np.arccos(
        np.dot(sim, test) / (np.linalg.norm(sim) * np.linalg.norm(test))
    )
    return {"magnitude_error": m, "phase_error": p}

def peak_error(sim: np.ndarray, test: np.ndarray) -> float:
    return (np.max(np.abs(sim)) - np.max(np.abs(test))) / np.max(np.abs(test))
```

Sonuç, `correlation_vector` tablosuna **kanal başına** yazılır (baş ivmesi, femur, boyun momenti ayrı ayrı) — tek bir birleşik skor asla üretilmez.

### 8.4 Credibility Assessment — açıklayıcı, sayısal eşiksiz

```python
def assess_credibility(vectors: list[CorrelationVector]) -> CredibilityAssessment:
    """Deterministik kurallar öneri üretir, ama nihai 'overall_assessment' alanı
    her zaman bir mühendisin gözden geçirip onaylamasını gerektirir
    (reviewed_by alanı NULL olamaz — sistem tek başına karar vermez)."""
    ...
```

---

## 9. Evidence Package Üretimi

### 9.1 Kriptografik zincir mantığı

```python
def build_evidence_artifact(assessment: EngineeringAssessment) -> EvidenceArtifact:
    input_manifest = {
        "model_revision_sha256": assessment.model_revision.cad_file_sha256,
        "material_dataset_sha256": assessment.material_dataset.sha256,
        "dummy_configuration_sha256": assessment.dummy_configuration.fe_model_sha256,
        "pulse_definition_sha256": assessment.pulse_definition.sha256,
        "solver_version": assessment.solver_version,
    }
    input_hash = sha256(json.dumps(input_manifest, sort_keys=True).encode()).hexdigest()

    output_manifest = {
        "simulation_result_sha256": assessment.simulation_result.output_sha256,
        "injury_metrics": assessment.injury_metrics_summary,
        "correlation_vectors": assessment.correlation_vectors,
    }
    output_hash = sha256(json.dumps(output_manifest, sort_keys=True).encode()).hexdigest()

    pdf_uri = render_evidence_pdf(assessment, input_hash, output_hash)

    return EvidenceArtifact(
        input_manifest_sha256=input_hash,
        output_manifest_sha256=output_hash,
        package_pdf_uri=pdf_uri,
        parent_evidence_id=find_previous_revision_evidence(assessment),
    )
```

### 9.2 PDF Rapor Yapısı

```
1. Executive Summary
   - Test konfigürasyonu (16g Forward, HIII-50M)
   - Genel durum: READY / CONDITIONALLY_READY / NOT_READY

2. Regulatory Compliance (standart × requirement × ölçüm × limit × PASS/FAIL tablosu)

3. Model Credibility (ARP5765B Korelasyon Özeti)
   - Referans fiziksel test kimliği
   - Kanal bazlı korelasyon vektörü tablosu (magnitude/phase/shape/peak/RMS)
   - Mühendis yorumu ve onay imzası (reviewed_by)

4. Digital Audit Trail
   - Solver versiyonu, model/malzeme/dummy/pulse hash'leri
   - input_manifest_sha256 / output_manifest_sha256
   - parent_evidence_id (önceki revizyona zincirleme)

5. Görsel Ekler
   - Deformasyon animasyonundan alınmış anahtar kareler
   - Kuvvet-zaman grafikleri
```

---

## 10. Worker / Job Yaşam Döngüsü (Celery)

```python
@celery_app.task(bind=True)
def run_simulation_job(self, simulation_configuration_id: str):
    config = load_config(simulation_configuration_id)
    qa_result = run_model_qa(config.model_data)
    save(qa_result)
    if qa_result.overall_status == "BLOCKED":
        raise SimulationBlockedError(qa_result.checks)

    adapter = AdapterFactory.get(config.solver_name)
    input_uri = adapter.prepare_input(config.model_data, config.pulse_data)
    job_id = adapter.submit_job(input_uri, compute_config=HPC_DEFAULT)

    update_status(simulation_configuration_id, "RUNNING")
    while (status := adapter.poll_status(job_id)) not in ("COMPLETED", "FAILED"):
        self.update_state(state="PROGRESS", meta={"solver_status": status})
        time.sleep(30)

    if status == "FAILED":
        update_status(simulation_configuration_id, "FAILED")
        return

    result = adapter.parse_results(job_id)
    save(result)
    metrics = compute_injury_metrics(result)
    save(metrics)
    update_status(simulation_configuration_id, "COMPLETED")
    notify_frontend_via_websocket(simulation_configuration_id)


@celery_app.task
def run_correlation_job(correlation_run_id: str):
    run = load_correlation_run(correlation_run_id)
    vectors = compute_correlation_vectors(run.simulation_result, run.physical_test)
    save_all(vectors)
    notify_frontend_via_websocket(correlation_run_id)
```

---

## 11. Güvenlik ve Veri İzolasyonu

- **Multi-tenant izolasyon:** Her sorguda `customer_id` filtresi zorunlu (row-level security PostgreSQL'de aktif edilir).
- **Obje depolama:** CAD/sonuç dosyaları müşteri başına ayrı bucket/prefix, sunucu tarafı şifreleme (SSE) zorunlu.
- **Export-control farkındalığı:** Havacılık CAD verisi hassas olabileceğinden, veri saklama bölgesi (data residency) ve erişim logları en baştan tasarlanmalı; ilk kurumsal müşteri görüşmelerinde bu konu netleştirilmeli (bu belge kapsamında varsayım yapılmaz).
- **Audit trail:** `audit_event` tablosu her durum değişikliğini, kim/ne zaman/ne yaptı bilgisiyle tutar — silinemez, sadece eklenir (append-only).

---

## 12. V1.0 Teslim Kriterleri (Definition of Done)

Aşağıdaki uçtan uca zincir, gerçek bir koltuk + gerçek (veya pilot müşteriden alınan) bir fiziksel test verisiyle **tek kesintisiz akış** halinde çalışmalı:

```
CAD yükle → Model QA PASS → Simülasyon çalıştır → Injury metrics hesapla
→ Requirement status üret → Fiziksel test yükle → Korelasyon çalıştır
→ Credibility assessment (mühendis onayı) → Engineering assessment
→ Evidence package (PDF + hash zinciri) indir
```

Bu zincir tek bir proje için uçtan uca, insan müdahalesiyle (mühendis onayları dahil) ama yazılım hatasız şekilde tamamlanabiliyorsa, V1.0 hedefine ulaşılmış sayılır.
