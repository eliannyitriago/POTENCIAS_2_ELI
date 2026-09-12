import os
import sys
import numpy as np
import copy
import cmath 
from logica.instanciadores import Fallas3f
from logica.estabilidad_transitoria import reduccion_kron, simular_transitorio
from base_datos.gestor_base_datos import construccion_sep
from utilidades.encabezados import bienvenida 
from utilidades.carga import ejecutar_con_animacion
from utilidades.menu_desplegable import menu_resultados
from logica.metodo_gs import FlujoPotencia
from logica.modificadores_sep import barra_en_bornes

#===============================================================================
#                       RUTINA PRINCIPAL DEL PROGRAMA
#===============================================================================
def main(ruta_problema:str):
    """
    Funcion principal encargada de ejecutar las rutinas de calculo.
    """
    #----------------------------CONSTRUCCION DEL SEP---------------------------
    sep = construccion_sep(ruta_problema)
    # ---------------------------REGIMEN ESTACIONARIO----------------------------
    # 1. Flujo de potencia (calcula V y delta en las barras 1, 2 y 3)
    sep.ybus = sep.armar_ybus()
    flujo_potencia = FlujoPotencia(sep)
    flujo_potencia.gauss_seidel()
    flujo_potencia.potencia_slack()
    flujo_potencia.actualizar_potencias()

    # 2. CÁLCULO DE TENSIONES INTERNAS ANTES DE TOCAR LA RED
    # (Esto se hace con el 'sep' original para usar los voltajes de las barras 1 y 2 verdaderas)
    sep.corriente_inyectada_generador()
    sep.tension_interna_generadores()
    sep.impedancia_carga()

    # 3. Asignación de Potencia Mecánica
    for gen in sep.generadores.values():
        gen.Pm = sep.barras[gen.id_barra].P_gen

    np.set_printoptions(precision=4, suppress=True, linewidth=150)
    
    # -----------------------ANÁLISIS DE PERTURBACIÓN----------------------------
    # 4. AHORA SÍ: Creamos las barras en bornes para la simulación transitoria
    sep_estacionario = barra_en_bornes(sep)
    sep_estacionario.ybus = sep_estacionario.armar_ybus()
    sep_estacionario.ybus = sep_estacionario.agregar_cargas_ybus()
    
    # 1. Definir la falla trifásica (Ejemplo: Falla franca en barra 3, despeje en 0.2s)
    if not sep_estacionario.fallas:
        raise ValueError("Error: No se encontraron fallas registradas en el Excel.")
        
    id_primera_falla = list(sep_estacionario.fallas.keys())[0] 
    falla_prueba = sep_estacionario.fallas[id_primera_falla]

    print(f"\n⚠️  FALLA APLICADA: {id_primera_falla}")
    print(f"    Línea(s) afectada(s): {falla_prueba.id_linea}")
    print(f"    Barra de falla: {falla_prueba.barra_falla}")
    print(f"    Tiempo de despeje (tc): {falla_prueba.tiempo_despeje} s")
    print(f"    Duración total simulada: {falla_prueba.duracion} s")
    print(f"    Impedancia de falla: {falla_prueba.Z_falla} p.u.")
    
    # 2. Matriz Ybus de Falla
    ybus_falla = np.copy(sep_estacionario.ybus)
    
    # Función de apoyo para validar si el Excel tiene una barra definida
    def es_numero(valor):
        try:
            import math
            return not math.isnan(float(valor))
        except (ValueError, TypeError):
            return False

    # Validamos si la falla es en una barra (Problema 2) o en medio de una línea (Problema 1)
    if falla_prueba.barra_falla and es_numero(falla_prueba.barra_falla):
        # --- FALLA FRANCA EN BARRA ---
        idx_falla = sep_estacionario.bus_to_idx[int(falla_prueba.barra_falla)]
        ybus_falla[idx_falla, idx_falla] += 1.0 / falla_prueba.Z_falla
        
    else:
        # --- FALLA EN MEDIO DE UNA LÍNEA (Transformación Estrella-Triángulo) ---
        id_lin = str(falla_prueba.id_linea).split(',')[0].strip()
        
        # Búsqueda segura que evita errores de tipo en el diccionario
        linea_falla = None
        for k, v in sep_estacionario.lineasTrx.items():
            if str(k) == id_lin or str(getattr(v, 'id_linea', '')) == id_lin:
                linea_falla = v
                break
                
        if linea_falla is None:
            linea_falla = list(sep_estacionario.lineasTrx.values())[0]
        
        idx_i = sep_estacionario.bus_to_idx[linea_falla.barra_i]
        idx_j = sep_estacionario.bus_to_idx[linea_falla.barra_j]
        
        # Determinamos el porcentaje (si falla_prueba no lo tiene, asumimos 50% = 0.5)
        p = getattr(falla_prueba, 'porc_linea', 0.5)
        if p > 1: p = p / 100.0  # Convierte 50.0 a 0.5
        
        # Impedancias: Z1 (hasta la falla), Z2 (desde la falla), y Zf (impedancia a tierra)
        Z1 = p * linea_falla.Z_serie
        Z2 = (1 - p) * linea_falla.Z_serie
        Zf = falla_prueba.Z_falla if falla_prueba.Z_falla != 0 else 1e-6
        
        # Equivalente Triángulo (Zeq = Z1*Z2 + Z2*Zf + Z1*Zf)
        Zeq = (Z1 * Z2) + (Z2 * Zf) + (Z1 * Zf)
        
        # Admitancias equivalentes
        y_ij = 1.0 / (Zeq / Zf)
        y_iG = 1.0 / (Zeq / Z2)
        y_jG = 1.0 / (Zeq / Z1)
        
        # A. Retiramos la línea sana original de la matriz Ybus_falla
        y_L = 1.0 / linea_falla.Z_serie
        ybus_falla[idx_i, idx_i] -= y_L
        ybus_falla[idx_j, idx_j] -= y_L
        ybus_falla[idx_i, idx_j] += y_L
        ybus_falla[idx_j, idx_i] += y_L
        
        # B. Añadimos el equivalente con el cortocircuito integrado
        ybus_falla[idx_i, idx_i] += (y_ij + y_iG)
        ybus_falla[idx_j, idx_j] += (y_ij + y_jG)
        ybus_falla[idx_i, idx_j] -= y_ij
        ybus_falla[idx_j, idx_i] -= y_ij

    # 3. Matriz Ybus de Post-Falla (Desconexión de líneas falladas)
    sep_postfalla = copy.deepcopy(sep_estacionario)
    
    # Separar los IDs por comas en caso de que la falla despeje más de una línea
    if falla_prueba.id_linea:
        lineas_a_desconectar = falla_prueba.id_linea.replace(" ", "").split(",")
        for id_lin in lineas_a_desconectar:
            if id_lin in sep_postfalla.lineasTrx:
                del sep_postfalla.lineasTrx[id_lin]
    
    sep_postfalla.ybus = sep_postfalla.armar_ybus()
    ybus_postfalla = sep_postfalla.agregar_cargas_ybus(actualizar_self=True)

    # 4. Reducción de Kron (Retener solo nodos internos de generadores)
    nodos_gen = [sep_estacionario.bus_to_idx[gen.id_barra] for gen in sep_estacionario.generadores.values()]
    
    ybus_prefalla_red = reduccion_kron(sep_estacionario.ybus, nodos_gen)
    ybus_falla_red = reduccion_kron(ybus_falla, nodos_gen)
    ybus_postfalla_red = reduccion_kron(ybus_postfalla, nodos_gen)

    # IGUALAR Pm AL Pe INTERNO EXACTO PRE-FALLA ===
    gens = list(sep_estacionario.generadores.values())
    E_fasores_0 = np.array([cmath.rect(g.E_mag or 0.0, g.E_angle_rad or 0.0) for g in gens])
    I_pre = np.dot(ybus_prefalla_red, E_fasores_0)
    Pe_pre = (E_fasores_0 * np.conj(I_pre)).real
    
    for i, gen in enumerate(gens):
        gen.Pm = Pe_pre[i]

    # 5. Simulación RK4
    DURACION_VISUALIZACION = 4.0  # segundos - ajusta este valor libremente
    if falla_prueba.duracion < DURACION_VISUALIZACION:
        print(f"    (Duracion extendida de {falla_prueba.duracion}s a "
              f"{DURACION_VISUALIZACION}s para poder visualizar la oscilacion completa)")
        falla_prueba.duracion = DURACION_VISUALIZACION

    print("\nIniciando simulación transitoria...")
    tiempos, angulos, velocidades, potencias_e, estado = simular_transitorio(
        sep_estacionario, ybus_falla_red, ybus_postfalla_red, falla_prueba
    )
    print(f"\n⚡ RESULTADO: {estado} ⚡")
    
    return sep_estacionario, tiempos, angulos, velocidades, potencias_e, estado, ybus_prefalla_red, ybus_falla_red, ybus_postfalla_red

#===============================================================================
#                               ENTRY POINT 
#===============================================================================
if __name__ == "__main__":
    #-----------------DECLARACION DE VARIABLES Y CONSTANTES---------------------
    RUTA_BD = os.path.join(os.path.dirname(__file__), "base_datos")
    
    #-----------------RUTINA PRINCIPAL DEL PROGRAMA-----------------------------
    while True:
        os.system("cls" if os.name=="nt" else "clear") 
        ruta_problema = bienvenida(RUTA_BD)
        
        # 1. Recibir todas las variables y matrices
        sep_calculado, tiempos, angulos, velocidades, potencias_e, estado, ybus_pre, ybus_fall, ybus_post = main(ruta_problema)
        
        # 2. Pasarlas al menú de resultados
        accion = menu_resultados(sep_calculado, tiempos, angulos, velocidades, potencias_e, estado, ybus_pre, ybus_fall, ybus_post)
        
        if accion != "REINICIAR":
            break