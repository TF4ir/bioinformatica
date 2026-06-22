import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import os
from dotenv import load_dotenv
from supabase import create_client
from sklearn.ensemble import RandomForestClassifier

# ── Credenciales Supabase ────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass  # Se maneja más adelante en la UI

# ── Configuración de la página ───────────────────────────────────────────────
st.set_page_config(
    page_title="VarAI Detect",
    page_icon="🧬",
    layout="wide"
)

st.title("🧬 VarAI Detect")
st.markdown("**Sistema de clasificación y priorización de variantes VUS en BRCA1**")

# Indicador de estado de conexión en la barra lateral
with st.sidebar:
    st.markdown("### ⚙️ Estado del sistema")
    if supabase:
        st.success("🟢 Supabase conectado")
    else:
        st.warning("🟡 Supabase no configurado")
        st.caption("Configura `.env` con tus credenciales para habilitar la base de datos en la nube.")

    tiene_archivos_locales = (
        os.path.exists("cadd_brca1.tsv") and
        os.path.exists("revel_data/revel_with_transcript_ids")
    )
    if tiene_archivos_locales:
        st.info("📁 Archivos locales CADD/REVEL disponibles")
    else:
        if supabase:
            st.info("☁️ Usando Supabase para scores CADD/REVEL")
        else:
            st.error("❌ Sin fuente de datos CADD/REVEL")

st.markdown("---")

# ── Carga del modelo ─────────────────────────────────────────────────────────
@st.cache_resource
def cargar_modelo():
    df = pd.read_csv("brca1_dataset_final.csv")
    FEATURES = ["cadd_phred", "REVEL", "af"]
    X = df[FEATURES].values
    y = df["etiqueta"].values
    modelo = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    modelo.fit(X, y)
    return modelo, FEATURES

modelo, FEATURES = cargar_modelo()

# ── Carga de referencias (archivos locales — fallback) ───────────────────────
@st.cache_data
def cargar_referencias_locales():
    """Carga CADD y REVEL desde archivos locales (método original)."""
    df_cadd = pd.read_csv(
        "cadd_brca1.tsv", sep="\t", header=None,
        names=["chr", "pos", "ref", "alt", "raw_score", "cadd_phred"]
    )
    df_cadd["pos"] = df_cadd["pos"].astype(str)
    df_cadd["chr"] = df_cadd["chr"].astype(str)

    chunks = []
    for chunk in pd.read_csv(
        "revel_data/revel_with_transcript_ids",
        sep=",", low_memory=False, chunksize=100000
    ):
        filtrado = chunk[chunk.iloc[:, 0].astype(str) == "17"]
        if len(filtrado) > 0:
            chunks.append(filtrado)
    df_revel = pd.concat(chunks, ignore_index=True)
    df_revel["grch38_pos"] = df_revel["grch38_pos"].astype(str)
    df_revel["chr"] = df_revel["chr"].astype(str)
    return df_cadd, df_revel


# ── Consulta de scores desde Supabase ────────────────────────────────────────
def obtener_scores_supabase(df_vcf):
    """
    Consulta los scores CADD y REVEL desde las tablas de Supabase
    para las variantes del VCF. Retorna un DataFrame con las columnas
    chr, pos, ref, alt, cadd_phred, REVEL.
    """
    resultados = []

    for _, row in df_vcf.iterrows():
        chr_val = str(row["chr"])
        pos_val = str(row["pos"])
        ref_val = str(row["ref"])
        alt_val = str(row["alt"])

        # Consultar CADD
        cadd_phred = None
        try:
            resp = supabase.table("cadd_brca1") \
                .select("cadd_phred") \
                .eq("chr", chr_val) \
                .eq("pos", pos_val) \
                .eq("ref", ref_val) \
                .eq("alt", alt_val) \
                .maybe_single() \
                .execute()
            if resp.data:
                cadd_phred = resp.data["cadd_phred"]
        except Exception:
            pass

        # Consultar REVEL
        revel_score = None
        try:
            resp = supabase.table("revel_brca1") \
                .select("revel_score") \
                .eq("chr", chr_val) \
                .eq("grch38_pos", pos_val) \
                .eq("ref", ref_val) \
                .eq("alt", alt_val) \
                .maybe_single() \
                .execute()
            if resp.data:
                revel_score = resp.data["revel_score"]
        except Exception:
            pass

        resultados.append({
            "chr": chr_val,
            "pos": pos_val,
            "ref": ref_val,
            "alt": alt_val,
            "cadd_phred": cadd_phred,
            "REVEL": revel_score
        })

    return pd.DataFrame(resultados)


def enriquecer_variantes(df_vcf):
    """
    Obtiene scores CADD y REVEL para las variantes del VCF.
    Prioridad: archivos locales > Supabase.
    Retorna un DataFrame con cadd_phred y REVEL añadidos.
    """
    df_vcf["pos"] = df_vcf["pos"].astype(str)
    df_vcf["chr"] = df_vcf["chr"].astype(str)

    tiene_locales = (
        os.path.exists("cadd_brca1.tsv") and
        os.path.exists("revel_data/revel_with_transcript_ids")
    )

    if tiene_locales:
        # ── Método original: merge con archivos locales ──
        st.caption("📁 Usando archivos locales para CADD y REVEL")
        df_cadd, df_revel = cargar_referencias_locales()

        df_con_cadd = df_vcf.merge(
            df_cadd[["chr", "pos", "ref", "alt", "cadd_phred"]],
            on=["chr", "pos", "ref", "alt"], how="left"
        )
        df_con_todo = df_con_cadd.merge(
            df_revel[["grch38_pos", "ref", "alt", "REVEL"]],
            left_on=["pos", "ref", "alt"],
            right_on=["grch38_pos", "ref", "alt"], how="left"
        ).drop(columns=["grch38_pos"])
        return df_con_todo

    elif supabase:
        # ── Método nuevo: consulta a Supabase ──
        st.caption("☁️ Consultando scores desde Supabase...")
        df_scores = obtener_scores_supabase(df_vcf)
        return df_scores

    else:
        st.error(
            "⚠️ **No hay fuente de datos CADD/REVEL disponible.**\n\n"
            "Opciones:\n"
            "1. Coloca los archivos `cadd_brca1.tsv` y `revel_data/` en el directorio del proyecto.\n"
            "2. Configura Supabase en el archivo `.env` y ejecuta `setup_database.py`."
        )
        return None


# ── Funciones auxiliares ─────────────────────────────────────────────────────
def consultar_gnomad(chr_, pos, ref, alt):
    variante_id = f"{chr_}-{pos}-{ref}-{alt}"
    query = """
    query {
      variant(variantId: "%s", dataset: gnomad_r4) {
        genome { af }
        exome  { af }
      }
    }
    """ % variante_id
    try:
        response = requests.post(
            "https://gnomad.broadinstitute.org/api",
            json={"query": query}, timeout=30
        )
        if response.status_code != 200:
            return 0.0
        data = response.json().get("data", {}).get("variant", None)
        if data is None:
            return 0.0
        genome_af = (data.get("genome") or {}).get("af", None)
        exome_af  = (data.get("exome")  or {}).get("af", None)
        if genome_af is not None:
            return genome_af
        if exome_af is not None:
            return exome_af
        return 0.0
    except Exception:
        return 0.0

def asignar_prioridad(prob):
    if prob >= 0.7:
        return "🔴 Alta"
    elif prob >= 0.4:
        return "🟡 Media"
    else:
        return "🟢 Baja"

def parsear_vcf(archivo):
    filas = []
    for linea in archivo:
        if isinstance(linea, bytes):
            linea = linea.decode("utf-8")
        if linea.startswith("#"):
            continue
        partes = linea.strip().split("\t")
        if len(partes) < 5:
            continue
        filas.append({
            "chr": partes[0].replace("chr", ""),
            "pos": partes[1],
            "ref": partes[3],
            "alt": partes[4]
        })
    return pd.DataFrame(filas)

def guardar_en_supabase(laboratorio, df_resultado):
    if not supabase:
        st.warning("⚠️ No se guardó en la base de datos (Supabase no está configurado).")
        return False
    try:
        supabase.table("historial_analisis").insert({
            "laboratorio": laboratorio,
            "total_variantes": int(len(df_resultado)),
            "alta":  int((df_resultado["prioridad"] == "🔴 Alta").sum()),
            "media": int((df_resultado["prioridad"] == "🟡 Media").sum()),
            "baja":  int((df_resultado["prioridad"] == "🟢 Baja").sum()),
            "resultados": df_resultado.to_dict(orient="records")
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error al guardar en Supabase: {e}")
        return False

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📁 Subir archivo VCF",
    "📊 Ver resultados guardados",
    "📈 Historial de análisis"
])

# ── TAB 1: Subir VCF ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("Subir archivo VCF con variantes del paciente")

    laboratorio = st.text_input("Nombre del laboratorio o código de muestra", 
                                 placeholder="Ej: Lab_Genomica_USIL_001")

    archivo = st.file_uploader("Selecciona tu archivo VCF", type=["vcf", "txt"])

    if archivo is not None and laboratorio:
        st.info("Procesando variantes...")

        df_vcf = parsear_vcf(archivo)
        st.write(f"**Variantes detectadas:** {len(df_vcf)}")

        df_vcf = df_vcf[
            (df_vcf["ref"].str.len() == 1) &
            (df_vcf["alt"].str.len() == 1)
        ].reset_index(drop=True)
        st.write(f"**Variantes missense procesables:** {len(df_vcf)}")

        if len(df_vcf) == 0:
            st.error("No se encontraron variantes missense en el archivo.")
        else:
            with st.spinner("Obteniendo scores CADD y REVEL..."):
                df_con_todo = enriquecer_variantes(df_vcf)

            if df_con_todo is not None:
                df_procesable = df_con_todo[
                    df_con_todo["cadd_phred"].notna() &
                    df_con_todo["REVEL"].notna()
                ].copy().reset_index(drop=True)

                if len(df_procesable) == 0:
                    st.warning("Ninguna variante tiene scores CADD y REVEL disponibles.")
                else:
                    st.write(f"**Variantes con CADD y REVEL:** {len(df_procesable)}")

                    progress = st.progress(0)
                    status   = st.empty()
                    afs = []
                    for i, fila in df_procesable.iterrows():
                        af = consultar_gnomad(
                            fila["chr"], fila["pos"], fila["ref"], fila["alt"]
                        )
                        afs.append(af)
                        progress.progress((i + 1) / len(df_procesable))
                        status.text(f"Consultando gnomAD: {i+1}/{len(df_procesable)}")
                        time.sleep(0.3)

                    df_procesable["af"] = afs
                    status.text("✅ Consulta gnomAD completada")

                    probs = modelo.predict_proba(df_procesable[FEATURES].values)[:, 1]
                    df_procesable["prob_patogenica"] = probs
                    df_procesable["prioridad"] = df_procesable["prob_patogenica"].apply(
                        asignar_prioridad
                    )

                    df_resultado = df_procesable[
                        ["chr", "pos", "ref", "alt", "cadd_phred", 
                         "REVEL", "af", "prob_patogenica", "prioridad"]
                    ].sort_values("prob_patogenica", ascending=False).reset_index(drop=True)

                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("🔴 Alta",  (df_resultado["prioridad"] == "🔴 Alta").sum())
                    col2.metric("🟡 Media", (df_resultado["prioridad"] == "🟡 Media").sum())
                    col3.metric("🟢 Baja",  (df_resultado["prioridad"] == "🟢 Baja").sum())

                    st.markdown("### Tabla de resultados")
                    st.dataframe(df_resultado, use_container_width=True)

                    # Guardamos en Supabase
                    if guardar_en_supabase(laboratorio, df_resultado):
                        st.success("✅ Resultados guardados en Supabase correctamente")

                    csv = df_resultado.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Descargar resultados CSV",
                        data=csv,
                        file_name="vus_priorizadas_varai.csv",
                        mime="text/csv"
                    )

    elif archivo is not None and not laboratorio:
        st.warning("Por favor ingresa el nombre del laboratorio antes de procesar.")

# ── TAB 2: Ver resultados guardados ──────────────────────────────────────────
with tab2:
    st.subheader("Resultados del análisis previo de VUS en BRCA1")

    if os.path.exists("vus_priorizadas_varai.csv"):
        df_guardado = pd.read_csv("vus_priorizadas_varai.csv")
        df_guardado["prioridad"] = df_guardado["prob_patogenica"].apply(asignar_prioridad)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total VUS", len(df_guardado))
        col2.metric("🔴 Alta",  (df_guardado["prioridad"] == "🔴 Alta").sum())
        col3.metric("🟡 Media", (df_guardado["prioridad"] == "🟡 Media").sum())
        col4.metric("🟢 Baja",  (df_guardado["prioridad"] == "🟢 Baja").sum())

        st.markdown("---")
        prioridad_filtro = st.selectbox(
            "Filtrar por prioridad:",
            ["Todas", "🔴 Alta", "🟡 Media", "🟢 Baja"]
        )

        df_mostrar = df_guardado if prioridad_filtro == "Todas" else \
                     df_guardado[df_guardado["prioridad"] == prioridad_filtro]

        st.markdown(f"### {len(df_mostrar)} variantes")
        st.dataframe(df_mostrar, use_container_width=True)

        csv = df_mostrar.to_csv(index=False)
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv,
            file_name="vus_filtradas.csv",
            mime="text/csv"
        )
    else:
        st.warning("No hay resultados guardados. Sube un archivo VCF en la pestaña anterior.")

# ── TAB 3: Historial Supabase ─────────────────────────────────────────────────
with tab3:
    st.subheader("Historial de análisis guardados en Supabase")

    if st.button("🔄 Cargar historial"):
        if not supabase:
            st.warning(
                "⚠️ Supabase no está configurado. "
                "Verifica las variables SUPABASE_URL y SUPABASE_KEY en `.env`."
            )
        else:
            try:
                respuesta = supabase.table("historial_analisis").select("*").order(
                    "fecha", desc=True
                ).execute()
                df_historial = pd.DataFrame(respuesta.data)

                if len(df_historial) == 0:
                    st.info("No hay análisis guardados aún.")
                else:
                    st.write(f"**Total de análisis guardados:** {len(df_historial)}")
                    st.dataframe(
                        df_historial[["fecha", "laboratorio", "total_variantes", 
                                      "alta", "media", "baja"]],
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Error al conectar con Supabase: {e}")
