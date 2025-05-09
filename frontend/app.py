import pandas as pd
from supabase._async.client import AsyncClient as Client, create_client
import re
from datetime import datetime
import random
import streamlit as st
import asyncio
import os

def get_supabase_client() -> Client:
    # Leer desde variables de entorno
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def obtener_talleres_multimarca(talleres, shop_type_dict):
    ids_prioritarios = {
        "807bfd88-3f6a-4de4-8949-78dc615c288a",
        "08541ddf-ebf6-4653-adbb-7be30763da77",
        "9299ea34-037f-4d22-a2ba-344ca0e1af94",
        "19005d1f-612e-4e29-9265-f351fc9987bc" # SOFICAR
    }

    base = [
        t for t in talleres
        if shop_type_dict.get(t["mechanic_shop_type"]) in ['KPG-MULTIMARCA', 'CONVENIO-MULTIMARCA']
        and "PITS" not in t["name"]
    ]   

    prioritarios_presentes = [
        t for t in talleres
        if str(t.get("id")) in ids_prioritarios
    ]

    # Unir, priorizando, y eliminar duplicados manteniendo orden
    talleres_ordenados = []
    vistos = set()
    for t in prioritarios_presentes + base:
        t_id = str(t.get("id"))
        if t_id not in vistos:
            talleres_ordenados.append(t)
            vistos.add(t_id)

    return talleres_ordenados


def obtener_talleres_multimarca_kia(talleres, shop_type_dict):
    ids_prioritarios = {
        "6197a82b-1590-4d32-93de-3467f3e836a3" # SURMOTOR
    }

    base = [
        t for t in talleres
        if shop_type_dict.get(t["mechanic_shop_type"]) in ['KPG-MULTIMARCA', 'CONVENIO-MULTIMARCA']
        and "PITS" not in t["name"]
    ]   

    prioritarios_presentes = [
        t for t in talleres
        if str(t.get("id")) in ids_prioritarios
    ]

    # Unir, priorizando, y eliminar duplicados manteniendo orden
    talleres_ordenados = []
    vistos = set()
    for t in prioritarios_presentes + base:
        t_id = str(t.get("id"))
        if t_id not in vistos:
            talleres_ordenados.append(t)
            vistos.add(t_id)

    return talleres_ordenados


async def direccionar_taller(producto_auto, marca_vehiculo, anio_vehiculo, provincia, ciudad, supabase_client):
    
    anio_actual = datetime.now().year
    
    # 🚨 Regla: Si ProductoAuto contiene el patrón 'MOTO' en cualquier forma, no se puede realizar el direccionamiento
    if re.search(r'\bmotos\b', producto_auto, re.IGNORECASE):
        return {'message': 'No se puede realizar el direccionamiento para productos relacionados con motos.', 'mechanic_shop_list': []}
    
    # Obtener talleres desde Supabase filtrando por provincia y ciudad
    talleres_query = (
        supabase_client
        .from_("mechanic_shop")
        .select("*")
        .eq("province", provincia)
        .eq("city", ciudad)
        .eq("is_active", True)
        .is_("is_at_full_capacity", False)
        .order("capacity", desc=True)
    )

    talleres_response = await talleres_query.execute()

    talleres = talleres_response.data

    
    if not talleres:
        return  {'message': f"No existe talleres en esta ubicación {provincia} - {ciudad} para este vehículo en específico. Intente con otra ubicación.", 'mechanic_shop_list': []} 
    
    
    # Obtener tipos de talleres desde Supabase
    mechanic_shop_types_query = (
        supabase_client
        .from_("mechanic_shop_type")
        .select("id, name")
    )

    mechanic_shop_response = await mechanic_shop_types_query.execute()
    mechanic_shop_types = mechanic_shop_response.data
    
    shop_type_dict = {t["id"]: t["name"] for t in mechanic_shop_types}
    
    # Definir reglas específicas
    reglas_especificas = {
        "talleres_concesionario": [
            "AMERAFIN PERDIDA TOTAL SESA", "74 AIG - AUTOSEGURO SIO LIVIANOS", "75 AIG - AUTOSEGURO BPAC LIVIANOS",
            "78 AIG - AUTOSEGURO SIO PESADOS", "80 AIG - AMERAFIN BPAC PESADOS", "169 AIG - AUTOSEGURO SIO LIVIANOS SESA",
            "AIG - AUTOSEGURO BPAC LIVIANOS SESA", "171 AIG - AUTOSEGURO SIO PESADOS SESA", "172 AIG - AMERAFIN BPAC PESADOS SESA",
            "205 AIG - AUTOSEGURO SIO PLUS", "229 - BPAC - NOVAPACK CON AMPARO", "230 - BPAC - NOVAPACK SIN AMPARO",
            "244 AIG - AUTOSEGURO LOJA SIO PLUS", "277 AUTOSEGURO SIO PLUS NUEVOS", "352 BPAC 2024", "355 BPAC COMERCIAL 2024"
        ],
        "talleres_pits": ["UNINOVA 1-2", "UNINOVA 3-5", "UNINOVA 40", "UNINOVA VH COMERCIAL", "PRACTIAUTO"],
        "taller_szk": ["SUZUKI", "ALTON", "SUZUKI NUEVOS", "ALTON NUEVOS", "MIGRACION SUZUKI", "MIGRACION ALTON", "357 SUZUKI SEMI"],
        "taller_condelpi": ["AUTO CONDELPI", "AUTO CONDELPI 1", "POST RENTING", "CONDELPI-PIK-FUR", "CONDELPI-PESADOS", "RENTING - NESTLE"],
        "taller_ayasa": ["AYASA", "AYASA23", "AYASA23 MIG"],
        "taller_casabaca": ["1001 CARROS SEMINUEVOS", "ULTRA CASABACA", "ULTRA CASABACA NUEVOS", "NUEVOS 1001 CARROS", "MIGRACION CASABACA", "MIGRACIÓN 1001 CARROS"]
    }
    
    regla_aplicada = None
    talleres_especiales = []
    
    for regla, productos in reglas_especificas.items():
        if producto_auto in productos:
            regla_aplicada = regla
            print(f"Regla aplicada: {regla}")
            
            if regla == "talleres_concesionario" or regla == "taller_condelpi":
                talleres_especiales = [t for t in talleres if shop_type_dict.get(t["mechanic_shop_type"]) in ['KPG-CONCESIONARIO', 'CONVENIO-CONCESIONARIO']]
                # Obtener la marca solo para talleres concesionarios
                marca_query = (
                    supabase_client
                    .from_("vehicle_brand")
                    .select("id")
                    .eq("name", marca_vehiculo.lower())
                )
                marca_response = await marca_query.execute()
                marca_result = marca_response.data
                
                if not marca_result:
                    # print("No se encontró la marca")
                    talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                    talleres_complementarios = talleres_multimarca[:5]
                    
                    return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_complementarios} 
                
                marca_id = marca_result[0]["id"]
                talleres_ids = [t["id"] for t in talleres_especiales]

                
                talleres_marca_query = (
                    supabase_client
                    .from_("mechanic_shop_vehicle_brand")
                    .select("mechanic_shop_id")
                    .in_("mechanic_shop_id", talleres_ids)
                    .eq("vehicle_brand_id", marca_id)
                )
                
                talleres_marca_response = await talleres_marca_query.execute()


                if not talleres_marca_response.data:
                    print("No se encontró talleres_marca_response")
                    talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                    talleres_complementarios = talleres_multimarca[:5]
                    return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_complementarios} 

                talleres_marca_result = talleres_marca_response.data
                talleres_marca_ids = [t["mechanic_shop_id"] for t in talleres_marca_result]
                talleres_especiales = [t for t in talleres_especiales if t["id"] in talleres_marca_ids]
                
 

            elif regla == "talleres_pits":
                talleres_especiales = [t for t in talleres if shop_type_dict.get(t["mechanic_shop_type"]) == 'CONVENIO-MULTIMARCA' and "PITS" in t["name"]]
                
            else:
                patron = regla.replace("taller_", "").strip().lower()

                # Obtener nombres permitidos (en mayúsculas para comparación)
                permitidos = [n.upper() for n in reglas_especificas.get(regla, [])]

                # Buscar talleres que coincidan exactamente con los nombres permitidos
                talleres_exactos = [
                    t for t in talleres if t["name"].strip().upper() in permitidos
                ]

                # Si no se encuentran coincidencias exactas, usar coincidencia por patrón
                if talleres_exactos:
                    talleres_especiales = talleres_exactos
                else:
                    talleres_especiales = [
                        t for t in talleres if patron in t["name"].strip().lower()
                    ]
                
                marca_query = (
                        supabase_client
                        .from_("vehicle_brand")
                        .select("id")
                        .eq("name", marca_vehiculo.lower())
                    )
                marca_response = await marca_query.execute()
                marca_result = marca_response.data
                    
                if not marca_result:
                    talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                    talleres_complementarios = talleres_multimarca[:5]
                    
                    return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_complementarios} 
                    
                marca_id = marca_result[0]["id"]
                talleres_ids = [t["id"] for t in talleres_especiales]

                
                talleres_marca_query = (
                    supabase_client
                    .from_("mechanic_shop_vehicle_brand")
                    .select("mechanic_shop_id")
                    .in_("mechanic_shop_id", talleres_ids)
                    .eq("vehicle_brand_id", marca_id)
                )
                
                talleres_marca_response = await talleres_marca_query.execute()


                if not talleres_marca_response.data:
                    print("No se encontró talleres_marca_response")
                    talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                    talleres_complementarios = talleres_multimarca[:5] #random.sample(talleres_multimarca, min(len(talleres_multimarca), 5))
                    return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_complementarios} 

                talleres_marca_result = talleres_marca_response.data
                talleres_marca_ids = [t["mechanic_shop_id"] for t in talleres_marca_result]
                talleres_especiales = [t for t in talleres_especiales if t["id"] in talleres_marca_ids]

                
            if talleres_especiales:
                if len(talleres_especiales) <= 2:
                    talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                    talleres_complementarios = talleres_multimarca[:4] 
                    talleres_especiales += talleres_complementarios

                return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_especiales} 
            
#####################################################################################################################################################            
    
    if not talleres_especiales and regla_aplicada not in ["talleres_concesionario", "taller_condelpi"]:
        if anio_actual - anio_vehiculo <= 3:

            talleres_especiales = [t for t in talleres if shop_type_dict.get(t["mechanic_shop_type"]) in ['KPG-CONCESIONARIO', 'CONVENIO-CONCESIONARIO']]
            marca_query = (
                    supabase_client
                    .from_("vehicle_brand")
                    .select("id")
                    .eq("name", marca_vehiculo.lower())
                )
            marca_response = await marca_query.execute()
            marca_result = marca_response.data


            print(f"Marca regla de años: {marca_vehiculo.lower()}")
            
            if not marca_result:
                # print("No se encontró la marca")
                talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                talleres_complementarios = talleres_multimarca[:5] #random.sample(talleres_multimarca, min(len(talleres_multimarca), 5))
                return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_complementarios} 

            
            marca_id = marca_result[0]["id"]
            talleres_ids = [t["id"] for t in talleres_especiales]
            talleres_marca_query = (
                supabase_client
                .from_("mechanic_shop_vehicle_brand")
                .select("mechanic_shop_id")
                .in_("mechanic_shop_id", talleres_ids)
                .eq("vehicle_brand_id", marca_id)
            )
            
            talleres_marca_response = await talleres_marca_query.execute()

            if not talleres_marca_response.data:
                print("No se encontró talleres_marca_response")
                talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                talleres_complementarios = talleres_multimarca[:5] # random.sample(talleres_multimarca, min(len(talleres_multimarca), 5))
                return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_complementarios} 
            
            talleres_marca_result = talleres_marca_response.data
            talleres_marca_ids = [t["mechanic_shop_id"] for t in talleres_marca_result]
            talleres_especiales = [t for t in talleres_especiales if t["id"] in talleres_marca_ids]

            # Si hay talleres especiales
            if talleres_especiales:
                print("talleres_especiales_año")

                # Obtener talleres multimarca complementarios
                talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                talleres_complementarios = talleres_multimarca[:5]

                # Filtrar Metrocar S.A. si está presente
                metrocar = None
                for t in talleres_especiales + talleres_complementarios:
                    if t.get("name", "").strip().lower() == "metrocar s.a.":
                        metrocar = t
                        break

                # Combinar especiales + complementarios (sin duplicados exactos)
                talleres_combinados = talleres_especiales + [
                    t for t in talleres_complementarios if t not in talleres_especiales
                ]

                # Si Metrocar está, moverlo al inicio
                if metrocar and marca_vehiculo.lower() == "chevrolet":
                    talleres_combinados = [metrocar] + [t for t in talleres_combinados if t != metrocar]

                # Eliminar duplicados por dirección (solo el primero con esa address)
                talleres_filtrados = []
                direcciones_vistas = set()
                for t in talleres_combinados:
                    direccion = t.get("address", "").strip().lower()
                    if direccion not in direcciones_vistas:
                        talleres_filtrados.append(t)
                        direcciones_vistas.add(direccion)

                # Resultado final
                talleres_especiales = talleres_filtrados[:5]

            else:
                
                talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)
                talleres_complementarios = talleres_multimarca[:5] # random.sample(talleres_multimarca, min(len(talleres_multimarca), 3))
                talleres_especiales += talleres_complementarios
            
        else:
            print("Regla mayor a 3 años")
            if marca_vehiculo.lower() == "kia" and ciudad == "Quito":
                talleres_multimarca_kia = obtener_talleres_multimarca_kia(talleres, shop_type_dict)
                return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_multimarca_kia[:5]}
            
            talleres_multimarca = obtener_talleres_multimarca(talleres, shop_type_dict)

            # Eliminar duplicados por dirección (solo el primero con esa address)
            talleres_filtrados = []
            direcciones_vistas = set()
            for t in talleres_multimarca:
                direccion = t.get("address", "").strip().lower()
                if direccion not in direcciones_vistas:
                    talleres_filtrados.append(t)
                    direcciones_vistas.add(direccion)

            # Resultado final: máximo 5 talleres
            talleres_especiales = talleres_filtrados[:5]

                        
        return {'message': f"Lista de talleres en esta ubicación {provincia} - {ciudad} fue encontrada con éxito.", 'mechanic_shop_list': talleres_especiales} 


    
async def buscar_talleres_async(producto_auto, marca_vehiculo, anio_vehiculo, provincia, ciudad):
    supabase_client = await get_supabase_client()
    return await direccionar_taller(producto_auto, marca_vehiculo, anio_vehiculo, provincia, ciudad, supabase_client)

# Streamlit UI
st.title("Dirección de Talleres")

# Entrada de datos
producto_auto = st.text_input("Producto Auto", value="FULL COBERTURA")
marca_vehiculo = st.text_input("Marca del Vehículo", value="CHEVROLET")
anio_vehiculo = st.number_input("Año del Vehículo", min_value=1900, max_value=datetime.now().year, value=2022)
provincia = st.text_input("Provincia", value="Pichincha")
ciudad = st.text_input("Ciudad", value="Quito")

if st.button("Buscar Talleres"):
    resultado = asyncio.run(buscar_talleres_async(producto_auto, marca_vehiculo, anio_vehiculo, provincia, ciudad))

    print(resultado["message"])
    
    talleres = resultado.get("mechanic_shop_list", [])

    if not talleres:
        st.warning("No se encontraron talleres para los criterios ingresados.")
    else:
        st.write("Talleres encontrados:")
        df = pd.DataFrame(talleres)
        columnas_a_mostrar = ["name", "city", "address", "responsable_name", "phone", "email"]
        st.dataframe(df[columnas_a_mostrar])