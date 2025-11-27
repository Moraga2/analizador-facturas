import streamlit as st
import google.generativeai as genai
import os
import tempfile

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="GSM ElectroBot", page_icon="🤖", layout="centered")

# --- GESTIÓN DE ESTADO ---
if 'api_key' not in st.session_state: st.session_state.api_key = ''
if 'ultimo_archivo' not in st.session_state: st.session_state.ultimo_archivo = None
if 'modelo_usar' not in st.session_state: st.session_state.modelo_usar = None
if 'viendo_resultados' not in st.session_state: st.session_state.viendo_resultados = False

# Lógica del LED del Robot (Equivalente a tu bombilla)
# OFF (Gris) -> Si no hay clave O si estamos viendo el popup
# ON (Verde Brillante) -> Si hay clave Y estamos en la pantalla de subir
estado_led = "off"
if st.session_state.api_key and not st.session_state.viendo_resultados:
    estado_led = "on"

# --- ESTILO VISUAL (TEMA ROBOT) ---
st.markdown(f"""
    <style>
    /* Fondo Azul Oscuro Tecnológico */
    .stApp {{ background-color: #0b1120; color: #00ff41; font-family: 'Courier New', monospace; }}
    
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

    /* TÍTULO ROBÓTICO */
    .custom-title {{
        color: #00ff41; /* Verde Hacker */
        text-align: center;
        font-family: 'Courier New', monospace;
        font-weight: 900;
        font-size: 2.5rem;
        white-space: nowrap;
        margin-bottom: 40px;
        text-shadow: 0px 0px 10px rgba(0, 255, 65, 0.7);
        letter-spacing: -2px;
        /* Ajuste de posición centrado para el robot */
        width: 100%;
    }}
    
    /* Inputs (Estilo Terminal) */
    .stTextInput {{ width: 100%; max-width: 600px; margin-bottom: 20px; }}
    .stTextInput > div > div > input {{
        background-color: #000000; 
        color: #00ff41; 
        border: 2px solid #00ff41;
        text-align: center; font-weight: bold; letter-spacing: 3px;
        padding: 1.5rem; font-size: 1.5rem; border-radius: 5px;
    }}
    
    /* Uploader (Zona de carga) */
    .stFileUploader {{
        border: 2px dashed #00ff41;
        border-radius: 10px;
        padding: 40px;
        background-color: #050a14;
        text-align: center;
        width: 100%; max-width: 800px;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.1);
    }}
    .stFileUploader label {{
        width: 100%; text-align: center; display: block;
        font-size: 1.5rem !important; color: #00ff41 !important; font-weight: bold;
        margin-bottom: 20px; font-family: 'Courier New', monospace;
    }}
    .stFileUploader small {{ display: none; }}
    
    /* Botones */
    .stButton > button {{
        background-color: #00ff41; color: #000000; border: none; width: 100%; font-weight: bold;
        padding: 15px; border-radius: 5px; font-size: 1.1rem; text-transform: uppercase;
    }}
    .stButton > button:hover {{ background-color: #00cc33; color: white; }}

    /* --- ANIMACIÓN DEL ROBOT VOLADOR --- */
    @keyframes fly-scan {{
        0% {{ transform: translate(-10vw, 50vh) scale(1); opacity: 0; }}
        10% {{ opacity: 1; }}
        90% {{ opacity: 1; }}
        100% {{ transform: translate(110vw, -10vh) scale(1); opacity: 0; }}
    }}
    .rocket-container {{
        position: fixed; left: 0; top: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 9998;
    }}
    .rocket-emoji {{
        position: absolute; font-size: 120px;
        animation: fly-scan 8s linear infinite; 
        filter: drop-shadow(0 0 15px #00ff41);
    }}

    /* --- FOOTER (ROBOT BASE) --- */
    .footer-container {{
        position: fixed; bottom: 0; left: 0; width: 100%;
        display: flex; justify-content: center; align-items: flex-end;
        pointer-events: none; 
        z-index: 999999; /* Siempre visible */
        padding-bottom: 10px;
    }}
    .worker-wrapper {{
        position: relative; display: flex; flex-direction: column; align-items: center;
    }}
    .led {{
        font-size: 40px; margin-bottom: -10px; z-index: 102; transition: all 0.5s ease;
    }}
    .robot-base {{ font-size: 120px; z-index: 101; }}
    
    /* Estados del LED */
    .led-on {{ text-shadow: 0 0 20px #00FF00; opacity: 1; filter: brightness(1.5); }}
    .led-off {{ filter: grayscale(100%) brightness(0.3); opacity: 0.5; }}
    
    /* Ocultar elementos extra */
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    </style>
    """, unsafe_allow_html=True)

# --- CARGAR FOOTER (ROBOT) ---
clase_css_led = f"led-{estado_led}"
st.markdown(f"""
    <div class="footer-container">
        <div class="worker-wrapper">
            <div class="led {clase_css_led}">🔋</div>
            <div class="robot-base">🤖</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- POP-UP ---
@st.dialog("📟 ANÁLISIS COMPLETADO", width="large")
def mostrar_popup(texto_resultado):
    st.markdown(texto_resultado)
    st.markdown("---")
    if st.button("Cerrar y Escanear Otra"):
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
    st.markdown('<div class="custom-title">🤖⚡ GSM ELECTRO-BOT ⚡🤖</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    input_clave = st.text_input("PROTOCOLO DE SEGURIDAD", type="password", placeholder="INTRODUCE CÓDIGO...", label_visibility="collapsed")
    
    if input_clave:
        if input_clave == "GSM":
            try:
                # Tu lógica de Secrets que funcionaba bien
                st.session_state.api_key = st.secrets["GOOGLE_API_KEY"]
                st.rerun()
            except:
                st.error("⚠️ Error: Configura los Secrets en Streamlit.")
        else: 
            st.error("⛔ ACCESO DENEGADO")

# 2. APP
else:
    st.markdown('<div class="custom-title">🤖⚡ GSM ELECTRO-BOT ⚡🤖</div>', unsafe_allow_html=True)
    
    try:
        genai.configure(api_key=st.session_state.api_key)
        if not st.session_state.modelo_usar: st.session_state.modelo_usar = conseguir_modelo_automatico()
        
        uploaded_file = st.file_uploader("📥 ALIMENTA AL ROBOT AQUÍ 📥", type=["pdf", "jpg", "png"])

        if uploaded_file is not None:
            if uploaded_file != st.session_state.ultimo_archivo:
                
                # ROBOT VOLADOR (Sustituye al cohete)
                placeholder_rocket = st.empty()
                placeholder_rocket.markdown("""
                    <div class="rocket-container"><div class="rocket-emoji">🤖</div></div>
                """, unsafe_allow_html=True)
                
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    myfile = genai.upload_file(tmp_path)

                    # TU PROMPT EXACTO (El que funciona)
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














