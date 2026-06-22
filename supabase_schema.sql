-- ============================================================
-- VarAI Detect — Esquema de Base de Datos para Supabase
-- Ejecutar este SQL en el Editor SQL de Supabase Dashboard
-- ============================================================

-- 1. Tabla de scores CADD filtrados para la región BRCA1
CREATE TABLE IF NOT EXISTS cadd_brca1 (
    id BIGSERIAL PRIMARY KEY,
    chr TEXT NOT NULL,
    pos TEXT NOT NULL,
    ref TEXT NOT NULL,
    alt TEXT NOT NULL,
    raw_score DOUBLE PRECISION,
    cadd_phred DOUBLE PRECISION NOT NULL,
    UNIQUE(chr, pos, ref, alt)
);

-- 2. Tabla de scores REVEL filtrados para la región BRCA1
CREATE TABLE IF NOT EXISTS revel_brca1 (
    id BIGSERIAL PRIMARY KEY,
    chr TEXT NOT NULL,
    grch38_pos TEXT NOT NULL,
    ref TEXT NOT NULL,
    alt TEXT NOT NULL,
    revel_score DOUBLE PRECISION NOT NULL,
    UNIQUE(chr, grch38_pos, ref, alt)
);

-- 3. Tabla de historial de análisis
CREATE TABLE IF NOT EXISTS historial_analisis (
    id BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    laboratorio TEXT NOT NULL,
    total_variantes INTEGER DEFAULT 0,
    alta INTEGER DEFAULT 0,
    media INTEGER DEFAULT 0,
    baja INTEGER DEFAULT 0,
    resultados JSONB
);

-- 4. Índices para búsquedas rápidas por variante
CREATE INDEX IF NOT EXISTS idx_cadd_lookup
    ON cadd_brca1(chr, pos, ref, alt);

CREATE INDEX IF NOT EXISTS idx_revel_lookup
    ON revel_brca1(chr, grch38_pos, ref, alt);

CREATE INDEX IF NOT EXISTS idx_historial_fecha
    ON historial_analisis(fecha DESC);

-- 5. Habilitar Row Level Security (buena práctica en Supabase)
ALTER TABLE cadd_brca1 ENABLE ROW LEVEL SECURITY;
ALTER TABLE revel_brca1 ENABLE ROW LEVEL SECURITY;
ALTER TABLE historial_analisis ENABLE ROW LEVEL SECURITY;

-- 6. Políticas de acceso público (para la API key anon/service_role)
--    Ajusta según tus necesidades de seguridad.
CREATE POLICY "Permitir lectura pública de CADD" ON cadd_brca1
    FOR SELECT USING (true);

CREATE POLICY "Permitir lectura pública de REVEL" ON revel_brca1
    FOR SELECT USING (true);

CREATE POLICY "Permitir lectura pública del historial" ON historial_analisis
    FOR SELECT USING (true);

CREATE POLICY "Permitir inserción en historial" ON historial_analisis
    FOR INSERT WITH CHECK (true);
