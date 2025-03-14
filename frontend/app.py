import streamlit as st
import pandas as pd
import re
from datetime import datetime

def direccionar_taller(producto_auto, marca_vehiculo, anio_vehiculo, provincia, ciudad):
    anio_actual = datetime.now().year
    talleres_df = pd.read_excel("talleres.xlsx")


    # Convertir entradas a minúsculas
    producto_auto = producto_auto.lower()
    marca_vehiculo = marca_vehiculo.lower()
    provincia = provincia.lower()
    ciudad = ciudad.lower()
    
    # 🚨 Regla: Si ProductoAuto contiene el patrón 'MOTO' en cualquier forma, no se puede realizar el direccionamiento
    if re.search(r'\bmotos\b', producto_auto, re.IGNORECASE):
        return "No se puede realizar el direccionamiento para productos relacionados con motos."
    
    # 1️⃣ Filtrar por provincia y ciudad

    talleres_df['PROVINCIA'] = talleres_df['PROVINCIA'].str.lower()
    talleres_df['CIUDAD'] = talleres_df['CIUDAD'].str.lower()
    
    talleres_filtrados = talleres_df[(talleres_df['PROVINCIA'] == provincia) & 
                                     (talleres_df['CIUDAD'] == ciudad)]
    
    # 2️⃣ Verificar si el ProductoAuto coincide con reglas específicas
    reglas_especificas = {
        "talleres_concesionario": [
            "AMERAFIN PERDIDA TOTAL SESA", "74 AIG - AUTOSEGURO SIO LIVIANOS", "75 AIG - AUTOSEGURO BPAC LIVIANOS",
            "78 AIG - AUTOSEGURO SIO PESADOS", "80 AIG - AMERAFIN BPAC PESADOS", "169 AIG - AUTOSEGURO SIO LIVIANOS SESA",
            "AIG - AUTOSEGURO BPAC LIVIANOS SESA", "171 AIG - AUTOSEGURO SIO PESADOS SESA", "172 AIG - AMERAFIN BPAC PESADOS SESA",
            "205 AIG - AUTOSEGURO SIO PLUS", "229 - BPAC - NOVAPACK CON AMPARO", "230 - BPAC - NOVAPACK SIN AMPARO",
            "244 AIG - AUTOSEGURO LOJA SIO PLUS", "277 AUTOSEGURO SIO PLUS NUEVOS", "352 BPAC 2024", "355 BPAC COMERCIAL 2024"
        ],
        "talleres_pits": ["UNINOVA 1-2", "UNINOVA 3-5", "UNINOVA 40", "UNINOVA VH COMERCIAL", "PRACTIAUTO"],
        "taller_sz": ["SUZUKI", "ALTON", "SUZUKI NUEVOS", "ALTON NUEVOS", "MIGRACION SUZUKI", "MIGRACION ALTON", "357 SUZUKI SEMI"],
        "taller_condelpi": ["AUTO CONDELPI", "AUTO CONDELPI 1", "POST RENTING", "CONDELPI-PIK-FUR", "CONDELPI-PESADOS", "RENTING - NESTLE"],
        "taller_ayasa": ["AYASA", "AYASA23", "AYASA23 MIG"],
        "taller_casabaca": ["1001 CARROS SEMINUEVOS", "ULTRA CASABACA", "ULTRA CASABACA NUEVOS", "NUEVOS 1001 CARROS", "MIGRACION CASABACA", "MIGRACIÓN 1001 CARROS"]
    }

    talleres_especiales = pd.DataFrame()
    regla_aplicada = None
    
    for regla, productos in reglas_especificas.items():
        if producto_auto in [p.lower() for p in productos]:
            regla_aplicada = regla
            print(f"Regla aplicada: {regla}")
            
            # Aplicar filtro según tipo de regla
            if regla == "talleres_concesionario" or regla == "taller_condelpi":
                talleres_especiales = talleres_filtrados[talleres_filtrados['TIPO TALLER'].isin(['KPG - Concesionario', 'Convenio - Concesionario'])]
                talleres_especiales = talleres_especiales[talleres_especiales['FABRICANTE'].str.lower().str.contains(marca_vehiculo, na=False)]
            elif regla == "talleres_pits":
                talleres_especiales = talleres_filtrados[(talleres_filtrados['TIPO TALLER'] == 'Convenio - Multimarca') & 
                                                         (talleres_filtrados['NOMBRE COMERCIAL'].str.contains("PITS", na=False))]
            else:
                talleres_especiales = talleres_filtrados[talleres_filtrados['NOMBRE COMERCIAL'].str.contains(regla.replace("taller_", ""), na=False, case=False)]
                # Filtrar por marca de vehículo si no es un taller multimarca PITS
                talleres_especiales = talleres_especiales[talleres_especiales['FABRICANTE'].str.lower().str.contains(marca_vehiculo, na=False)]


            if not talleres_especiales.empty:

                if len(talleres_especiales) < 2:
                    talleres_multimarca = talleres_df[
                        (talleres_df['PROVINCIA'] == provincia) &
                        (talleres_df['CIUDAD'] == ciudad) &
                        (talleres_df['TIPO TALLER'].isin(['KPG - Multimarca', 'Convenio - Multimarca'])) &
                        (~talleres_df['NOMBRE COMERCIAL'].str.contains('PITS', na=False))
                    ]

                    # Seleccionar hasta 3 talleres multimarca adicionales
                    talleres_complementarios = talleres_multimarca.head(5 - len(talleres_especiales))
                    
                    # Unir los talleres especiales con los talleres multimarca adicionales
                    talleres_especiales = pd.concat([talleres_especiales, talleres_complementarios])

                
                return talleres_especiales[["NOMBRE COMERCIAL", "FABRICANTE", "TIPO TALLER", "PROVINCIA", "CIUDAD", "DIRECCIÓN"]]
    
    # 3️⃣ Si talleres_especiales está vacío y no es una regla de concesionario, aplicar regla de edad del vehículo
    if talleres_especiales.empty and regla_aplicada not in ["talleres_concesionario", "taller_condelpi"]:
        if anio_actual - anio_vehiculo <= 3:
            talleres_filtrados = talleres_filtrados[talleres_filtrados['TIPO TALLER'].isin(['KPG - Concesionario', 'Convenio - Concesionario'])]
            # Aplicar filtro por marca de vehículo
            talleres_filtrados = talleres_filtrados[talleres_filtrados['FABRICANTE'].str.lower().str.contains(marca_vehiculo, na=False)]


            if len(talleres_filtrados) < 2: 
                talleres_multimarca = talleres_df[
                    (talleres_df['PROVINCIA'] == provincia) &
                    (talleres_df['CIUDAD'] == ciudad) &
                    (talleres_df['TIPO TALLER'].isin(['KPG - Multimarca', 'Convenio - Multimarca'])) &
                    (~talleres_df['NOMBRE COMERCIAL'].str.contains('PITS', na=False))
                ]  

                # Seleccionar hasta 3 talleres multimarca adicionales
                talleres_complementarios = talleres_multimarca.head(5 - len(talleres_filtrados))
                    
                # Unir los talleres especiales con los talleres multimarca adicionales
                talleres_filtrados = pd.concat([talleres_filtrados, talleres_complementarios])
            
        else:
            talleres_filtrados = talleres_filtrados[talleres_filtrados['TIPO TALLER'].isin(['KPG - Multimarca', 'Convenio - Multimarca'])]
            talleres_filtrados = talleres_filtrados[~talleres_filtrados['NOMBRE COMERCIAL'].str.contains('PITS', na=False)]
        
        if not talleres_filtrados.empty:
            return talleres_filtrados[["NOMBRE COMERCIAL", "FABRICANTE", "TIPO TALLER", "PROVINCIA", "CIUDAD", "DIRECCIÓN"]]
    
    # 4️⃣ Si aún no hay coincidencias, devolver mensaje indicando que no existen talleres para este vehículo
    return f"No existe talleres en esta ubicación {provincia} - {ciudad} para este vehículo en específico. Intente con otra ubicación."

# Streamlit UI
st.title("Dirección de Talleres")
    
# Entrada de datos
producto_auto = st.text_input("Producto Auto")
marca_vehiculo = st.text_input("Marca del Vehículo")
anio_vehiculo = st.number_input("Año del Vehículo", min_value=1900, max_value=datetime.now().year, value=2022)
provincia = st.text_input("Provincia")
ciudad = st.text_input("Ciudad")

if st.button("Buscar Talleres"):
    resultado = direccionar_taller(producto_auto, marca_vehiculo, anio_vehiculo, provincia, ciudad)
    
    if isinstance(resultado, pd.DataFrame):
        st.write("Talleres encontrados:")
        st.dataframe(resultado)
    else:
        st.warning(resultado)
