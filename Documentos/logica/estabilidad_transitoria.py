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
import numpy as np

def reduccion_kron(ybus_original, nodos_a_mantener):
    """
    Reduce la matriz Ybus eliminando los nodos que no pertenecen a 'nodos_a_mantener'
    mediante reducción matricial por bloques (Kron reduction).
    """
    ybus = np.array(ybus_original, dtype=complex)
    n_total = ybus.shape[0]
    
    # Identificar índices a eliminar
    nodos_a_eliminar = [i for i in range(n_total) if i not in nodos_a_mantener]
    
    # Si no hay nodos que eliminar, retornar la matriz original
    if not nodos_a_eliminar:
        return ybus
        
    R = nodos_a_mantener
    E = nodos_a_eliminar
    
    # Partición de matrices
    Y_RR = ybus[np.ix_(R, R)]
    Y_RE = ybus[np.ix_(R, E)]
    Y_ER = ybus[np.ix_(E, R)]
    Y_EE = ybus[np.ix_(E, E)]
    
    # Inversión segura del bloque E (usando pseudo-inversa por si hay nodos mal acondicionados)
    Y_EE_inv = np.linalg.pinv(Y_EE)
    
    # Cálculo de la reducción de Kron: Y_red = Y_RR - Y_RE * inv(Y_EE) * Y_ER
    ybus_red = Y_RR - Y_RE @ Y_EE_inv @ Y_ER
    
    return ybus_red

#===============================================================================
#                       RUTINA PRINCIPAL DE SIMULACIÓN
#===============================================================================
def simular_transitorio(sep, ybus_falla_red, ybus_postfalla_red, falla, dt=0.001):
    t = 0.0
    tiempos = []
    
    resultados_delta = {gen.id_gen: [] for gen in sep.generadores.values()}
    resultados_omega = {gen.id_gen: [] for gen in sep.generadores.values()}
    resultados_pe = {gen.id_gen: [] for gen in sep.generadores.values()}
    
    id_slack = next(gen.id_gen for gen in sep.generadores.values() if gen.ref)
    gens = list(sep.generadores.values())
    ws = 2 * np.pi * 60.0
    
    # Función auxiliar para evaluar Pe en cada iteración interna de RK4
    def calcular_Pe(angulos, ybus):
        E_fasores = np.array([cmath.rect(g.E_mag, ang) for g, ang in zip(gens, angulos)])
        I_calc = np.dot(ybus, E_fasores)
        return (E_fasores * np.conj(I_calc)).real
    
    while t <= falla.duracion:
        tiempos.append(t)
        # Tolerancia para el corte exacto en coma flotante
        ybus_actual = ybus_falla_red if t < (falla.tiempo_despeje - 1e-6) else ybus_postfalla_red
        
        deltas = np.array([g.E_angle_rad for g in gens])
        omegas = np.array([g.omega for g in gens])
        Pms = np.array([g.Pm for g in gens])
        Hs = np.array([g.H for g in gens])
        
        # 1. Almacenar el estado real actual al inicio del paso
        Pe_actual = calcular_Pe(deltas, ybus_actual)
        for i, gen in enumerate(gens):
            resultados_pe[gen.id_gen].append(Pe_actual[i])
            resultados_delta[gen.id_gen].append(math.degrees(deltas[i]))
            resultados_omega[gen.id_gen].append(omegas[i])
            
        # 2. Multi-Machine RK4 (Evaluación acoplada)
        k1_d = omegas - ws
        k1_w = (np.pi * 60.0 / Hs) * (Pms - Pe_actual)
        
        Pe2 = calcular_Pe(deltas + 0.5 * dt * k1_d, ybus_actual)
        k2_d = (omegas + 0.5 * dt * k1_w) - ws
        k2_w = (np.pi * 60.0 / Hs) * (Pms - Pe2)
        
        Pe3 = calcular_Pe(deltas + 0.5 * dt * k2_d, ybus_actual)
        k3_d = (omegas + 0.5 * dt * k2_w) - ws
        k3_w = (np.pi * 60.0 / Hs) * (Pms - Pe3)
        
        Pe4 = calcular_Pe(deltas + dt * k3_d, ybus_actual)
        k4_d = (omegas + dt * k3_w) - ws
        k4_w = (np.pi * 60.0 / Hs) * (Pms - Pe4)
        
        deltas_new = deltas + (dt / 6.0) * (k1_d + 2*k2_d + 2*k3_d + k4_d)
        omegas_new = omegas + (dt / 6.0) * (k1_w + 2*k2_w + 2*k3_w + k4_w)
        
        for i, gen in enumerate(gens):
            gen.E_angle_rad = deltas_new[i]
            gen.omega = omegas_new[i]
            
        t += dt
        
    estado = "SISTEMA ESTABLE"
    for id_gen in resultados_delta:
        if id_gen != id_slack:
            diff = np.abs(np.array(resultados_delta[id_gen]) - np.array(resultados_delta[id_slack]))
            if np.max(diff) > 180: # Verificación sobre toda la oscilación, no solo el final
                estado = "SISTEMA INESTABLE"
                break
                
    return tiempos, resultados_delta, resultados_omega, resultados_pe, estado