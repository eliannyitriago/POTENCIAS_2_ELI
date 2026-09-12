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
                          ybus_prefalla, ybus_falla=None, ybus_postfalla=None,
                          tiempo_despeje=None):
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 11

    id_slack = next(g.id_gen for g in sep.generadores.values() if g.ref)
    gens_lista = list(sep.generadores.values())
    idx_slack_mat = next(i for i, g in enumerate(gens_lista) if g.id_gen == id_slack)

    E_fasores_0 = np.array([
        cmath.rect(g.E_mag, np.radians(angulos[g.id_gen][0])) for g in gens_lista
    ])
    I_pre = np.dot(ybus_prefalla, E_fasores_0)
    Pe_pre_inicial = (E_fasores_0 * np.conj(I_pre)).real
    dict_Pe_pre = {g.id_gen: Pe_pre_inicial[i] for i, g in enumerate(gens_lista)}

    todos_generadores = list(angulos.keys())
    generadores_sin_slack = [g for g in todos_generadores if g != id_slack]
    n_gens = len(generadores_sin_slack)

    colores = ['#2980b9', '#e67e22', '#8e44ad', '#f1c40f', '#16a085']
    color_titulo = '#27ae60' if "ESTABLE" in estado else '#c0392b'

    # ================================================================
    # FIGURA 1: Angulos relativos vs tiempo (sin cambios, todos juntos)
    # ================================================================
    fig1, ax1 = plt.subplots(figsize=(9, 6))
    if tiempo_despeje is not None:
        ax1.axvspan(0, tiempo_despeje, color='red', alpha=0.12,
                    label=f'Falla activa (0 - {tiempo_despeje}s)')
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
    max_abs = max(2000, np.max(np.abs([
        np.array(angulos[g]) - np.array(angulos[id_slack])
        for g in generadores_sin_slack
    ])) * 1.15)
    ax1.set_ylim(-max_abs, max_abs)
    ax1.legend(loc='upper left', frameon=True, fontsize=9)
    fig1.suptitle(f'Análisis Transitorio - {estado}', fontsize=16,
                  fontweight='bold', color='black')
    fig1.tight_layout(rect=(0, 0, 1, 0.94))
    

    # ================================================================
    # FIGURA 2: UN panel por generador, con sus propias curvas Pmax
    # ================================================================
    angulos_bg = np.linspace(-180, 180, 300)

    def calc_pe_bg(ybus, idx_gen_mat):
        """Curva Pe vs delta de UN generador, congelando los angulos de
        las demas maquinas en su valor inicial (aproximacion estandar
        para dibujar la curva de referencia sobre un eje 2D)."""
        if ybus is None:
            return None
        pe_list = []
        for d_deg in angulos_bg:
            d_rad = np.radians(d_deg + angulos[id_slack][0])
            E_fasores_bg = np.zeros(len(gens_lista), dtype=complex)
            for i, g in enumerate(gens_lista):
                if i == idx_gen_mat:
                    E_fasores_bg[i] = cmath.rect(g.E_mag, d_rad)
                else:
                    E_fasores_bg[i] = cmath.rect(g.E_mag, np.radians(angulos[g.id_gen][0]))
            I_bg = np.dot(ybus, E_fasores_bg)
            pe_list.append((E_fasores_bg[idx_gen_mat] * np.conj(I_bg[idx_gen_mat])).real)
        return pe_list

    ncols = min(2, n_gens)
    nrows = int(np.ceil(n_gens / ncols))
    fig2, axes = plt.subplots(nrows, ncols, figsize=(7.5 * ncols, 5.5 * nrows))
    axes = np.atleast_1d(axes).flatten()

    for idx, id_gen in enumerate(generadores_sin_slack):
        ax = axes[idx]
        idx_gen_mat = next(i for i, g in enumerate(gens_lista) if g.id_gen == id_gen)
        gen_color = colores[idx % len(colores)]

        pe_pre = calc_pe_bg(ybus_prefalla, idx_gen_mat)
        pe_fall = calc_pe_bg(ybus_falla, idx_gen_mat)
        pe_post = calc_pe_bg(ybus_postfalla, idx_gen_mat)

        if pe_pre:
            ax.plot(angulos_bg, pe_pre, color='#34495e', linestyle=':',
                    alpha=0.7, linewidth=1.3, label='$P_{max}$ Pre-falla')
        if pe_fall:
            ax.plot(angulos_bg, pe_fall, color='#e74c3c', linestyle=':',
                    alpha=0.7, linewidth=1.3, label='$P_{max}$ Durante falla')
        if pe_post:
            ax.plot(angulos_bg, pe_post, color='#27ae60', linestyle=':',
                    alpha=0.7, linewidth=1.3, label='$P_{max}$ Post-falla')

        Pm = sep.generadores[id_gen].Pm
        ax.axhline(Pm, color='magenta', linestyle='--', alpha=0.6,
                   label=f'$P_m$ = {Pm:.2f} p.u.')

        # --- LÓGICA DE RECORTE Y PUNTO INICIAL ---
        delta_rel_sim = np.array(angulos[id_gen]) - np.array(angulos[id_slack])
        potencias_sim = np.array(potencias_e[id_gen])
        
        # Buscar el índice donde el tiempo llega a 1.2 segundos
        try:
            idx_corte = next(i for i, t in enumerate(tiempos) if t >= 1.2)
        except StopIteration:
            idx_corte = len(delta_rel_sim)
            
        delta_recortado = list(delta_rel_sim[:idx_corte])
        potencias_recortadas = list(potencias_sim[:idx_corte])

        # Concatenar el punto de pre-falla (t=0-) al inicio de la trayectoria real
        delta_completo = [delta_recortado[0]] + delta_recortado
        potencias_completas = [dict_Pe_pre[id_gen]] + potencias_recortadas

        # Graficar el tramo limpio con la caída inicial
        ax.plot(delta_completo, potencias_completas, color=gen_color,
                linewidth=2.5, alpha=0.95, label='Trayectoria real', zorder=5)
        
        # Punto de inicio (bolita) ahora sobre la curva de pre-falla (gris)
        ax.plot(delta_completo[0], potencias_completas[0], marker='o',
                markersize=7, color=gen_color, zorder=6)

        ax.set_xlim(-180, 180)
        ax.set_title(f'Generador {id_gen}', fontweight='bold')
        ax.set_xlabel(f'Ángulo relativo al slack {id_slack} (grados)')
        ax.set_ylabel('Potencia eléctrica $P_e$ (p.u.)')
        ax.legend(loc='best', fontsize=8, frameon=True)

    for j in range(n_gens, len(axes)):
        axes[j].axis('off')

    fig2.suptitle(f'Curvas $P_e$ vs $\\delta$ por generador - {estado}',
                  fontsize=16, fontweight='bold', color='black')
    fig2.tight_layout(rect=(0, 0, 1, 0.95))
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