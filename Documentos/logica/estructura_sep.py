import sys
from logica.instanciadores import (Barra, Generador, LineaTrx, Carga, Fallas3f)
from typing import Dict, Tuple, Optional
import numpy as np
import logging
#===============================================================================
#           DECLARACIÓN DE LA CLASE PARA EL SISTEMA EN GENERAL
#===============================================================================
class SistemaPotencia:
    def __init__(self):
    #COMPONENTES DE UN SISTEMA DE POTENCIA
        self.frecuencia: Optional[float] = None
        self.barras: Dict[int, Barra] = {}
        self.generadores: Dict[int, Generador] = {}
        self.cargas: Dict[int, Carga] = {}
        self.lineasTrx: Dict[Tuple[int,int,str],LineaTrx] = {}
        self.fallas: Dict[str, Fallas3f] = {}
    #MATRICES DEL SISTEMA
        self.ybus: Optional[np.ndarray] = None
    #MAPEO DINÁMICO A ÍNDICES DE MATRIZ
        self.bus_to_idx: Dict[int,int] = {}
        self.idx_to_bus: Dict[int,int] = {}
#===============================================================================
#                   MÉTODOS PARA EL CONTROL DEL SISTEMA
#===============================================================================
#CONSTRUCCIÓN DEL MAPEO
    def _construir_mapeo(self) -> None:
            """Genera un mapeo bidireccional entre IDs de barras e índices de 
            matriz (0 a N-1)."""
            self.bus_to_idx = {}
            self.idx_to_bus = {}
            
            for idx, id_barra in enumerate(sorted(self.barras.keys())):
                self.bus_to_idx[id_barra] = idx
                self.idx_to_bus[idx] = id_barra
#===============================================================================
#               MÉTODOS PARA LOS CÁLCULOS COMUNES DE UN SEP
#===============================================================================
    def armar_ybus(self) -> np.ndarray:
        """Construye y asigna la matriz de admitancia nodal Ybus tomando en 
        cuenta las líneas de transmisión, transformadores y capacitancias shunt."""
        # 1. Actualizar el mapeo de barras a índices
        self._construir_mapeo()
        
        num_barras = len(self.barras)
        ybus_analisis = np.zeros((num_barras, num_barras), dtype=complex)

        # 2. Incorporar elementos Shunt propios de la barra (ej. capacitores/reactores de barra)
        for id_barra, barra in self.barras.items():
            i = self.bus_to_idx[id_barra]
            ybus_analisis[i, i] += getattr(barra, 'Y_shunt', 0.0)

        # 3. Incorporar líneas de transmisión y transformadores
        for linea in self.lineasTrx.values():
            i = self.bus_to_idx.get(linea.barra_i)
            j = self.bus_to_idx.get(linea.barra_j)

            # Verificación de existencia de nodos
            if i is None or j is None:
                id_linea = getattr(linea, 'id_linea', f"{linea.barra_i}-{linea.barra_j}")
                logging.warning(
                    f"La línea/trafo {id_linea} conecta a barras no existentes "
                    f"({linea.barra_i} -> {linea.barra_j}). Se ignorará."
                )
                continue

            # Parámetros del modelo Pi equivalente
            y_serie = linea.Y_serie
            y_shunt = getattr(linea, 'Y_shunt', 0.0) / 2.0
            tap = getattr(linea, 'tap', 1.0)  # Valor por defecto 1.0 si es una línea normal

            # Ensamblaje nodal con soporte para Tap (Modelo Pi general)
            ybus_analisis[i, i] += (y_serie / (tap ** 2)) + y_shunt
            ybus_analisis[j, j] += y_serie + y_shunt
            ybus_analisis[i, j] -= y_serie / tap
            ybus_analisis[j, i] -= y_serie / tap

        # 4. Guardar resultado en el estado del objeto y retornar
        return ybus_analisis

    def agregar_cargas_ybus(self, actualizar_self: bool = False) -> np.ndarray:
        """Calcula las admitancias de carga en derivación y las suma a la Ybus.
        
        Args:
            actualizar_self: Si es True, sobrescribe `self.ybus` con la nueva matriz.
        """
        if self.ybus is None:
            raise ValueError("Debe ejecutar 'armar_ybus()' antes de agregar las cargas.")

        num_barras = len(self.barras)
        ybus_cargas = np.zeros((num_barras, num_barras), dtype=complex)

        for carga in self.cargas.values():
            i = self.bus_to_idx.get(carga.id_barra)
            y_rect = getattr(carga, 'Y_rect', None)

            if i is not None and y_rect is not None:
                ybus_cargas[i, i] += y_rect

        ybus_total = self.ybus + ybus_cargas

        if actualizar_self:
            self.ybus = ybus_total

        return ybus_total

    def impedancia_carga(self):
        """Precalcula las impedancias/admitancias equivalentes de todas las 
        cargas."""
        for carga in self.cargas.values():
            barra = self.barras.get(carga.id_barra)
            if barra and barra.v_mag:
                carga.v_mag = barra.v_mag
                carga.calcular_impedancia()
            else:
                logging.error(f"Falta voltaje en barra {carga.id_barra} para"
                              f" calcular carga {carga.id_carga}.")

    def corriente_inyectada_generador(self):
        """"Calcula la corriente inicial inyectada al sistema por 
        cada generador."""
        for gen in self.generadores.values():
            barra = self.barras.get(gen.id_barra)
            if not barra or not barra.v_fasor:
                logging.error(f"Falta fasor de voltaje en barra {gen.id_barra}"
                              f" para generador {gen.id_gen}.")
                continue
            S_generada = complex(barra.P_gen,barra.Q_gen)
            if barra.v_fasor == 0j:
                raise ZeroDivisionError(f"Voltaje nulo en la barra "
                            f"{barra.id_barra}. Imposible calcular corriente.")
            gen.I_iny =  (S_generada/barra.v_fasor).conjugate()

    def tension_interna_generadores(self):
        """Calcula la FEM interna inducida (E') de cada máquina síncrona."""
        for gen in self.generadores.values():
            barra = self.barras.get(gen.id_barra)
            if barra and barra.v_fasor is not None and gen.I_iny is not None:
                gen.E = barra.v_fasor + (gen.Z_prima*gen.I_iny)
                gen.actualizar_fem_inducida()
