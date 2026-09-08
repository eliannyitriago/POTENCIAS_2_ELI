import math
import cmath
import numpy as np

#===============================================================================
#                       ECUACIÓN DE OSCILACIÓN Y RUNGE-KUTTA
#===============================================================================
def derivadas_oscilacion(delta, omega, Pm, Pe, H, f=60.0):
    """Ecuación de oscilación: retorna d(delta)/dt y d(omega)/dt"""
    ws = 2 * np.pi * f
    d_delta = omega - ws
    d_omega = (np.pi * f / H) * (Pm - Pe)
    return d_delta, d_omega

def paso_runge_kutta(delta_n, omega_n, Pm, Pe, H, dt, f=60.0):
    """Calcula el siguiente estado (n+1) usando RK4"""
    # Pendientes k1
    k1_d, k1_w = derivadas_oscilacion(delta_n, omega_n, Pm, Pe, H, f)
    
    # Pendientes k2
    k2_d, k2_w = derivadas_oscilacion(delta_n + 0.5*dt*k1_d, omega_n + 0.5*dt*k1_w, Pm, Pe, H, f)
    
    # Pendientes k3
    k3_d, k3_w = derivadas_oscilacion(delta_n + 0.5*dt*k2_d, omega_n + 0.5*dt*k2_w, Pm, Pe, H, f)
    
    # Pendientes k4
    k4_d, k4_w = derivadas_oscilacion(delta_n + dt*k3_d, omega_n + dt*k3_w, Pm, Pe, H, f)

    # Actualización de variables
    delta_n1 = delta_n + (dt / 6.0) * (k1_d + 2*k2_d + 2*k3_d + k4_d)
    omega_n1 = omega_n + (dt / 6.0) * (k1_w + 2*k2_w + 2*k3_w + k4_w)

    return delta_n1, omega_n1

#===============================================================================
#                       REDUCCIÓN DE KRON (MATRIZ YBUS)
#===============================================================================
def reduccion_kron(ybus_original, nodos_a_mantener):
    """
    Reduce la matriz Ybus eliminando los nodos que no pertenecen a 'nodos_a_mantener'.
    """
    ybus = np.array(ybus_original, dtype=complex)
    num_nodos = ybus.shape[0]
    
    # Identificar qué índices debemos eliminar (ordenados de mayor a menor)
    nodos_a_eliminar = [i for i in range(num_nodos) if i not in nodos_a_mantener]
    nodos_a_eliminar.sort(reverse=True)
    
    for p in nodos_a_eliminar:
        y_pp = ybus[p, p]
        
        # Evitar divisiones por cero si el nodo está desconectado
        if abs(y_pp) < 1e-6:
            ybus = np.delete(ybus, p, axis=0)
            ybus = np.delete(ybus, p, axis=1)
            continue
            
        ybus_nueva = np.copy(ybus)
        indices_actuales = [i for i in range(ybus.shape[0]) if i != p]
        
        for i in indices_actuales:
            for j in indices_actuales:
                ybus_nueva[i, j] = ybus[i, j] - (ybus[i, p] * ybus[p, j]) / y_pp
                
        # Eliminar fila y columna p de la matriz definitiva
        ybus = np.delete(ybus_nueva, p, axis=0)
        ybus = np.delete(ybus, p, axis=1)

    
    return ybus

#===============================================================================
#                       RUTINA PRINCIPAL DE SIMULACIÓN
#===============================================================================
def simular_transitorio(sep, ybus_falla_red, ybus_postfalla_red, falla, dt=0.001):
    t = 0.0
    tiempos = []
    
    # Listas para almacenar resultados
    resultados_delta = {gen.id_gen: [] for gen in sep.generadores.values()}
    resultados_omega = {gen.id_gen: [] for gen in sep.generadores.values()}
    resultados_pe = {gen.id_gen: [] for gen in sep.generadores.values()}
    
    # Identificar el generador de referencia (slack)
    id_slack = next(gen.id_gen for gen in sep.generadores.values() if gen.ref)
    gens = list(sep.generadores.values())
    
    while t <= falla.duracion:
        tiempos.append(t)
        ybus_actual = ybus_falla_red if t < falla.tiempo_despeje else ybus_postfalla_red
        
        # Cálculo dinámico de Pe para la iteración actual
        E_fasores = np.array([cmath.rect(g.E_mag, g.E_angle_rad) for g in gens])
        I_calc = np.dot(ybus_actual, E_fasores)
        Pe_calc = (E_fasores * np.conj(I_calc)).real
        
        for i, gen in enumerate(gens):
            Pe = Pe_calc[i]
            resultados_pe[gen.id_gen].append(Pe)
            
            delta_n1, omega_n1 = paso_runge_kutta(
                gen.E_angle_rad, gen.omega, gen.Pm, Pe, gen.H, dt
            )
            
            gen.E_angle_rad = delta_n1
            gen.omega = omega_n1
            
            resultados_delta[gen.id_gen].append(math.degrees(delta_n1))
            resultados_omega[gen.id_gen].append(omega_n1)
            
        t += dt
        
    # Evaluación automática de estabilidad
    estado = "SISTEMA ESTABLE"
    for id_gen in resultados_delta:
        if id_gen != id_slack:
            diff = np.abs(np.array(resultados_delta[id_gen]) - np.array(resultados_delta[id_slack]))
            # Si el ángulo relativo final diverge significativamente, es inestable
            if diff[-1] > 180: 
                estado = "SISTEMA INESTABLE"
                break
                
    return tiempos, resultados_delta, resultados_omega, resultados_pe, estado