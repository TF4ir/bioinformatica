# 🧬 Estado del Proyecto y Memoria de Desarrollo — VarAI Detect

Este archivo sirve como memoria técnica para que cualquier desarrollador o agente de IA pueda retomar el proyecto desde el estado actual.

---

## 📌 Datos de la Sesión Actual
* **ID de Conversación de Referencia (Antigravity):** `412462d0-60d1-4b01-8ad0-45e63540b094`
* **Última Actualización:** 2026-06-19

---

## 🚀 Arquitectura de la Solución (Híbrida)
Para solucionar el problema de portabilidad y espacio (los archivos originales de REVEL pesan ~7 GB y CADD ~100-500 MB, imposibles de subir a GitHub o Supabase completos), se rediseñó la app:
1. **Filtro por BRCA1:** Dado que la app solo analiza la región de BRCA1 en el cromosoma 17, las bases de datos de CADD y REVEL se filtran localmente para quedarse solo con esa región (~5-20 MB en total).
2. **Tablas en Supabase:** Se crearon estructuras para almacenar los scores de BRCA1 en la nube.
3. **Consulta Dinámica:** La aplicación `app.py` busca primero los archivos de referencia locales. Si no existen, consulta automáticamente a Supabase vía API. Esto permite que los laboratorios (clientes) usen la plataforma subiendo solo su VCF sin descargar gigabytes de datos de referencia.

---

## 🛠️ Estado del Proyecto

### ✅ Lo que ya está Hecho y Configurado:
1. **Entorno Virtual (`.venv`):** Configurado con Python 3.14 y dependencias instaladas (`streamlit`, `pandas`, `supabase`, `scikit-learn`, etc.).
2. **Código de la App (`app.py`):** Completamente reescrito. Detecta si la conexión a Supabase está activa y si hay archivos locales. Si no hay archivos locales, hace consultas seguras por API a Supabase.
3. **Esquema de Base de Datos (`supabase_schema.sql`):** Script SQL listo para crear las tablas `historial_analisis`, `cadd_brca1` y `revel_brca1` con sus respectivos índices para búsquedas veloces.
4. **Script de Carga (`setup_database.py`):** Script listo para procesar los archivos locales filtrando BRCA1 y subiendo los datos en lotes de 500 filas a Supabase.
5. **Descarga de REVEL:** Completada con éxito. El archivo `revel_data/revel_with_transcript_ids` (~6.05 GB) y `revel.zip` (~667 MB) están en el disco local de Windows (`C:\Users\Usuario\Desktop\Git\bioinformatica`).

### ⚠️ Lo que quedó Pendiente (Bloqueado por Servidor Externo):
* **Descarga de CADD:** El servidor oficial de CADD de la Universidad de Washington (`krishna.gs.washington.edu`) experimentó caídas y arrojó *Connection timed out* al intentar hacer las peticiones `tabix`. Falta el archivo `cadd_brca1.tsv` en la raíz del proyecto.

---

## 📋 Pasos a Seguir para Completar el Setup

Cuando retomes el proyecto, debes seguir estos pasos en orden:

### Paso 1: Obtener el archivo de CADD
Dado que el servidor web de CADD está caído, pídele a tu compañera el archivo **`cadd_brca1.tsv`** (pesa solo ~15 MB ya filtrado por ella) y colócalo en la raíz de tu proyecto `C:\Users\Usuario\Desktop\Git\bioinformatica\`.

### Paso 2: Configurar Supabase
1. Entra a tu consola de [Supabase](https://supabase.com/).
2. Ve al **SQL Editor** de tu proyecto y ejecuta todo el código de [supabase_schema.sql](file:///C:/Users/Usuario/Desktop/Git/bioinformatica/supabase_schema.sql) para crear las tablas e índices.
3. Copia el archivo `.env.example` y nómbralo como `.env`.
4. Rellena las variables `SUPABASE_URL` y `SUPABASE_KEY` con las credenciales de tu proyecto (las encuentras en *Project Settings* -> *API*).

### Paso 3: Subir los datos iniciales
Con los archivos `cadd_brca1.tsv` y `revel_data/revel_with_transcript_ids` en tu carpeta, ejecuta:
```powershell
.venv\Scripts\python setup_database.py
```
*Este script subirá los scores filtrados de CADD y REVEL a tu base de datos de Supabase. Solo se ejecuta una vez.*

### Paso 4: Limpiar disco (Liberar ~6.7 GB)
Una vez que `setup_database.py` termine con éxito (100% completado), puedes borrar permanentemente para liberar espacio:
* El archivo `revel.zip`
* La carpeta `revel_data/`
* El archivo `cadd_brca1.tsv`

### Paso 5: Ejecutar la App
Inicia el servidor local de Streamlit para probar la plataforma como lo haría un laboratorio real:
```powershell
.venv\Scripts\python -m streamlit run app.py
```
*La app se conectará a Supabase para enriquecer las variantes de cualquier archivo VCF que subas sin requerir archivos locales.*
