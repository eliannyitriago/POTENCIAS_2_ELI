import os

from utilidades.presentacion import RESET
#===============================================================================
#                           PRESENTACIÓN DEL PROGRAMA
#===============================================================================
#CONFIGURACION DE LOS COLORES
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"
LABEL_COLOR = "\033[38;2;152;195;121m"
#CONFIGURACIONES DE LOS ESPACIADOS Y SEPARADORES
ANCHURA = 86
LINEA_DOBLE = "="*ANCHURA

def cabeceras_programa():
    """
    Presentacion de la informacion general del programa
    """
    #----------------CABECERA No.1: MEMBRETE DE LA UNIVERSIDAD------------------
    print(LINEA_DOBLE)
    #Variables del encabezado
    uni = "U N I V E R S I D A D   S I M Ó N   B O L Í V A R".center(ANCHURA)
    depa = "Departamento de Conversión y Transporte de Energía".center(ANCHURA)
    materia = "CT4234 · Sistemas de Potencia II".center(ANCHURA)
    print(f"{BOLD}{uni}{RESET}")
    print(f"{BOLD}{depa}{RESET}")
    print(f"{BOLD}{materia}{RESET}")
    print(LINEA_DOBLE)
    #---------------CABECERA No.2: INFORMACION DOCENTE Y AUTOR------------------
    print()
    print(f"{LABEL_COLOR}{BOLD}[ PROFESORA ]{RESET}  Ing. Carmen Quintero")
    print(f"{LABEL_COLOR}{BOLD}[ AUTOR ]{RESET}      Elianny Itriago  (Carnet: 21-10297)")
    print()
    print(LINEA_DOBLE)

def lectura_archivo(ruta_bd:str):
    """Funcion encargada de preguntarle al usuario el nombre del archivo a 
    trabajar"""
    while True:
        print()
        archivo = input(f"🔹 Ingrese el archivo Excel de datos: ").strip()
        if not archivo.endswith(".xlsx"):
            archivo += ".xlsx"
            ruta = os.path.join(ruta_bd,archivo)
        #VERIFICACION DE LA EXISTENCIA DE ARCHIVOS
            if not os.path.exists(ruta):
                os.system("cls" if os.name=="nt" else "clear")
                cabeceras_programa()
                print()
                print("⚠️ El archivo no existe".center(ANCHURA))
                print()
            else:
                os.system("cls" if os.name=="nt" else "clear")
                cabeceras_programa()
                break
    return ruta

def bienvenida(ruta_bd:str):
    "Funcion de bienvenida del programa"
    cabeceras_programa()
    return lectura_archivo(ruta_bd)
