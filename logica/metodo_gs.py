import math
import pdb
import sys
import cmath
import numpy as np
#===============================================================================
#   CONSTRUCCION DE LA CLASE ENCARGADA EN EL CÁLCULO DEL FLUJO DE POTENCIA
#===============================================================================
class FlujoPotencia:
    #CONSTRUCTOR DE LA CLASE
    def __init__(self,sistema_potencia):
        self.sistema = sistema_potencia;
    
    #METODOS DE LA CLASE
    def gauss_seidel(self, max_tolerancia=1e-10, max_ite=10000):
        #DECLARACION DE VARIABLES Y CONSTANTES 
            y_bus = self.sistema.ybus
            num_barras = len(self.sistema.barras)
            errores_barras = {}
            error = float('inf')
            iteraciones = nuevo_valor_voltaje= 0
        #OBTENER MAPEOS DEL SISTEMA
            bus_to_idx = self.sistema.bus_to_idx
            idx_to_bus = self.sistema.idx_to_bus
        #CREACION DE UN DICCIONARIO PARA LOS ERRORES ENTRE BARRAS
            for bus in self.sistema.barras.values():
                errores_barras[f'Bus#{bus.id_barra}'] = 0
        #CONDICIONES INICIALES DEL SISTEMA PARA LAS BARRAS
                if (bus.tipo=='slack'):
                    continue
                elif (bus.tipo=='pv'):
                    bus.v_fasor = cmath.rect(bus.v_mag,0.0)
                    bus.v_ang = 0.0
                else:
                    bus.v_fasor = 1.0+0.0j
                    bus.v_mag = 1.0
                    bus.v_ang = 0
        #RUTINA DE CALCULO DEL METODO GAUSS-SEIDEL
            while ((error >= max_tolerancia) and (iteraciones <= max_ite)):
                for bus in self.sistema.barras.values():
                    if (bus.tipo=='slack'):
                        continue
                #TÉRMINOS DE LA FÓRMULA
                    i = bus_to_idx[bus.id_barra]
                    term_1 = y_bus[i,i]
                    term_2 = 0j
                    for j in range(0,num_barras):
                        if (j != i):
                            id_barra_j = idx_to_bus[j]
                            voltaje_j =self.sistema.barras[id_barra_j].v_fasor
                            term_2 += y_bus[i,j]*voltaje_j
                #APLICACIÓN DE LA FORMULA ITERATIVA
                    if (bus.tipo=='pv'):
                        S_gen=bus.v_fasor*(bus.v_fasor*term_1+term_2).conjugate()
                        bus.Q_neta = S_gen.imag
                        term_3=(bus.P_neta-1j*bus.Q_neta)/(bus.v_fasor.conjugate())
                        angulo_voltaje = cmath.phase((term_3-term_2)/term_1)
                        nuevo_valor_voltaje = cmath.rect(bus.v_mag,angulo_voltaje)
                    else:
                        term_3=(bus.P_neta-1j*bus.Q_neta)/(bus.v_fasor.conjugate())
                        nuevo_valor_voltaje = (term_3-term_2)/term_1 
                #ALMACENAMIENTO DEL ERROR DE LA BARRA
                    diferencia_voltajes = bus.v_fasor - nuevo_valor_voltaje
                    errores_barras[bus.id_barra]=abs(diferencia_voltajes)
                #ACTUALIZACIÓN DE VARIABLE
                    bus.v_fasor = nuevo_valor_voltaje
                    bus.v_mag = abs(nuevo_valor_voltaje)
                    bus.v_ang = math.degrees(cmath.phase(nuevo_valor_voltaje))
                #COMPROBACIÓN DE LA CONDICIÓN DE CONVERGENCIA
                error = max(errores_barras.values())
                iteraciones += 1

    def potencia_slack(self):
        """Calcula la potencia activa y reactiva absorbida/entregada por la
        barra Slack."""
        #---------DECLARACIÓN DE CONSTANTES E INICIACIÓN DE VARIABLES-----------
        y_bus  = self.sistema.ybus
        num_barras = len(self.sistema.barras)
        idx_slack = None
        #-----------IDENTIFICACIÓN DE LA BARRA SLACK EN EL SISTEMA--------------
        for i in range(num_barras):
            if self.sistema.barras[self.sistema.idx_to_bus[i]].tipo == 'slack':
                idx_slack = i
                break
        if idx_slack is None:
            raise ValueError("No se ha identificado ninguna barra SLACK")
        #-----------ALGORITMO PARA CALCULAR LA POTENCIA DE LA BARRA SLACK-------
        #Construccion del vector de voltaje actualizado
        V = np.array(
            [self.sistema.barras[self.sistema.idx_to_bus[i]].v_fasor 
             for i in range(num_barras)])

        #Corriente inyectada de la barra slack
        I_slack = np.dot(y_bus[idx_slack, :], V)

        #Calculo de la potencia compleja
        S_slack = V[idx_slack] * np.conj(I_slack)

        #Actualizando valores
        barra_slack = self.sistema.barras[self.sistema.idx_to_bus[idx_slack]]
        barra_slack.P_neta = S_slack.real
        barra_slack.Q_neta = S_slack.imag

    def actualizar_potencias(self):
        for barra in self.sistema.barras.values():
            if barra.id_barra in  self.sistema.cargas:
                carga = self.sistema.cargas[barra.id_barra]
                barra.P_dem = carga.P_mag
                barra.P_gen = barra.P_neta + barra.P_dem
                barra.Q_dem = carga.Q_mag
                barra.Q_gen = barra.Q_neta + barra.Q_dem
            elif (barra.tipo == 'slack'):
                barra.P_gen = max(0.0, barra.P_neta)
                barra.P_dem = max(0.0, -barra.P_neta)
                barra.Q_gen = max(0.0, barra.Q_neta)
                barra.Q_dem = max(0.0, -barra.Q_neta)
            else:
                barra.P_gen = barra.P_neta + barra.P_dem
                barra.Q_gen = barra.Q_neta + barra.Q_dem
        for gen in self.sistema.generadores.values():
            barra = self.sistema.barras.get(gen.id_barra)
            if barra:
                gen.Pm = barra.P_gen
