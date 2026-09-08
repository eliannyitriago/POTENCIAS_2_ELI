import os
import sys
import numpy as np
import copy
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
    #---------------------------REGIMEN ESTACIONARIO----------------------------
    #Armado de la matriz de admitacia para el flujo de potencia
    sep.ybus = sep.armar_ybus()
    #Calculo del flujo de potencia
    flujo_potencia = FlujoPotencia(sep)
    flujo_potencia.gauss_seidel()
    flujo_potencia.potencia_slack()
    flujo_potencia.actualizar_potencias()

    #Calculo de las valores de los generadores y cargas
    sep.corriente_inyectada_generador()
    sep.tension_interna_generadores()
    sep.impedancia_carga()
    
    # Asignación de Potencia Mecánica para el ciclo de estabilidad
    for gen in sep.generadores.values():
        gen.Pm = sep.barras[gen.id_barra].P_gen

    np.set_printoptions(precision=4, suppress=True, linewidth=150)
    #-----------------------ANÁLISIS DE PERTURBACIÓN----------------------------
    #Creando las barras en los bornes
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
    idx_falla = sep_estacionario.bus_to_idx[int(falla_prueba.barra_falla or 0)]
    ybus_falla = np.copy(sep_estacionario.ybus)
    ybus_falla[idx_falla, idx_falla] += 1.0 / falla_prueba.Z_falla # Inyección de impedancia

    # 3. Matriz Ybus de Post-Falla (Desconexión de líneas falladas)
    sep_postfalla = copy.deepcopy(sep_estacionario)
    
    # Separar los IDs por comas en caso de que la falla despeje más de una línea
    if falla_prueba.id_linea:
        lineas_a_desconectar = falla_prueba.id_linea.replace(" ", "").split(",")
        for id_lin in lineas_a_desconectar:
            if id_lin in sep_postfalla.lineasTrx:
                del sep_postfalla.lineasTrx[id_lin]
    
    ybus_postfalla = sep_postfalla.armar_ybus()
    ybus_postfalla = sep_postfalla.agregar_cargas_ybus(actualizar_self=True)

    # 4. Reducción de Kron (Retener solo nodos internos de generadores)
    nodos_gen = [sep_estacionario.bus_to_idx[gen.id_barra] for gen in sep_estacionario.generadores.values()]
    
    ybus_prefalla_red = reduccion_kron(sep_estacionario.ybus, nodos_gen)
    ybus_falla_red = reduccion_kron(ybus_falla, nodos_gen)
    ybus_postfalla_red = reduccion_kron(ybus_postfalla, nodos_gen)

    # 5. Simulación RK4
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