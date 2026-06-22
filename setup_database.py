"""
setup_database.py — VarAI Detect
================================
Script de configuración inicial que:
  1. Lee los archivos de referencia locales (CADD y REVEL)
  2. Filtra solo las variantes en la región del gen BRCA1
  3. Sube las tablas filtradas a Supabase

Uso:
  python setup_database.py

Requisitos:
  - Tener los archivos locales:
      * cadd_brca1.tsv
      * revel_data/revel_with_transcript_ids
  - Tener configurado el archivo .env con SUPABASE_URL y SUPABASE_KEY
  - Haber ejecutado supabase_schema.sql en el Editor SQL de Supabase

Nota: Este script solo necesita ejecutarse UNA VEZ para poblar
las tablas de referencia en Supabase.
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# ── Configuración ────────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Región BRCA1 en GRCh38 (chr17)
BRCA1_CHR = "17"
BRCA1_START = 43044295
BRCA1_END   = 43125364

# Tamaño de lote para inserciones en Supabase
BATCH_SIZE = 500


def verificar_requisitos():
    """Verifica que existan las credenciales y los archivos necesarios."""
    errores = []

    if not SUPABASE_URL or not SUPABASE_KEY:
        errores.append(
            "❌ Variables SUPABASE_URL y/o SUPABASE_KEY no configuradas.\n"
            "   Copia .env.example como .env y completa tus credenciales."
        )

    if not os.path.exists("cadd_brca1.tsv"):
        errores.append(
            "❌ No se encontró 'cadd_brca1.tsv'.\n"
            "   Descárgalo de https://cadd.gs.washington.edu/ usando tabix\n"
            "   para la región chr17:43044295-43125364"
        )

    if not os.path.exists("revel_data/revel_with_transcript_ids"):
        errores.append(
            "❌ No se encontró 'revel_data/revel_with_transcript_ids'.\n"
            "   Descárgalo de https://sites.google.com/site/revelgenomics/downloads\n"
            "   y descomprímelo en la carpeta revel_data/"
        )

    if errores:
        print("\n⚠️  REQUISITOS FALTANTES:\n")
        for e in errores:
            print(f"  {e}\n")
        sys.exit(1)


def insertar_en_lotes(supabase, tabla, registros, nombre_tabla):
    """Inserta registros en Supabase en lotes para evitar timeouts."""
    total = len(registros)
    insertados = 0
    errores = 0

    for i in range(0, total, BATCH_SIZE):
        lote = registros[i : i + BATCH_SIZE]
        try:
            if tabla == "revel_brca1":
                supabase.table(tabla).upsert(lote, on_conflict="chr,grch38_pos,ref,alt").execute()
            else:
                supabase.table(tabla).upsert(lote, on_conflict="chr,pos,ref,alt").execute()
            insertados += len(lote)
            progreso = (insertados / total) * 100
            print(f"  [{nombre_tabla}] {insertados}/{total} ({progreso:.1f}%)", end="\r")
        except Exception as e:
            errores += len(lote)
            print(f"\n  ⚠️ Error en lote {i//BATCH_SIZE + 1}: {e}")

    print(f"\n  ✅ {nombre_tabla}: {insertados} insertados, {errores} errores")
    return insertados, errores


def procesar_cadd(supabase):
    """Lee cadd_brca1.tsv, filtra BRCA1 y sube a Supabase."""
    print("\n📄 Procesando CADD scores...")

    df = pd.read_csv(
        "cadd_brca1.tsv", sep="\t", header=None,
        names=["chr", "pos", "ref", "alt", "raw_score", "cadd_phred"]
    )

    # Asegurar tipos
    df["chr"] = df["chr"].astype(str)
    df["pos_int"] = pd.to_numeric(df["pos"], errors="coerce")

    # Filtrar región BRCA1
    df_brca1 = df[
        (df["chr"] == BRCA1_CHR) &
        (df["pos_int"] >= BRCA1_START) &
        (df["pos_int"] <= BRCA1_END)
    ].copy()

    df_brca1["pos"] = df_brca1["pos"].astype(str)
    df_brca1 = df_brca1.drop(columns=["pos_int"])

    print(f"  Total variantes CADD: {len(df)}")
    print(f"  Filtradas para BRCA1: {len(df_brca1)}")

    # Convertir a registros
    registros = df_brca1.to_dict(orient="records")

    # Subir a Supabase
    return insertar_en_lotes(supabase, "cadd_brca1", registros, "CADD")


def procesar_revel(supabase):
    """Lee REVEL, filtra chr17/BRCA1 y sube a Supabase."""
    print("\n📄 Procesando REVEL scores...")

    chunks = []
    total_leidos = 0

    for chunk in pd.read_csv(
        "revel_data/revel_with_transcript_ids",
        sep=",", low_memory=False, chunksize=100000
    ):
        total_leidos += len(chunk)
        # Filtrar chr17
        filtrado = chunk[chunk.iloc[:, 0].astype(str) == BRCA1_CHR]
        if len(filtrado) > 0:
            chunks.append(filtrado)
        print(f"  Leyendo REVEL... {total_leidos} filas procesadas", end="\r")

    if not chunks:
        print("\n  ⚠️ No se encontraron datos REVEL para chr17")
        return 0, 0

    df_revel = pd.concat(chunks, ignore_index=True)
    print(f"\n  Total variantes REVEL chr17: {len(df_revel)}")

    # Filtrar solo región BRCA1
    df_revel["pos_int"] = pd.to_numeric(df_revel["grch38_pos"], errors="coerce")
    df_brca1 = df_revel[
        (df_revel["pos_int"] >= BRCA1_START) &
        (df_revel["pos_int"] <= BRCA1_END)
    ].copy()

    print(f"  Filtradas para BRCA1: {len(df_brca1)}")
    
    # Remover duplicados (mismo chr, pos, ref, alt) debido a múltiples transcritos
    df_brca1 = df_brca1.drop_duplicates(subset=["chr", "grch38_pos", "ref", "alt"]).copy()
    print(f"  Únicas a subir: {len(df_brca1)}")

    # Preparar registros con las columnas que necesitamos
    registros = []
    for _, row in df_brca1.iterrows():
        registros.append({
            "chr": str(row.iloc[0]),           # chr
            "grch38_pos": str(row["grch38_pos"]),
            "ref": str(row["ref"]),
            "alt": str(row["alt"]),
            "revel_score": float(row["REVEL"]) if pd.notna(row["REVEL"]) else None
        })

    # Filtrar registros sin score
    registros = [r for r in registros if r["revel_score"] is not None]

    # Subir a Supabase
    return insertar_en_lotes(supabase, "revel_brca1", registros, "REVEL")


def main():
    print("=" * 60)
    print("🧬 VarAI Detect — Setup de Base de Datos")
    print("=" * 60)

    # 1. Verificar requisitos
    verificar_requisitos()

    # 2. Conectar a Supabase
    print("\n🔌 Conectando a Supabase...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("  ✅ Conexión exitosa")
    except Exception as e:
        print(f"  ❌ Error de conexión: {e}")
        sys.exit(1)

    # 3. Procesar y subir CADD (YA SUBIDO, IGNORANDO)
    cadd_ok, cadd_err = 0, 0 # procesar_cadd(supabase)

    # 4. Procesar y subir REVEL
    revel_ok, revel_err = procesar_revel(supabase)

    # 5. Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"  CADD:  {cadd_ok} registros subidos ({cadd_err} errores)")
    print(f"  REVEL: {revel_ok} registros subidos ({revel_err} errores)")
    print()

    if cadd_err == 0 and revel_err == 0:
        print("  ✅ ¡Setup completado exitosamente!")
        print("  Ahora puedes ejecutar la app con: streamlit run app.py")
    else:
        print("  ⚠️ Hubo algunos errores. Revisa los mensajes anteriores.")

    print()


if __name__ == "__main__":
    main()
