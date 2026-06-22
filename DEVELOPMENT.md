# 🧬 Estado del Proyecto y Memoria de Desarrollo — VarAI Detect

Este archivo sirve como memoria técnica para que cualquier desarrollador o agente de IA pueda retomar el proyecto desde el estado actual.

---

## 📌 Datos de la Sesión Actual
* **ID de Conversación de Referencia (Antigravity):** `0e256ae4-dcba-4288-b360-db897e6226d9`
* **Última Actualización:** 2026-06-22

---

## 🚀 Arquitectura de la Solución (Híbrida y Dinámica)
Para solucionar el problema de portabilidad y tamaño de las bases de datos (REVEL ~7 GB y CADD ~80GB), la aplicación se rediseñó para operar en la nube:
1. **Bases de Datos Locales a Supabase:** Los archivos de CADD y REVEL fueron filtrados exclusivamente para la región BRCA1 del cromosoma 17 y migrados exitosamente a tablas en Supabase.
2. **Consulta Híbrida CADD/REVEL:** La aplicación (`app.py`) busca primero los archivos locales. Si está desplegada en la nube y no existen los archivos pesados, consulta directamente a Supabase a través de la API para obtener los valores `cadd_phred` y `REVEL`.
3. **Frecuencia Alélica (AF) en Tiempo Real:** En lugar de alojar gigabytes de datos poblacionales, la aplicación consulta de forma dinámica y en tiempo real la API pública de **gnomAD** por cada variante para obtener el valor `af` (frecuencia en exomas o genomas).

---

## 🛠️ Estado del Proyecto

### ✅ Lo que ya está Hecho y Completado:
1. **Obtención de CADD y REVEL:** Aunque el servidor oficial de CADD fallaba por *Connection timed out* en WSL, el archivo `cadd_brca1.tsv` fue incorporado manualmente al directorio. REVEL se descargó y procesó con éxito.
2. **Configuración de Supabase:** Se crearon las tablas e índices mediante `supabase_schema.sql` y se habilitó *Row Level Security (RLS)*.
3. **Población de la Base de Datos:** Se actualizó `setup_database.py` para manejar conflictos de inserción (`on_conflict`) y eliminar transcritos duplicados de REVEL. **Se logró cargar el 100% de las variantes de BRCA1** (243,210 de CADD y 13,703 únicas de REVEL) hacia Supabase usando la clave `service_role`.
4. **Repositorio en GitHub:** El código fue integrado en la rama `main` del repositorio `TF4ir/bioinformatica`. El archivo `.gitignore` fue configurado para proteger los secretos e ignorar los datos locales pesados.
5. **Despliegue en Streamlit Cloud:** La aplicación está funcional en la web. Está configurada con los *Secrets* (credenciales de Supabase en formato TOML) para conectarse a la base de datos remotamente.

---

## 📋 Pasos Futuros o Tareas Pendientes

El pipeline ya funciona de extremo a extremo, pero si necesitas hacer mantenimiento en el futuro:

### 1. Limpieza de Entorno Local
Dado que los datos ya están en Supabase de forma segura, puedes eliminar de forma permanente los archivos pesados locales para liberar ~6.7 GB de disco:
* Archivo `revel.zip`
* Carpeta `revel_data/`
* Archivo `cadd_brca1.tsv`
*(Al eliminarlos, la app local automáticamente empezará a probar la conexión contra Supabase, tal como lo hace la versión en producción).*

### 2. Modificaciones al código
Si modificas la lógica en `app.py` o el modelo `brca1_dataset_final.csv`:
1. Haz un `git add .` y `git commit -m "Cambios"`
2. Sube los cambios con `git push origin main`
3. Streamlit Cloud detectará el push y reiniciará la app web automáticamente en un par de minutos.

### 3. Recordatorio de Secretos en Producción
Si creas un nuevo proyecto en Supabase, recuerda que en **Streamlit Cloud -> Advanced Settings -> Secrets**, las variables deben estar entre comillas dobles (formato TOML estricto), de la siguiente forma:
```toml
SUPABASE_URL="https://tu-url.supabase.co"
SUPABASE_KEY="tu-service-role-key-que-empieza-con-secret"
```
