-- ============================================================
-- VarAI Detect — Esquema de Autenticación para Supabase
-- Ejecutar este SQL en el Editor SQL de Supabase Dashboard
-- ============================================================

-- 1. Tabla de usuarios del sistema
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    laboratorio TEXT NOT NULL,
    nombre_completo TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- 2. Índice para búsquedas rápidas por email
CREATE INDEX IF NOT EXISTS idx_usuarios_email
    ON usuarios(email);

-- 3. Agregar columna user_id a la tabla historial_analisis
--    (vincula cada análisis con el usuario que lo realizó)
ALTER TABLE historial_analisis
    ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES usuarios(id);

-- 4. Índice para filtrar historial por usuario
CREATE INDEX IF NOT EXISTS idx_historial_user_id
    ON historial_analisis(user_id);

-- 5. Habilitar RLS en la tabla de usuarios
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

-- 6. Políticas de acceso para la tabla usuarios
--    (solo se accede via service_role key desde la app)
CREATE POLICY "Permitir lectura de usuarios" ON usuarios
    FOR SELECT USING (true);

CREATE POLICY "Permitir inserción de usuarios" ON usuarios
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Permitir actualización de usuarios" ON usuarios
    FOR UPDATE USING (true);
