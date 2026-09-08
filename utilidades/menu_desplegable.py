import os 
import sys
from utilidades.encabezados import cabeceras_programa, ANCHURA, LINEA_DOBLE, RESET, BOLD
from utilidades.presentacion import (embellecer_matriz_color, 
                                     mostrar_informacion_sep,
                                     mostrar_informacion_barras_tabla)

#===============================================================================
#           CONFIGURACIONES GENERALES Y DECLARACION DE VARIABLES
#===============================================================================
#Configuracion de los colores
TITLE_COLOR = "\033[38;2;229;192;123m"
NUM_COLOR = "\033[38;2;152;195;121m"
#===============================================================================
#                   CONFIGURACION DE LAS OPCIONES DEL MENU
#===============================================================================
def header_menu():
        titulo = "M E N Ú   D E   R E S U L T A D O S".center(ANCHURA)
        print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
        print(LINEA_DOBLE)

def menu_resultados(sep, tiempos=None, angulos=None, velocidades=None, potencias_e=None, estado=None, ybus_prefalla=None, ybus_falla=None, ybus_postfalla=None):
    """Muestra el menú desplegable de resultados al finalizar las rutinas."""
    header_menu()
    while True:
        print(f"  {NUM_COLOR}[1]{RESET} Ver Matriz de Admitancia Nodal (Ybus)")
        print(f"  {NUM_COLOR}[2]{RESET} Ver Información del Sistema Eléctrico (SEP)")
        print(f"  {NUM_COLOR}[3]{RESET} Ver Flujo de Potencia")
        print(f"  {NUM_COLOR}[4]{RESET} Ver Gráficas de Estabilidad (δ y ω)")
        print(f"  {NUM_COLOR}[5]{RESET} Ver Matrices Reducidas (Pre-falla, Falla y Post-falla)")
        print(f"  {NUM_COLOR}[6]{RESET} Cargar otro archivo de datos")
        print(f"  {NUM_COLOR}[0]{RESET} Salir del programa")
        print(LINEA_DOBLE)
        
        opcion = input("🔹 Seleccione una opción: ").strip()
    #-----------------OPCION 1: MOSTRAR MATRIZ DE ADMITANCIAS-------------------
        if opcion == "1":
            titulo = "MATRIZ YBUS:".center(ANCHURA)
            #Limpia la pantalla dejando el encabezado
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
            print("=" * ANCHURA)
            #Muestra el resultado de la opcion seleccionada
            embellecer_matriz_color(sep.ybus)
            #Limpia la pantalla dejando el encabezado y volviendo al menu
            input("\nPresione ENTER para volver al menú...")
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()
    #-----------------OPCION 2: MOSTRAR INFORMACION DEL SEP---------------------
        elif opcion == "2":
            titulo = "INFORMACIÓN DEL SISTEMA:".center(ANCHURA)
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
            print("=" * ANCHURA)
            mostrar_informacion_sep(sep)
            input("\nPresione ENTER para volver al menú...")
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()
    #-----------------OPCION 3: MOSTRAR EL FLUJO DE POTENCIA--------------------
        elif opcion == "3":
            titulo = "FLUJO DE POTENCIA:".center(ANCHURA)
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
            print("=" * ANCHURA)
            mostrar_informacion_barras_tabla(sep)
            input("\nPresione ENTER para volver al menú...")
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()
    #-----------------OPCION 4: MOSTRAR GRÁFICAS DE ESTABILIDAD-----------------
        elif opcion == "4":
            if tiempos is not None and angulos is not None and potencias_e is not None:
                import numpy as np
                import matplotlib.pyplot as plt
                id_slack = next(g.id_gen for g in sep.generadores.values() if g.ref)
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
                fig.suptitle(f"Análisis Transitorio - {estado}", fontsize=14, fontweight='bold')
                
                # Gráfica 1: Ángulos Relativos
                for id_gen, val_delta in angulos.items():
                    if id_gen != id_slack:
                        delta_relativo = np.array(val_delta) - np.array(angulos[id_slack])
                        ax1.plot(tiempos, delta_relativo, label=f'δ_{id_gen} - δ_{id_slack}')
                ax1.set_title('Ángulos Relativos vs Tiempo')
                ax1.set_xlabel('Tiempo (s)')
                ax1.set_ylabel('Ángulo Relativo (grados)')
                ax1.grid(True, linestyle='--')
                ax1.legend()
                
                # Gráfica 2: Curva P vs δ
                for id_gen in angulos.keys():
                    ax2.plot(angulos[id_gen], potencias_e[id_gen], label=f'Gen {id_gen}')
                ax2.set_title('Potencia Eléctrica vs Ángulo (P vs δ)')
                ax2.set_xlabel('Ángulo Absoluto (grados)')
                ax2.set_ylabel('Potencia Eléctrica (p.u.)')
                ax2.grid(True, linestyle='--')
                ax2.legend()
                
                plt.tight_layout()
                plt.show()
            else:
                print("\n⚠️ No hay datos de simulación disponibles.")
            
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()

        #-----------------OPCION 5: MOSTRAR INFORMACIÓN DE LA FALLA-----------------
        elif opcion == "5":
            titulo = "ANÁLISIS DE PERTURBACIÓN (FALLA Y MATRICES)".center(ANCHURA)
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
            print("=" * ANCHURA)
            
            if ybus_prefalla is not None and sep.fallas:
                id_falla = list(sep.fallas.keys())[0]
                falla = sep.fallas[id_falla]
                
                # 1. Definir el evento de falla y tiempo de despeje
                print(f"\n  {BOLD}⚡ DEFINICIÓN DEL EVENTO DE FALLA:{RESET}")
                print(f"  • Tipo de Falla:               Cortocircuito Trifásico")
                print(f"  • Ubicación:                   Barra {falla.barra_falla}")
                print(f"  • Elementos a despejar:        Líneas {falla.id_linea}")
                print(f"  • Tiempo de Despeje (tc):      {falla.tiempo_despeje} segundos")
                print(f"  • Impedancia de Falla (Zf):    {falla.Z_falla} p.u.\n")
                
                # 2. Modelar las tres etapas (Matrices)
                print(f"  {BOLD}🔄 MODELADO DE LAS TRES ETAPAS (MATRICES REDUCIDAS):{RESET}")
                
                print(f"\n  {NUM_COLOR}1. ETAPA DE PRE-FALLA (Régimen Estacionario){RESET}")
                print("  Matriz Ybus Reducida (Nodos Internos de Generadores):")
                embellecer_matriz_color(ybus_prefalla)
                
                print(f"\n  {NUM_COLOR}2. ETAPA DURANTE LA FALLA (t <= tc){RESET}")
                print("  Matriz Ybus Reducida con Inyección de Falla:")
                embellecer_matriz_color(ybus_falla)
                
                print(f"\n  {NUM_COLOR}3. ETAPA DE POST-FALLA (t > tc){RESET}")
                print("  Matriz Ybus Reducida tras Desconexión de Líneas:")
                embellecer_matriz_color(ybus_postfalla)
            else:
                print("\n  ⚠️ No hay matrices o datos de falla disponibles.\n")

            input("\nPresione ENTER para volver al menú...")
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()

        #-----------------OPCIONES DEL SISTEMA (CARGAR/SALIR)-----------------------
        elif opcion == "6":
            return "REINICIAR"

        elif opcion == "0":
            print("\n¡Gracias por utilizar el programa! Salida exitosa.\n")
            sys.exit(0)

        else:
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()
            print()
            print("⚠️ Opción no válida. Por favor, intente de nuevo.".center(ANCHURA))
            print()
