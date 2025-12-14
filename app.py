import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="EME Wealth Objetive",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS (NATURAL LUXURY) ---
st.markdown("""
<style>
    /* Importar fuente elegante si es posible, o usar sistema */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Sidebar High Contrast */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA; /* Blanco humo muy claro */
        border-right: 1px solid #E5E7EB;
    }
    
    /* Forzar color de texto oscuro en sidebar */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {
        color: #111827 !important; /* Gris muy oscuro, casi negro */
        font-weight: 500;
    }
    
    /* Inputs en sidebar */
    [data-testid="stSidebar"] input {
        color: #111827 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
    }

    /* Fondo limpio y minimalista principal */
    .stApp {
        background-color: #FFFFFF; 
        color: #111827;
    }

    /* Títulos */
    h1, h2, h3 {
        color: #111827 !important;
        font-weight: 700;
    }
    
    /* KPI Cards Custom */
    div.stMetric {
        background-color: #F3F4F6; /* Gris suave contraste */
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 15px;
        color: #111827;
    }
    
    label {
        color: #374151 !important; /* Gris oscuro para labels generales */
    }
    
    /* Botones */
    .stButton>button {
        background-color: #2C3E50;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #34495E;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE CÁLCULO FINANCIERO ---

def calcular_valor_futuro(present_value, monthly_contribution, years, annual_rate):
    """Calcula el valor futuro dado un PV, aportación mensual, años y tasa."""
    months = years * 12
    monthly_rate = annual_rate / 12
    
    # FV del principal inicial
    fv_principal = present_value * (1 + monthly_rate) ** months
    
    # FV de las aportaciones mensuales (Anualidad)
    # Formula FV = PMT * (((1 + r)^n - 1) / r)
    if monthly_rate > 0:
        fv_contributions = monthly_contribution * (((1 + monthly_rate) ** months - 1) / monthly_rate)
    else:
        fv_contributions = monthly_contribution * months
        
    return fv_principal + fv_contributions

def calcular_cagr_necesario(present_value, target_value, years, monthly_contribution):
    """
    Calcula la tasa anual necesaria (CAGR) para llegar del PV al Target,
    considerando aportaciones mensuales.
    Usa numpy_financial.rate: rate(nper, pmt, pv, fv)
    """
    months = years * 12
    # Nota: pmt y pv suelen ser negativos en finanzas (cash outflows), fv positivo.
    # Aquí asumimos que PV es dinero que ya tienes (negativo desde la vista del flujo del contrato)
    # y PMT son pagos (negativos).
    
    try:
        monthly_rate = npf.rate(nper=months, pmt=-monthly_contribution, pv=-present_value, fv=target_value)
        # Convertir a anual
        if monthly_rate is None or np.isnan(monthly_rate):
            return None
        annual_rate = (1 + monthly_rate) ** 12 - 1
        return annual_rate
    except Exception:
        return None

def calcular_aportacion_necesaria(present_value, target_value, years, annual_rate_fixed):
    """
    Calcula la aportación mensual necesaria dado un retorno fijo.
    Usa numpy_financial.pmt: pmt(rate, nper, pv, fv)
    """
    months = years * 12
    monthly_rate = annual_rate_fixed / 12
    
    try:
        monthly_pmt = npf.pmt(rate=monthly_rate, nper=months, pv=-present_value, fv=target_value)
        # El resultado suele ser negativo (lo que debes pagar), lo pasamos a positivo
        return abs(monthly_pmt)
    except:
        return None

def generar_pdf(data_resumen, df_proyeccion):
    """
    Genera un informe PDF con FPDF.
    data_resumen: dicc con claves 'cliente', 'objetivo', 'patrimonio_actual', 'estrategia', etc.
    df_proyeccion: dataframe con la tabla año a año de los primeros 5 y último.
    """
    class PDF(FPDF):
        def header(self):
            # Título simple
            self.set_font('Helvetica', 'B', 16)
            self.cell(0, 10, 'Informe EME Wealth Objetive', 0, 1, 'C')
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # 1. Resumen Situación
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "1. Resumen de Situación", 0, 1, 'L')
    pdf.set_font("Helvetica", size=11)
    
    pdf.cell(50, 8, f"Patrimonio Actual:", 0, 0)
    pdf.cell(0, 8, f"{data_resumen['patrimonio_actual']}", 0, 1)
    
    pdf.cell(50, 8, f"Objetivo Financiero:", 0, 0)
    pdf.cell(0, 8, f"{data_resumen['objetivo_valor']} en {data_resumen['horizonte']} años", 0, 1)
    
    pdf.cell(50, 8, f"Inflación Estimada:", 0, 0)
    pdf.cell(0, 8, f"{data_resumen['inflacion']}", 0, 1)
    pdf.ln(5)

    # 2. Hoja de Ruta (Resultados)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "2. Hoja de Ruta - Escenarios", 0, 1, 'L')
    pdf.set_font("Helvetica", size=11)

    pdf.cell(0, 8, "Escenario A: Rentabilidad Requerida", 0, 1)
    pdf.set_font("Helvetica", '', 11)
    pdf.multi_cell(0, 6, f"Para alcanzar {data_resumen['objetivo_valor']} manteniendo su ahorro actual de {data_resumen['ahorro_actual']}, sus inversiones deben generar un retorno anual compuesto (CAGR) de: {data_resumen['cagr_necesario']}")
    pdf.ln(3)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, "Escenario B: Esfuerzo de Ahorro", 0, 1)
    pdf.set_font("Helvetica", '', 11)
    pdf.multi_cell(0, 6, f"Si asumimos una rentabilidad fija del {data_resumen['rentabilidad_fija']}, debería aumentar su ahorro mensual a: {data_resumen['ahorro_necesario']} (Gap: {data_resumen['gap_ahorro']})")
    pdf.ln(10)

    # 3. Proyección Tabla Temprana
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "3. Proyección Patrimonial (Primeros Años y Final)", 0, 1, 'L')
    pdf.set_font("Helvetica", size=10)
    
    # Cabecera tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(20, 8, "Año", 1, 0, 'C', 1)
    pdf.cell(50, 8, "Patrimonio Proyectado", 1, 0, 'C', 1)
    pdf.cell(50, 8, "Aportado Acumulado", 1, 1, 'C', 1) # Salto de linea
    
    # Filas
    for index, row in df_proyeccion.iterrows():
        year_lbl = str(int(row['Año']))
        patrimonio = f"{row['Patrimonio']:,.0f} €"
        aportado = f"{row['Total Aportado']:,.0f} €" if 'Total Aportado' in row else "-"
        
        pdf.cell(20, 8, year_lbl, 1, 0, 'C')
        pdf.cell(50, 8, patrimonio, 1, 0, 'R')
        pdf.cell(50, 8, aportado, 1, 1, 'R')

    return pdf

# --- MAIN APP LOGIC ---

def main():
    st.title("EME Wealth Objetive")
    st.markdown("Planificador de patrimonio y viabilidad financiera.")

    # --- SIDEBAR: INPUT DATOS ---
    with st.sidebar:
        st.header("1. Situación Actual")
        
        input_mode = st.radio("Método de Entrada", ["Manual", "Carga CSV (Kubera)"], index=0)
        
        patrimonio_inicial = 0.0
        
        if input_mode == "Manual":
            patrimonio_inicial = st.number_input("Patrimonio Neto Actual (€)", min_value=0.0, value=100000.0, step=1000.0, format="%.2f")
            
        else: # CSV Mode
            uploaded_file = st.file_uploader("Subir CSV de Activos", type=['csv'])
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.write("Vista previa:", df.head(3))
                    
                    # Detección de columnas
                    cols = df.columns.tolist()
                    col_asset = next((c for c in cols if "Asset" in c or "Name" in c), cols[0])
                    col_value = next((c for c in cols if "Value" in c or "Balance" in c or "Valor" in c), cols[1])
                    
                    c1, c2 = st.columns(2)
                    asset_col_sel = c1.selectbox("Columna Activo", cols, index=cols.index(col_asset))
                    val_col_sel = c2.selectbox("Columna Valor", cols, index=cols.index(col_value))
                    
                    # Limpieza y suma
                    # Asumimos que el valor puede venir con simbolos de moneda
                    try:
                        # Eliminar caracteres no numericos excepto punto y menos
                        df[val_col_sel] = df[val_col_sel].replace(r'[^\d.-]', '', regex=True).astype(float)
                        patrimonio_inicial = df[val_col_sel].sum()
                        st.success(f"Patrimonio Total Detectado: {patrimonio_inicial:,.2f} €")
                    except Exception as e:
                        st.error(f"Error parseando valores: {e}")
                except Exception as e:
                    st.error(f"No se pudo leer el CSV: {e}")
        
        st.divider()
        
        st.header("2. El Objetivo de Vida")
        
        # Paso 1: Definición Cualitativa
        goal_name = st.text_input("Nombre del Objetivo", value="Libertad Financiera", placeholder="Ej. Jubilación en la Playa")
        
        # Paso 2: El Coste de Vida
        st.subheader("¿Cuánto cuesta tu vida ideal?")
        gasto_mensual_deseado = st.number_input("Gasto Mensual Deseado (€)", min_value=500.0, value=3000.0, step=100.0)
        
        # Paso 3: Rentabilidad (Regla del 4% o personalizada)
        st.subheader("Rentabilidad del Capital")
        tasa_retirada_segura = st.slider("Rentabilidad Estimada de Distribución (%)", min_value=1.0, max_value=8.0, value=4.0, step=0.1, help="Regla general: 4% es conservador/estándar.")
        
        # CÁLCULO DEL NÚMERO DE LIBERTAD (Target Wealth)
        gasto_anual = gasto_mensual_deseado * 12
        objetivo_patrimonial = gasto_anual / (tasa_retirada_segura / 100.0)
        
        st.markdown(f"""
        <div style="background-color: #E8F8F5; padding: 10px; border-radius: 5px; border-left: 5px solid #1ABC9C;">
            <small>Patrimonio Necesario (Calculado)</small>
            <h3 style="margin:0; color: #16A085;">{objetivo_patrimonial:,.0f} €</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()

        horizonte_temporal = st.slider("Horizonte (Años)", min_value=1, max_value=50, value=20)
        
        aportacion_actual = st.number_input("Aportación Mensual Actual (€)", min_value=0.0, value=1000.0, step=100.0)
        inflacion = st.slider("Inflación Estimada (%) - Ajuste visual", min_value=0.0, max_value=10.0, value=2.5, step=0.1)

        st.divider()
        st.header("Parámetros Cálculo")
        rentabilidad_fija_ref = st.number_input("Ref. Rentabilidad Fija (%) para calculo de Ahorro", min_value=0.0, max_value=20.0, value=7.0, step=0.5)

    # --- CÁLCULOS ---
    
    # 1. Escenario Rentabilidad Necesaria
    # Incógnita: Tasa
    cagr_necesario = calcular_cagr_necesario(patrimonio_inicial, objetivo_patrimonial, horizonte_temporal, aportacion_actual)
    
    # 2. Escenario Ahorro Necesario
    # Incógnita: PMT, dado una tasa fija (ej. 7% o lo que puso el usuario)
    rentabilidad_fija_decimal = rentabilidad_fija_ref / 100.0
    ahorro_necesario_mensual = calcular_aportacion_necesaria(patrimonio_inicial, objetivo_patrimonial, horizonte_temporal, rentabilidad_fija_decimal)
    gap_ahorro = ahorro_necesario_mensual - aportacion_actual if ahorro_necesario_mensual else 0

    # --- DASHBOARD PRINCIPAL ---
    
    # KPI ROW
    st.subheader(f"Análisis: {goal_name}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if cagr_necesario is not None:
            cagr_display = cagr_necesario * 100
            diff_ref = cagr_display - rentabilidad_fija_ref
            st.metric(label="Rentabilidad Anual Necesaria", value=f"{cagr_display:.2f}%", delta=f"{diff_ref:.2f}% vs Ref", delta_color="inverse")
        else:
            st.metric(label="Rentabilidad Anual Necesaria", value="Inviable")
            st.caption("Con los parámetros actuales es imposible matemáticamente.")

    with col2:
        if ahorro_necesario_mensual is not None:
            st.metric(label="Ahorro Mensual Ideal (al 7%)", value=f"{ahorro_necesario_mensual:,.0f} €", delta=f"-{gap_ahorro:,.0f} € Gap", delta_color="normal")
        else:
            st.metric(label="Ahorro Mensual Ideal", value="N/A")

    with col3:
        # Proyección final con estrategia actual Y retorno referencia
        final_con_ref = calcular_valor_futuro(patrimonio_inicial, aportacion_actual, horizonte_temporal, rentabilidad_fija_decimal)
        deficit = final_con_ref - objetivo_patrimonial
        st.metric(label=f"Proyección Final (al {rentabilidad_fija_ref}%)", value=f"{final_con_ref:,.0f} €", delta=f"{deficit:,.0f} € vs Objetivo")


    # --- GRÁFICOS ---
    st.markdown("### Proyección Patrimonial")
    
    # Generar datos año a año para gráfico
    years_axis = list(range(horizonte_temporal + 1))
    
    # Serie A: Estrategia Actual (usando la tasa de referencia fija como "lo que pasaría normalmente")
    # O podríamos usar una tasa conservadora del 3%. Usaremos la referencia del usuario (7%) como "Baseline de mercado"
    serie_mercado = []
    
    # Serie B: Objetivo (Linea recta exponencial o la que cumple el CAGR necesario)
    serie_objetivo = []
    
    # Serie C: Solo Ahorro (sin interes) para ver impacto compuesto
    serie_cash = []
    
    for y in years_axis:
        # Mercado
        val_mercado = calcular_valor_futuro(patrimonio_inicial, aportacion_actual, y, rentabilidad_fija_decimal)
        serie_mercado.append(val_mercado)
        
        # Objetivo (usamos el CAGR, si existe, si no, es NaN)
        if cagr_necesario:
            val_obj = calcular_valor_futuro(patrimonio_inicial, aportacion_actual, y, cagr_necesario)
            serie_objetivo.append(val_obj)
        else:
            serie_objetivo.append(objetivo_patrimonial) # Fallback visual plano
            
        # Cash acumulado (Colchón)
        val_cash = patrimonio_inicial + (aportacion_actual * 12 * y)
        serie_cash.append(val_cash)

    fig = go.Figure()
    
    # Linea Objetivo
    fig.add_trace(go.Scatter(x=years_axis, y=serie_objetivo, mode='lines', name=f'Senda {goal_name} (Ideal)',
                             line=dict(color='#27AE60', width=3, dash='dash'))) # Verde EME
    
    # Linea Mercado/Actual
    fig.add_trace(go.Scatter(x=years_axis, y=serie_mercado, mode='lines+markers', name=f'Proyección Actual ({rentabilidad_fija_ref}%)',
                             line=dict(color='#2980B9', width=3)))
    
    # Linea Cash
    fig.add_trace(go.Scatter(x=years_axis, y=serie_cash, mode='lines', name='Solo Ahorro (Sin Inversión)',
                             line=dict(color='#95A5A6', width=2), fill='tozeroy', fillcolor='rgba(149, 165, 166, 0.1)'))
    
    # Linea Meta Horizontal
    fig.add_hline(y=objetivo_patrimonial, line_dash="dot", annotation_text=f"Objetivo: {objetivo_patrimonial/1000000:.1f}M€", annotation_position="top right", line_color="#E74C3C")

    fig.update_layout(
        title="Evolución del Patrimonio Neto",
        xaxis_title="Años Proyectados",
        yaxis_title="Patrimonio (€)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, use_container_width=True)


    # --- EXPORTAR PDF ---
    st.divider()
    
    # Preparar datos para reporte
    col_pdf, _ = st.columns([1, 4])
    with col_pdf:
        if st.button("📄 Exportar Objetive EME (PDF)"):
            # Datos resumen
            data_resumen = {
                'patrimonio_actual': f"{patrimonio_inicial:,.2f} €",
                'objetivo_valor': f"{objetivo_patrimonial:,.2f} €",
                'horizonte': horizonte_temporal,
                'inflacion': f"{inflacion}%",
                'ahorro_actual': f"{aportacion_actual:,.2f} €/mes",
                'cagr_necesario': f"{cagr_necesario*100:.2f}%" if cagr_necesario else "Inviable",
                'rentabilidad_fija': f"{rentabilidad_fija_ref}%",
                'ahorro_necesario': f"{ahorro_necesario_mensual:,.2f} €/mes" if ahorro_necesario_mensual else "N/A",
                'gap_ahorro': f"{gap_ahorro:,.2f} €"
            }
            
            # DF reducido para la tabla (Años 0, 1, 2, 3, 4, 5 y Final)
            indices_to_show = [i for i in range(len(years_axis)) if i <= 5 or i == len(years_axis)-1]
            df_export = pd.DataFrame({
                "Año": [2024 + y for y in list(np.array(years_axis)[indices_to_show])], # Asumiendo año base 2024
                "Patrimonio": list(np.array(serie_objetivo)[indices_to_show]),
                "Total Aportado": list(np.array(serie_cash)[indices_to_show])
            })
            
            pdf = generar_pdf(data_resumen, df_export)
            
            # Output PDF to bytes
            # FPDF output to string is default, for bytes we use output(dest='S').encode('latin-1') in older versions
            # Or simplified approach for fpdf2:
            try:
                # FPDF2
                pdf_bytes = pdf.output(dest='S') # Returns bytes in FPDF2 if defaults? Actually returns bytearray usually or string.
                # Let's use a safer approach for FPDF (bytearray)
                if isinstance(pdf_bytes, str):
                    pdf_bytes = pdf_bytes.encode('latin-1')
            except:
                # FPDF 1.7 style fallback
                pdf_bytes = pdf.output(dest='S').encode('latin-1')

            st.download_button(
                label="Descargar PDF",
                data=pdf_bytes,
                file_name="eme_wealth_objetive_report.pdf",
                mime="application/pdf"
            )

    # Footer
    st.markdown("---")
    st.caption("EME Wealth Objetive v1.0 | Calculations are estimates based on constant compounding.")

if __name__ == "__main__":
    main()
