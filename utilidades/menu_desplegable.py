import os 
import sys
from utilidades.encabezados import cabeceras_programa, ANCHURA, LINEA_DOBLE, RESET, BOLD
from utilidades.presentacion import (embellecer_matriz_color, 
                                     mostrar_informacion_sep,
                                     mostrar_informacion_barras_tabla)
import numpy as np
import matplotlib.pyplot as plt
import cmath

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

def graficar_estabilidad(sep, tiempos, angulos, potencias_e, estado,
                          ybus_prefalla, ybus_falla=None, ybus_postfalla=None, tiempo_despeje=None):
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12

    id_slack = next(g.id_gen for g in sep.generadores.values() if g.ref)
    gens_lista = list(sep.generadores.values())
    
    # Índices en la matriz Ybus para identificar a los generadores
    idx_slack_mat = next(i for i, g in enumerate(gens_lista) if g.id_gen == id_slack)

    E_fasores_0 = np.array([
        cmath.rect(g.E_mag, np.radians(angulos[g.id_gen][0])) for g in gens_lista
    ])
    I_pre = np.dot(ybus_prefalla, E_fasores_0)
    Pe_pre_inicial = (E_fasores_0 * np.conj(I_pre)).real
    dict_Pe_pre = {g.id_gen: Pe_pre_inicial[i] for i, g in enumerate(gens_lista)}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    color_titulo = '#27ae60' if "ESTABLE" in estado else '#c0392b'
    fig.suptitle(f'Análisis Transitorio - {estado}', fontsize=18,
                 fontweight='bold', color=color_titulo, y=0.98)

    colores = ['#2980b9', '#e67e22', '#8e44ad', '#f1c40f', '#16a085']
    todos_generadores = list(angulos.keys())
    generadores_sin_slack = [g for g in todos_generadores if g != id_slack]

    # --- GRÁFICA 1: ÁNGULO VS TIEMPO ---
    if tiempo_despeje is not None:
        ax1.axvspan(0, tiempo_despeje, color='red', alpha=0.12, label=f'Falla activa (0 - {tiempo_despeje}s)')
        ax1.axvline(tiempo_despeje, color='red', linestyle=':', linewidth=1.2)

    ax1.axhline(180, color='gray', linewidth=1, linestyle='--', alpha=0.5)
    ax1.axhline(-180, color='gray', linewidth=1, linestyle='--', alpha=0.5)
    ax1.axhline(0, color='black', linewidth=1.0, linestyle='-', alpha=0.6)

    for idx, id_gen in enumerate(generadores_sin_slack):
        delta_rel = np.array(angulos[id_gen]) - np.array(angulos[id_slack])
        ax1.plot(tiempos, delta_rel, label=f'Δδ ({id_gen} - {id_slack})',
                  linewidth=2.2, color=colores[idx % len(colores)])

    ax1.set_title('Ángulos Relativos vs Tiempo', fontweight='bold')
    ax1.set_xlabel('Tiempo (s)')
    ax1.set_ylabel('Ángulo relativo (grados)')
    max_abs = max(200, np.max(np.abs([np.array(angulos[g]) - np.array(angulos[id_slack]) for g in generadores_sin_slack])) * 1.15)
    ax1.set_ylim(-max_abs, max_abs)
    ax1.legend(loc='upper left', frameon=True, fontsize=9)

    # --- GRÁFICA 2: CRITERIO DE IGUALDAD DE ÁREAS ---
    angulos_bg = np.linspace(-10, 180, 400) # Rango panorámico del libro (grados relativos)
    
    for idx, id_gen in enumerate(generadores_sin_slack):
        idx_gen_mat = next(i for i, g in enumerate(gens_lista) if g.id_gen == id_gen)
        
        # 1. Rutina para proyectar la curva senoidal entera sobre los 360 grados
        def calc_pe_bg(ybus):
            if ybus is None: return None
            pe_list = []
            for d_deg in angulos_bg:
                d_rad = np.radians(d_deg + angulos[id_slack][0]) # Reconstruir ángulo real
                E_fasores_bg = np.zeros(len(gens_lista), dtype=complex)
                for i, g in enumerate(gens_lista):
                    if i == idx_slack_mat:
                        E_fasores_bg[i] = cmath.rect(g.E_mag, np.radians(angulos[g.id_gen][0]))
                    elif i == idx_gen_mat:
                        E_fasores_bg[i] = cmath.rect(g.E_mag, d_rad)
                    else:
                        E_fasores_bg[i] = cmath.rect(g.E_mag, np.radians(angulos[g.id_gen][0]))
                I_bg = np.dot(ybus, E_fasores_bg)
                Pe_gen = (E_fasores_bg[idx_gen_mat] * np.conj(I_bg[idx_gen_mat])).real
                pe_list.append(Pe_gen)
            return pe_list

        pe_pre = calc_pe_bg(ybus_prefalla)
        pe_fall = calc_pe_bg(ybus_falla)
        pe_post = calc_pe_bg(ybus_postfalla)

        # Dibujar las curvas de fondo
        if pe_pre: ax2.plot(angulos_bg, pe_pre, color='#34495e', linestyle=':', alpha=0.6, label='P_max (Pre-Falla)')
        if pe_fall: ax2.plot(angulos_bg, pe_fall, color='#e74c3c', linestyle=':', alpha=0.6, label='P_max (Falla)')
        if pe_post: ax2.plot(angulos_bg, pe_post, color='#27ae60', linestyle=':', alpha=0.6, label='P_max (Post-Falla)')
        
        # Línea de Potencia Mecánica
        Pm = sep.generadores[id_gen].Pm
        ax2.axhline(Pm, color='magenta', linestyle='--', alpha=0.5, label=f'Pm ({Pm:.2f} p.u.)')

        # 2. Dibujar la trayectoria dinámica superpuesta (trazo grueso)
        delta_rel_sim = np.array(angulos[id_gen]) - np.array(angulos[id_slack])
        
        # Recortar la simulación hasta el primer máximo (Ida del péndulo) ---
        cambio_direccion = np.where(np.diff(delta_rel_sim) < 0)[0]
        idx_max = cambio_direccion[0] if len(cambio_direccion) > 0 else len(delta_rel_sim) - 1
        
        delta_rel_recortado = delta_rel_sim[:idx_max+1]
        potencias_recortadas = potencias_e[id_gen][:idx_max+1]
        
        delta_rel_pre = angulos[id_gen][0] - angulos[id_slack][0]
        angulos_completos = [delta_rel_pre] + list(delta_rel_recortado)
        potencias_completas = [dict_Pe_pre[id_gen]] + potencias_recortadas

        ax2.plot(angulos_completos, potencias_completas, label=f'Trayectoria Real ({id_gen})',
                  linewidth=3.0, color=colores[idx % len(colores)], alpha=0.85)
        ax2.plot(angulos_completos[0], potencias_completas[0], marker='o',
                  markersize=8, color=colores[idx % len(colores)]) # Punto de inicio
        
    ax2.set_title('Criterio de Igualdad de Áreas', fontweight='bold')
    ax2.set_xlabel(f'Ángulo relativo al slack {id_slack} (grados)')
    ax2.set_ylabel('Potencia Eléctrica (p.u.)')
    ax2.set_xlim(-10, 180) # Enfocar el área de interés
    ax2.legend(loc='upper right', frameon=True, fontsize=9)

    plt.tight_layout(rect=(0, 0, 1, 0.93))
    plt.show()
    
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
        
        if opcion == "1":
            titulo = "MATRIZ YBUS:".center(ANCHURA)
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
            print("=" * ANCHURA)
            embellecer_matriz_color(sep.ybus)
            input("\nPresione ENTER para volver al menú...")
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()
            
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
            
        elif opcion == "4":
            if tiempos is not None and angulos is not None and potencias_e is not None and ybus_prefalla is not None and estado is not None:
                tc = sep.fallas[list(sep.fallas.keys())[0]].tiempo_despeje if sep.fallas else None
                # ---> ACTUALIZADO: Pasamos ybus_falla y ybus_postfalla a la función
                graficar_estabilidad(sep, tiempos, angulos, potencias_e, estado, ybus_prefalla, ybus_falla, ybus_postfalla, tiempo_despeje=tc)
            else:
                print("\n⚠️ No hay datos de simulación disponibles.")

            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()

        elif opcion == "5":
            titulo = "ANÁLISIS DE PERTURBACIÓN (FALLA Y MATRICES)".center(ANCHURA)
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            print(f"{TITLE_COLOR}{BOLD}{titulo}{RESET}")
            print("=" * ANCHURA)
            
            if ybus_prefalla is not None and sep.fallas:
                id_falla = list(sep.fallas.keys())[0]
                falla = sep.fallas[id_falla]
                
                print(f"\n  {BOLD}⚡ DEFINICIÓN DEL EVENTO DE FALLA:{RESET}")
                print(f"  • Tipo de Falla:               Cortocircuito Trifásico")
                print(f"  • Ubicación:                   Barra {falla.barra_falla}")
                print(f"  • Elementos a despejar:        Líneas {falla.id_linea}")
                print(f"  • Tiempo de Despeje (tc):      {falla.tiempo_despeje} segundos")
                print(f"  • Impedancia de Falla (Zf):    {falla.Z_falla} p.u.\n")
                
                print(f"  {BOLD}🔄 MODELADO DE LAS TRES ETAPAS (MATRICES REDUCIDAS):{RESET}")
                print(f"\n  {NUM_COLOR}1. ETAPA DE PRE-FALLA (Régimen Estacionario){RESET}")
                embellecer_matriz_color(ybus_prefalla)
                
                print(f"\n  {NUM_COLOR}2. ETAPA DURANTE LA FALLA (t <= tc){RESET}")
                embellecer_matriz_color(ybus_falla)
                
                print(f"\n  {NUM_COLOR}3. ETAPA DE POST-FALLA (t > tc){RESET}")
                embellecer_matriz_color(ybus_postfalla)
            else:
                print("\n  ⚠️ No hay matrices o datos de falla disponibles.\n")

            input("\nPresione ENTER para volver al menú...")
            os.system("cls" if os.name == "nt" else "clear")
            cabeceras_programa()
            header_menu()

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