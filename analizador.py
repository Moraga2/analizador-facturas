import streamlit as st
import google.generativeai as genai
import os
import tempfile

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CazaFacturas", page_icon="⚡", layout="centered")

# --- GESTIÓN DE ESTADO ---
if 'api_key' not in st.session_state: st.session_state.api_key = ''
if 'ultimo_archivo' not in st.session_state: st.session_state.ultimo_archivo = None
if 'modelo_usar' not in st.session_state: st.session_state.modelo_usar = None
if 'viendo_resultados' not in st.session_state: st.session_state.viendo_resultados = False

# Lógica de la bombilla: 
# OFF -> Si no hay clave O si estamos viendo el popup
# ON -> Si hay clave Y estamos en la pantalla de subir
estado_bombilla = "off"
if st.session_state.api_key and not st.session_state.viendo_resultados:
    estado_bombilla = "on"

# --- ESTILO VISUAL ---
st.markdown(f"""
    <style>
    /* Fondo Azul Oscuro */
    .stApp {{ background-color: #001f3f; color: #FFFFFF; }}
    
    /* --- CENTRADO MAESTRO --- */
    div.block-container {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 85vh;
        padding-top: 0 !important;
        padding-bottom: 50px !important;
    }}

    /* TÍTULO PERSONALIZADO */
    .custom-title {{
        color: #FF851B;
        text-align: center;
        font-family: 'Arial Black', sans-serif;
        font-size: 3rem;
        white-space: nowrap;
        margin-bottom: 40px;
        text-shadow: 2px 2px 4px #000000;
        /* AQUÍ ESTÁ EL AJUSTE: 10px a la derecha */
        transform: translateX(10px); 
    }}
    
    /* Inputs */
    .stTextInput {{ width: 100%; max-width: 600px; margin-bottom: 20px; }}
    .stTextInput > div > div > input {{
        background-color: #001226; color: white; border: 2px solid #FF851B;
        text-align: center; font-weight: bold; letter-spacing: 2px;
        padding: 1.5rem; font-size: 1.5rem; border-radius: 10px;
    }}
    
    /* Uploader */
    .stFileUploader {{
        border: 4px dashed #FF851B;
        border-radius: 25px;
        padding: 50px;
        background-color: #001226;
        text-align: center;
        width: 100%; max-width: 800px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .stFileUploader label {{
        width: 100%; text-align: center; display: block;
        font-size: 1.8rem !important; color: #FF851B !important; font-weight: bold;
        margin-bottom: 20px;
    }}
    .stFileUploader small {{ display: none; }}
    
    /* Botones */
    .stButton > button {{
        background-color: #FF851B; color: white; border: none; width: 100%; font-weight: bold;
        padding: 15px; border-radius: 10px; font-size: 1.1rem;
    }}
    .stButton > button:hover {{ background-color: #e07b17; }}

    /* --- COHETE --- */
    @keyframes fly-diagonal {{
        0% {{ transform: translate(-10vw, 110vh) scale(1); opacity: 0; }}
        5% {{ opacity: 1; }}
        95% {{ opacity: 1; }}
        100% {{ transform: translate(110vw, -10vh) scale(1); opacity: 0; }}
    }}
    .rocket-container {{
        position: fixed; left: 0; top: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 9998; /* Un poco menos que el obrero */
    }}
    .rocket-emoji {{
        position: absolute; font-size: 150px;
        animation: fly-diagonal 12s linear infinite; 
        text-shadow: 0 0 20px rgba(255, 133, 27, 0.5);
    }}

    /* --- FOOTER (OBRERO) --- */
    .footer-container {{
        position: fixed; bottom: 0; left: 0; width: 100%;
        display: flex; justify-content: center; align-items: flex-end;
        pointer-events: none; 
        z-index: 999999; /* SIEMPRE POR ENCIMA */
        padding-bottom: 10px;
    }}
    .worker-wrapper {{
        position: relative; display: flex; flex-direction: column; align-items: center;
    }}
    .bombilla {{
        font-size: 70px; margin-bottom: -20px; z-index: 102; transition: all 0.5s ease;
    }}
    .obrero {{ font-size: 140px; z-index: 101; }}
    .bombilla-on {{ filter: drop-shadow(0 0 30px #FFFF00) brightness(1.3); opacity: 1; }}
    .bombilla-off {{ filter: grayscale(100%) brightness(0.3); opacity: 0.6; }}
    
    /* Ocultar elementos extra */
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    </style>
    """, unsafe_allow_html=True)

# --- CARGAR FOOTER AQUÍ (AL PRINCIPIO) PARA QUE NO DESAPAREZCA ---
clase_css_bombilla = f"bombilla-{estado_bombilla}"
st.markdown(f"""
    <div class="footer-container">
        <div class="worker-wrapper">
            <div class="bombilla {clase_css_bombilla}">💡</div>
            <div class="obrero">👷‍♂️</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- POP-UP ---
@st.dialog("📋 RESULTADOS DEL ANÁLISIS", width="large")
def mostrar_popup(texto_resultado):
    st.markdown(texto_resultado)
    st.markdown("---")
    if st.button("Cerrar y Analizar Otra"):
        st.session_state.viendo_resultados = False 
        st.rerun()

# --- DETECTOR MODELO ---
def conseguir_modelo_automatico():
    try:
        modelos = genai.list_models()
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower(): return m.name
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower(): return m.name
        return "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

# --- INTERFAZ PRINCIPAL ---

# 1. LOGIN
if not st.session_state.api_key:
    st.markdown('<div class="custom-title">🧟🔪⚡ DESTRIPADOR DE FACTURAS</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    input_clave = st.text_input("ZONA DE ACCESO", type="password", placeholder="CÓDIGO DE ACCESO", label_visibility="collapsed")
    
    if input_clave:
        if input_clave == "GSM":
            try:
                st.session_state.api_key = st.secrets["GOOGLE_API_KEY"]
                st.rerun()
            except:
                st.error("⚠️ Error: Configura el Secret en Streamlit.")
        else: st.error("⛔ CÓDIGO INCORRECTO")

# 2. APP
else:
    st.markdown('<div class="custom-title">🧟🔪⚡ DESTRIPADOR DE FACTURAS</div>', unsafe_allow_html=True)
    
    try:
        genai.configure(api_key=st.session_state.api_key)
        if not st.session_state.modelo_usar: st.session_state.modelo_usar = conseguir_modelo_automatico()
        
        uploaded_file = st.file_uploader("👇 SUBIR FACTURA AQUÍ 👇", type=["pdf", "jpg", "png"])

        if uploaded_file is not None:
            if uploaded_file != st.session_state.ultimo_archivo:
                
                # COHETE
                placeholder_rocket = st.empty()
                placeholder_rocket.markdown("""
                    <div class="rocket-container"><div class="rocket-emoji">🚀</div></div>
                """, unsafe_allow_html=True)
                
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    myfile = genai.upload_file(tmp_path)

                    prompt = """
                    Actúa como experto administrativo. Extrae los datos:
                    
                    1. NOMBRE DEL TITULAR:
                    Busca el nombre del cliente/empresa (Ignora la comercializadora).
                    
                    2. UBICACIÓN:
                    Extrae la dirección completa (Calle, Nº, CP, Ciudad).
                    
                    3. BÚSQUEDA EN GOOGLE (ENLACE SEGURO):
                    Formato OBLIGATORIO (cambia espacios por +):
                    https://www.google.com/search?q=[NOMBRE+DEL+TITULAR]+[CIUDAD]
                    
                    4. CUPS:
                    Código ES...
                    
                    5. POTENCIA (LISTA VERTICAL):
                    Genera lista con guiones:
                    - P1: X kW
                    - P2: X kW
                    (Solo kW).
                    
                    6. DETALLE DE CONSUMO (SOLO ENERGÍA ACTIVA):
                    Genera una lista vertical con guiones "-".
                    LO QUE SÍ QUIERO (INCLUIR):
                    - Líneas de Energía Activa (kWh x precio). Ejemplo: "P3: 595 kWh..."
                    - Líneas de DESCUENTOS o AHORROS.
                    LO QUE NO QUIERO (EXCLUIR ESTRICTAMENTE):
                    - NO incluyas Término de Potencia.
                    - NO incluyas Excesos.
                    - NO incluyas Alquileres, Impuestos o Totales.
                    """
                    
                    model = genai.GenerativeModel(st.session_state.modelo_usar)
                    response = model.generate_content([myfile, prompt])
                    
                    st.session_state.resultado_actual = response.text
                    st.session_state.ultimo_archivo = uploaded_file
                    os.remove(tmp_path)
                    placeholder_rocket.empty()
                    
                except Exception as e: 
                    placeholder_rocket.empty()
                    st.error(f"Error: {e}")
                
                st.session_state.viendo_resultados = True
                mostrar_popup(st.session_state.resultado_actual)
            else:
                if st.button("Ver Resultados de nuevo"): 
                    st.session_state.viendo_resultados = True
                    mostrar_popup(st.session_state.resultado_actual)

    except Exception as e:
        st.error("Error de conexión.")
        if st.button("Reiniciar"):
            st.session_state.api_key = ''
            st.rerun()














