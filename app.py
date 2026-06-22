import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import os
import hashlib
import secrets
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

# ── CSS Premium para Login ───────────────────────────────────────────────────
def aplicar_estilos_login():
    st.markdown("""
    <style>
    /* ── Reset y base ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .login-container {
        max-width: 440px;
        margin: 2rem auto;
        padding: 2.5rem 2rem;
        background: linear-gradient(145deg, rgba(30, 33, 48, 0.95), rgba(20, 22, 35, 0.98));
        border-radius: 20px;
        border: 1px solid rgba(99, 102, 241, 0.2);
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.4),
                    0 0 40px rgba(99, 102, 241, 0.08);
        backdrop-filter: blur(20px);
    }

    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .login-header .logo-icon {
        font-size: 3.5rem;
        display: block;
        margin-bottom: 0.5rem;
        animation: pulse-glow 2s ease-in-out infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.4)); }
        50% { filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.8)); }
    }

    .login-header h2 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.6rem;
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .login-header p {
        font-family: 'Inter', sans-serif;
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }

    .login-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.3), transparent);
        margin: 1.5rem 0;
    }

    /* ── Tabs de login/registro ── */
    .auth-tabs {
        display: flex;
        gap: 0;
        margin-bottom: 1.5rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 4px;
    }

    .auth-tab {
        flex: 1;
        padding: 0.6rem;
        text-align: center;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.85rem;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        color: rgba(255, 255, 255, 0.5);
        border: none;
        background: transparent;
    }

    .auth-tab.active {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
    }

    /* ── Status badges ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    .status-badge.connected {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }

    .status-badge.disconnected {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }

    /* ── User info en sidebar ── */
    .user-card {
        padding: 1rem;
        background: linear-gradient(145deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.05));
        border-radius: 14px;
        border: 1px solid rgba(99, 102, 241, 0.15);
        margin-bottom: 1rem;
    }

    .user-card .user-email {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #e2e8f0;
        font-size: 0.9rem;
        margin: 0;
    }

    .user-card .user-lab {
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.78rem;
        margin: 4px 0 0 0;
    }

    .user-avatar {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        margin-bottom: 0.6rem;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Funciones de Autenticación ────────────────────────────────────────────────
def hash_password(password, salt=None):
    """Genera un hash seguro de la contraseña usando SHA-256 + salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password, stored_hash):
    """Verifica una contraseña contra el hash almacenado."""
    salt, hashed = stored_hash.split(":")
    return hash_password(password, salt) == stored_hash

def registrar_usuario(email, password, laboratorio, nombre_completo=""):
    """Registra un nuevo usuario en la tabla usuarios de Supabase."""
    if not supabase:
        return False, "Supabase no está configurado."

    # Verificar si el email ya existe
    try:
        existe = supabase.table("usuarios").select("id").eq("email", email).execute()
        if existe.data:
            return False, "Ya existe una cuenta con este correo electrónico."
    except Exception as e:
        return False, f"Error de conexión: {e}"

    # Crear el usuario
    try:
        pw_hash = hash_password(password)
        supabase.table("usuarios").insert({
            "email": email,
            "password_hash": pw_hash,
            "laboratorio": laboratorio,
            "nombre_completo": nombre_completo
        }).execute()
        return True, "Cuenta creada exitosamente. Ahora puedes iniciar sesión."
    except Exception as e:
        return False, f"Error al crear la cuenta: {e}"

def iniciar_sesion(email, password):
    """Autentica un usuario contra la tabla usuarios de Supabase."""
    if not supabase:
        return False, None, "Supabase no está configurado."

    try:
        resp = supabase.table("usuarios").select("*").eq("email", email).maybe_single().execute()
        if not resp.data:
            return False, None, "Correo electrónico o contraseña incorrectos."

        user_data = resp.data
        if not verify_password(password, user_data["password_hash"]):
            return False, None, "Correo electrónico o contraseña incorrectos."

        # Actualizar último login
        try:
            supabase.table("usuarios").update({
                "last_login": "now()"
            }).eq("id", user_data["id"]).execute()
        except Exception:
            pass  # No bloquear el login si falla la actualización

        return True, user_data, "Inicio de sesión exitoso."
    except Exception as e:
        return False, None, f"Error de conexión: {e}"

def cerrar_sesion():
    """Cierra la sesión del usuario actual."""
    for key in ["user", "user_id", "lab_name", "user_email", "user_nombre"]:
        if key in st.session_state:
            del st.session_state[key]


# ── Pantalla de Login ─────────────────────────────────────────────────────────
def mostrar_login():
    """Renderiza la pantalla de autenticación (login + registro)."""
    aplicar_estilos_login()

    # Usar columnas para centrar el formulario
    _, col_centro, _ = st.columns([1, 1.5, 1])

    with col_centro:
        # Header con logo
        st.markdown("""
        <div class="login-header">
            <span class="logo-icon">🧬</span>
            <h2>VarAI Detect</h2>
            <p>Sistema de clasificación de variantes VUS en BRCA1</p>
        </div>
        """, unsafe_allow_html=True)

        # Status de conexión
        if supabase:
            st.markdown("""
            <div style="text-align: center;">
                <span class="status-badge connected">● Base de datos conectada</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center;">
                <span class="status-badge disconnected">● Base de datos desconectada</span>
            </div>
            """, unsafe_allow_html=True)
            st.error("⚠️ Supabase no está configurado. Verifica tu archivo `.env`.")
            st.stop()

        st.markdown("<div class='login-divider'></div>", unsafe_allow_html=True)

        # Tabs Login / Registro
        if "auth_mode" not in st.session_state:
            st.session_state.auth_mode = "login"

        col_l, col_r = st.columns(2)
        with col_l:
            if st.button("🔑 Iniciar Sesión", use_container_width=True,
                          type="primary" if st.session_state.auth_mode == "login" else "secondary"):
                st.session_state.auth_mode = "login"
                st.rerun()
        with col_r:
            if st.button("📝 Registrarse", use_container_width=True,
                          type="primary" if st.session_state.auth_mode == "registro" else "secondary"):
                st.session_state.auth_mode = "registro"
                st.rerun()

        st.markdown("")  # Spacer

        if st.session_state.auth_mode == "login":
            mostrar_formulario_login()
        else:
            mostrar_formulario_registro()


def mostrar_formulario_login():
    """Formulario de inicio de sesión."""
    with st.form("login_form", clear_on_submit=False):
        st.markdown("#### 🔑 Iniciar Sesión")

        email = st.text_input(
            "Correo electrónico",
            placeholder="usuario@laboratorio.com",
            key="login_email"
        )
        password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Tu contraseña",
            key="login_password"
        )

        submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Por favor completa todos los campos.")
            else:
                with st.spinner("Verificando credenciales..."):
                    ok, user_data, msg = iniciar_sesion(email, password)
                if ok:
                    st.session_state.user = user_data
                    st.session_state.user_id = user_data["id"]
                    st.session_state.lab_name = user_data["laboratorio"]
                    st.session_state.user_email = user_data["email"]
                    st.session_state.user_nombre = user_data.get("nombre_completo", "")
                    st.success(f"✅ {msg}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


def mostrar_formulario_registro():
    """Formulario de registro de nuevos usuarios."""
    with st.form("registro_form", clear_on_submit=True):
        st.markdown("#### 📝 Crear nueva cuenta")

        nombre = st.text_input(
            "Nombre completo",
            placeholder="Dr. Juan Pérez",
            key="reg_nombre"
        )
        email = st.text_input(
            "Correo electrónico",
            placeholder="usuario@laboratorio.com",
            key="reg_email"
        )
        laboratorio = st.text_input(
            "Nombre del laboratorio",
            placeholder="Ej: Lab_Genomica_USIL_001",
            key="reg_lab"
        )
        password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Mínimo 6 caracteres",
            key="reg_password"
        )
        password_confirm = st.text_input(
            "Confirmar contraseña",
            type="password",
            placeholder="Repite tu contraseña",
            key="reg_password_confirm"
        )

        submitted = st.form_submit_button("Crear cuenta", use_container_width=True, type="primary")

        if submitted:
            # Validaciones
            if not all([email, laboratorio, password, password_confirm]):
                st.error("Por favor completa todos los campos obligatorios.")
            elif len(password) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres.")
            elif password != password_confirm:
                st.error("Las contraseñas no coinciden.")
            elif "@" not in email:
                st.error("Por favor ingresa un correo electrónico válido.")
            else:
                with st.spinner("Creando cuenta..."):
                    ok, msg = registrar_usuario(email, password, laboratorio, nombre)
                if ok:
                    st.success(f"✅ {msg}")
                    st.session_state.auth_mode = "login"
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


# ── Gate de Autenticación ─────────────────────────────────────────────────────
def usuario_autenticado():
    """Retorna True si hay un usuario logueado en session_state."""
    return "user" in st.session_state and st.session_state.user is not None


# ── GATE: Si no está autenticado, mostrar login y detener ────────────────────
if not usuario_autenticado():
    mostrar_login()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  A PARTIR DE AQUÍ, SOLO SE EJECUTA SI EL USUARIO ESTÁ AUTENTICADO
# ══════════════════════════════════════════════════════════════════════════════

st.title("🧬 VarAI Detect")
st.markdown("**Sistema de clasificación y priorización de variantes VUS en BRCA1**")

# Indicador de estado de conexión y usuario en la barra lateral
with st.sidebar:
    # Info del usuario logueado
    user_nombre = st.session_state.get("user_nombre", "")
    user_email = st.session_state.get("user_email", "")
    user_lab = st.session_state.get("lab_name", "")

    st.markdown(f"""
    <div class="user-card">
        <div class="user-avatar">👤</div>
        <p class="user-email">{user_nombre or user_email}</p>
        <p class="user-lab">🏥 {user_lab}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Cerrar sesión", use_container_width=True):
        cerrar_sesion()
        st.rerun()

    st.markdown("---")
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

def guardar_en_supabase(laboratorio, df_resultado, user_id=None):
    if not supabase:
        st.warning("⚠️ No se guardó en la base de datos (Supabase no está configurado).")
        return False
    try:
        registro = {
            "laboratorio": laboratorio,
            "total_variantes": int(len(df_resultado)),
            "alta":  int((df_resultado["prioridad"] == "🔴 Alta").sum()),
            "media": int((df_resultado["prioridad"] == "🟡 Media").sum()),
            "baja":  int((df_resultado["prioridad"] == "🟢 Baja").sum()),
            "resultados": df_resultado.to_dict(orient="records")
        }
        # Vincular el análisis con el usuario autenticado
        if user_id:
            registro["user_id"] = user_id
        supabase.table("historial_analisis").insert(registro).execute()
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

    # El laboratorio se auto-rellena con el lab del usuario logueado
    laboratorio = st.text_input(
        "Nombre del laboratorio o código de muestra",
        value=st.session_state.get("lab_name", ""),
        placeholder="Ej: Lab_Genomica_USIL_001",
        disabled=True,
        help="Este campo se rellena automáticamente con tu laboratorio registrado."
    )

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

                    # Guardamos en Supabase con el user_id del usuario autenticado
                    user_id = st.session_state.get("user_id", None)
                    if guardar_en_supabase(laboratorio, df_resultado, user_id=user_id):
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

# ── TAB 3: Historial Supabase (FILTRADO POR USUARIO) ─────────────────────────
with tab3:
    st.subheader("📈 Historial de análisis")
    st.caption(f"Mostrando análisis del laboratorio: **{st.session_state.get('lab_name', 'N/A')}**")

    if st.button("🔄 Cargar historial"):
        if not supabase:
            st.warning(
                "⚠️ Supabase no está configurado. "
                "Verifica las variables SUPABASE_URL y SUPABASE_KEY en `.env`."
            )
        else:
            try:
                user_id = st.session_state.get("user_id", None)

                # Filtrar historial por el user_id del usuario logueado
                query = supabase.table("historial_analisis").select("*")
                if user_id:
                    query = query.eq("user_id", user_id)
                respuesta = query.order("fecha", desc=True).execute()

                df_historial = pd.DataFrame(respuesta.data)

                if len(df_historial) == 0:
                    st.info("No tienes análisis guardados aún. Sube un archivo VCF para empezar.")
                else:
                    st.write(f"**Total de análisis realizados:** {len(df_historial)}")

                    # Mostrar métricas resumen
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("📊 Total análisis", len(df_historial))
                    col2.metric("🔴 Total Alta", df_historial["alta"].sum())
                    col3.metric("🟡 Total Media", df_historial["media"].sum())
                    col4.metric("🟢 Total Baja", df_historial["baja"].sum())

                    st.markdown("---")

                    # Tabla de historial (sin columna de resultados JSON)
                    columnas_mostrar = ["fecha", "laboratorio", "total_variantes",
                                        "alta", "media", "baja"]
                    columnas_disponibles = [c for c in columnas_mostrar if c in df_historial.columns]
                    st.dataframe(
                        df_historial[columnas_disponibles],
                        use_container_width=True
                    )

                    # Opción de expandir detalles de cada análisis
                    st.markdown("### 🔍 Detalle por análisis")
                    for idx, row in df_historial.iterrows():
                        fecha = row.get("fecha", "Sin fecha")
                        lab = row.get("laboratorio", "N/A")
                        total = row.get("total_variantes", 0)
                        with st.expander(f"📅 {fecha} — {lab} ({total} variantes)"):
                            if "resultados" in row and row["resultados"]:
                                df_detalle = pd.DataFrame(row["resultados"])
                                st.dataframe(df_detalle, use_container_width=True)

                                csv_detalle = df_detalle.to_csv(index=False)
                                st.download_button(
                                    label="⬇️ Descargar este análisis",
                                    data=csv_detalle,
                                    file_name=f"analisis_{lab}_{fecha}.csv",
                                    mime="text/csv",
                                    key=f"download_{idx}"
                                )
                            else:
                                st.info("Sin datos detallados para este análisis.")

            except Exception as e:
                st.error(f"Error al conectar con Supabase: {e}")
