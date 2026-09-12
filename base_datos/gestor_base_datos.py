import sys
import math
import pandas as pd 
from logica.instanciadores import (Barra, Generador, Carga, LineaTrx, Fallas3f)
from logica.estructura_sep import SistemaPotencia
#===============================================================================
#           FUNCIONES ENCARGADA DE LA LECTURA Y LIMPIEZA DE DATOS
#===============================================================================
def leer_hojas_excel(xls:pd.ExcelFile, hoja:str) -> pd.DataFrame:
    """
    Lee los archivos Excels y quita la informacion que no sirve en las tablas
    para que sea mas facil de trabajar
    """
    #LECTURA DE LAS HOJAS
    df = xls.parse(sheet_name=hoja, header=1, index_col=0)
    #LIMPIEZA DE LOS ENCABEZADOS
    df.columns = (
        df.columns.astype(str)
        .str.replace('\n', ' ')  
        .str.strip()
    )
    #ELIMINADO DE LAS FILAS VACIAS
    df = df[df.iloc[:,1].notna()]
    df = df.astype(object).where(pd.notna(df), None)
    return df

#===============================================================================
#       FUNCIONES ENCARGADAS DE INSTANCIAR LOS ELEMENTOS DEL SEP
#===============================================================================
def obtener_frecuencia(xls:pd.ExcelFile):
    df = leer_hojas_excel(xls,"DESCRIPCION")
    valor = df.iloc[1, 1]
    return float(str(valor)) if valor is not None else 60.0

def objeto_barra(xls:pd.ExcelFile):
    """
    Crea una instancia de la clase Barra para cada bus del sistema
    """
    #DDECLARACIÓN DE VARIABLES Y LECTURA DE LAS HOJAS DEL EXCEL
    barras = {}
    tabla_barras = leer_hojas_excel(xls,"BARRAS")
    for fila in tabla_barras.to_dict("records"):
        inst_barra = Barra(
            id_barra=fila["ID"],
            tipo = fila["TIPO"],
            P_gen = fila["P GENERADA"],
            Q_gen = fila["Q GENERADA"],
            P_dem = fila["P DEMANDADA"],
            Q_dem = fila["Q DEMANDADA"],
            v_mag = fila["V MAGNITUD"],
            v_ang = fila["V ANGULO"],
            barra_inf=False if fila["BARRA INFINITA"].strip().upper()=="NO" 
            else True
        )
        barras[fila["ID"]] = inst_barra
    return barras


def objeto_generador(xls:pd.ExcelFile):
    """
    Crea una instancia de la clase Generador para cada bus del sistema
    """
    generadores = {}
    tabla_generadores = leer_hojas_excel(xls,"GENERADORES")
    for fila in tabla_generadores.to_dict("records"):
        inst_generador = Generador(
            id_gen = fila["ID GENERADOR"],
            id_barra = fila["ID BARRA"],
            Ra = fila["Ra"],
            Xd_prima = fila["Xd PRIMA"],
            H = fila["H"],
            slack = False if fila["SLACK"].strip().upper() == "NO" else True
        )
        generadores[fila["ID GENERADOR"]] = inst_generador
    return generadores

def objeto_carga(xls:pd.ExcelFile):
    """
    Crea una instancia de la clase Carga para cada bus del sistema
    """
    cargas = {}
    tabla_cargas = leer_hojas_excel(xls,"CARGAS")
    for fila in tabla_cargas.to_dict("records"):
        inst_carga = Carga(
            id_carga=fila["ID CARGA"],
            id_barra=fila["ID BARRA"],
            P_mag=fila["P DEMANDADA"],
            Q_mag=fila["Q DEMANDADA"]
        )
        cargas[fila["ID CARGA"]] = inst_carga
    return cargas

def objeto_lineas_trx(xls:pd.ExcelFile):
    """
    Crea una instancia de la clase LineaTrx para cada bus del sistema
    """
    lineas_trxs = {}
    tabla_lineas_trx = leer_hojas_excel(xls,"LINEAS Y TRX's")
    for fila in tabla_lineas_trx.to_dict("records"):
        
        # --- LIMPIEZA DE COMAS A PUNTO DECIMAL ---
        r_str = str(fila.get("R", 0)).replace(',', '.')
        x_str = str(fila.get("X", 0)).replace(',', '.')
        b_str = str(fila.get("B", 0)).replace(',', '.')
        g_str = str(fila.get("G", 0)).replace(',', '.')
        bs_str = str(fila.get("B_SERIE", 0)).replace(',', '.')

        r = float(r_str) if r_str and r_str.upper() != 'NONE' else 0.0
        x = float(x_str) if x_str and x_str.upper() != 'NONE' else 0.0
        b_shunt = float(b_str) if b_str and b_str.upper() != 'NONE' else 0.0
        g = float(g_str) if g_str and g_str.upper() != 'NONE' else 0.0
        b_serie = float(bs_str) if bs_str and bs_str.upper() != 'NONE' else 0.0
        # ----------------------------------------

        inst_linea_trx = LineaTrx(
            id_linea = fila["ID LINEA"],
            id_barra_i = fila["BARRA I"],
            id_barra_j = fila["BARRA J"],
            R_value = r,
            X_value = x,
            B_shunt = b_shunt,
            G_value = g,
            B_serie_value = b_serie
        )
        lineas_trxs[fila["ID LINEA"]] = inst_linea_trx
    return lineas_trxs

def objeto_fallas(xls: pd.ExcelFile):
    """
    Crea una instancia de la clase Fallas3f para las perturbaciones del sistema
    """
    fallas = {}
    try:
        tabla_fallas = leer_hojas_excel(xls, "PARÁMETROS DE FALLA 3F")
        for fila in tabla_fallas.to_dict("records"):
            id_falla = str(fila.get("ID FALLA")).strip()
            
            # Limpieza de datos
            z_f_val = fila.get("IMPEDANCIA FALLA")
            z_falla = 1e-6 if pd.isna(z_f_val) or str(z_f_val).strip().upper() == 'NULL' else complex(z_f_val)
            
            b_j = fila.get("BARRA J")
            b_j = int(b_j) if pd.notna(b_j) and str(b_j).strip().upper() != 'NULL' else None
            
            porc = fila.get("PORCENTAJE LÍNEA")
            porc = float(porc) if pd.notna(porc) and str(porc).strip().upper() != 'NULL' else None
            
            b_falla = fila.get("BARRA FALLA")
            b_falla = int(b_falla) if pd.notna(b_falla) and str(b_falla).strip().upper() != 'NULL' else None
            
            # Instanciar falla
            dur_val = fila.get("DURACION")
            tdspj_val = fila.get("TIEMPO DESPEJE")
            bi_val = fila.get("BARRA I")
            id_val = fila.get("ID LINEA")
            comp_val = fila.get("ELEMENTO A FALLAR")

            inst_falla = Fallas3f(
                id_linea=str(id_val).strip() if id_val is not None else "",
                duracion=float(dur_val) if dur_val is not None else 0.0,
                t_dspj=float(tdspj_val) if tdspj_val is not None else 0.0,
                comp_falla=str(comp_val).strip() if comp_val is not None else "",
                barra_i=int(bi_val) if bi_val is not None else 0,
                barra_j=b_j,
                porc_linea=porc,
                Z_f=z_falla,
                barra_falla=b_falla
            )
            fallas[id_falla] = inst_falla
    except Exception as e:
        print(f"Error interno leyendo fallas: {e}") # Si no hay hoja de fallas, simplemente lo ignora
        
    return fallas

#===============================================================================
#                       FUNCION ENSAMBLADORA DEL SEP
#===============================================================================
def construccion_sep(archivo:str):
    #Ensamblaje del sep
    sistema = SistemaPotencia()
    with pd.ExcelFile(archivo) as xls:
        sistema.frecuencia = obtener_frecuencia(xls)
        sistema.barras = objeto_barra(xls)
        sistema.generadores = objeto_generador(xls)
        sistema.cargas = objeto_carga(xls)

        # Vincular la demanda de las cargas a las barras antes de simular
        # La hoja CARGAS es la UNICA fuente de verdad para P_dem/Q_dem.
        # Se resetea primero para no arrastrar valores ya cargados desde
        # la hoja BARRAS (evita duplicar la demanda si un bus aparece en
        # ambas hojas con el mismo monto).
        for barra in sistema.barras.values():
            barra.P_dem = 0.0
            barra.Q_dem = 0.0

        for carga in sistema.cargas.values():
            barra = sistema.barras.get(carga.id_barra)
            if barra:
                barra.P_dem += carga.P_mag
                barra.Q_dem += carga.Q_mag

        for barra in sistema.barras.values():
            barra.P_neta = barra.P_gen - barra.P_dem
            barra.Q_neta = barra.Q_gen - barra.Q_dem
                
        sistema.lineasTrx = objeto_lineas_trx(xls)
        sistema.fallas = objeto_fallas(xls)




    return sistema
