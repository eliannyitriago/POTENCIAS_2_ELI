
from typing import Optional
import math
import cmath
#===============================================================================
#                  DECLARACIÓN DE LA CLASE PARA LAS BARRAS
#===============================================================================
class Barra:
    #CONSTRUCTOR
    def __init__(self, id_barra:int, tipo:str, P_gen, Q_gen,
                 P_dem, Q_dem, v_mag, v_ang,
                 barra_inf:bool):

        #---------------CARACTERISTICAS GENERALES DE UNA BARRA------------------
        self.barra_inf = barra_inf
        self.id_barra = id_barra
        self.tipo = tipo.lower()
        #-------------------------VALORES DE POTENCIA---------------------------
        self.P_gen = P_gen or 0
        self.Q_gen = Q_gen or 0
        self.P_dem = P_dem or 0
        self.Q_dem = Q_dem or 0
        #-----------------------POTENCIA NETA DE LA BARRA-----------------------
        self.P_neta = self.P_gen - self.P_dem
        self.Q_neta = self.Q_gen - self.Q_dem
        #---------------------------FASOR DE VOLTAJE----------------------------
        self.v_mag = v_mag
        self.v_ang = v_ang
        self.v_fasor = (
            cmath.rect(v_mag,math.radians(v_ang)) 
            if (v_mag is not None and v_ang is not None) else None
        )

    #METODOS DE LA CLASE BARRA
    def actualizar_voltajes(self,nuevo_valor:complex):
        """Actualiza el fasor de voltaje y recalcula magnitud y ángulo."""
        self.v_fasor =  nuevo_valor
        self.v_mag = abs(nuevo_valor)
        self.v_ang = math.degrees(cmath.phase(nuevo_valor))
#===============================================================================
#               DECLARACIÓN DE LA CLASE PARA LOS GENERADORES
#===============================================================================
class Generador:
    #CONSTRUCTOR
    def __init__(self, id_gen:str, id_barra:int, Ra, Xd_prima,
                 H, slack:bool):

    #---------------CARACTERISTICAS GENERALES DEL GENERADOR---------------------
        self.id_gen = id_gen
        self.id_barra = id_barra
        self.H = H
        self.ref = slack
    #------------------------IMPEDANCIAS INTERNAS-------------------------------
        self.Ra = Ra
        self.Xd_prima = Xd_prima
        self.Z_prima = complex(self.Ra,self.Xd_prima)
    #----------------VOLTAJE INDUCIDO Y CORRIENTE INYECTADA---------------------
        self.E: Optional[complex] = None
        self.E_mag: Optional[float] = None
        self.E_angle: Optional[float] = None
        self.I_iny: Optional[complex] = None
   
#--------------------POTENCIA MECÁNICA Y ELÉCTRICA--------------------------
        self.Pm: Optional[float] = None
        self.Pe_prefalla: Optional[float] = None
        self.Pe_falla: Optional[float] = None
        self.Pe_postfalla: Optional[float] = None
    #--------------------VARIABLES DE ESTABILIDAD-------------------------------
        self.omega = 2 * math.pi * 60  # Velocidad síncrona inicial
        self.E_angle_rad: Optional[float] = None  # Ángulo delta en radianes
        
    #METODOS DE LA CLASE GENERADOR
    def actualizar_fem_inducida(self):
        """Calcula la magnitud y el ángulo del voltaje interno (Rotor)."""
        if self.E is None:
            raise ValueError("No se a obtenido un valor fasorial de la fem")
        self.E_mag = abs(self.E)
        self.E_angle = math.degrees(cmath.phase(self.E))
        self.E_angle_rad = cmath.phase(self.E)

#===============================================================================
#           DECLARACIÓN DE LA CLASE PARA LAS LINEAS Y TRANSFORMADORES
#===============================================================================
class LineaTrx:
    # CONSTRUCTOR
    def __init__(self, id_linea:str, id_barra_i:int, id_barra_j:int,
                 R_value, X_value, B_shunt, G_value=0.0, B_serie_value=0.0):
        
    #-------CARACTERISTICAS GENERALES DE LAS LINEAS Y TRANSFORMADORES-----------
        self.id_linea = id_linea
        self.tipo = id_linea
        self.barra_i = id_barra_i 
        self.barra_j = id_barra_j
    #-------------------VALORES REACTIVOS Y RESISTIVOS--------------------------
        self.R_value = R_value
        self.X_value = X_value
        self.B_shunt = B_shunt
        self.G_value = G_value
        self.B_serie_value = B_serie_value
    # LÓGICA DE DECISIÓN: Si hay G o B, es Admitancia directa
        if self.G_value != 0 or self.B_serie_value != 0:
            self.Y_serie = complex(self.G_value, self.B_serie_value)
            self.Z_serie = 1.0 / self.Y_serie if self.Y_serie != 0j else complex(float('inf'), 0)
        else:
    # ----------------------IMPEDANCIA Y ADMITANCIAS----------------------------
    # Si G y B_serie están en 0, asumimos que dieron R y X (Impedancia)
            self.Z_serie = complex(self.R_value, self.X_value)
            self.Y_serie = 1.0 / self.Z_serie if self.Z_serie != 0j else 0j

        self.Y_shunt = complex(0,self.B_shunt)
#===============================================================================
#                  DECLARACIÓN DE LA CLASE PARA LAS CARGAS
#===============================================================================
class Carga:
    #CONSTRUCTOR
    def __init__(self,id_carga:str,id_barra:int,P_mag:float,Q_mag:float):

        #--------------CARACTERISTICAS GENERALES DE LAS CARGAS------------------
        self.id_carga = id_carga
        self.id_barra = id_barra
        # Convertir a flotante de forma segura, asignando 0.0 si la celda está en blanco
        self.P_mag = float(P_mag) if P_mag is not None else 0.0
        self.Q_mag = float(Q_mag) if Q_mag is not None else 0.0
        
        #-----------------VOLTAJES,IMPEDANCIAS Y ADMITANCIAS--------------------
        self.v_mag: Optional[float] = None
        self.Z_rect: Optional[complex] = None
        self.Y_rect: Optional[complex] = None
        self.R_value: float = 0.0
        self.X_value: float = 0.0
        
        #-------------------CALCULO DEL FACTOR DE POTENCIA----------------------
        # Prevenir división por cero si P_mag es 0
        if self.P_mag == 0.0:
            self.fp = 0.0 if self.Q_mag != 0.0 else 1.0
        else:
            self.fp = math.cos(math.atan(self.Q_mag/self.P_mag))
       
    #METODOS DE LA CLASE CARGA
    def calcular_impedancia(self): 
        """Modela la carga como impedancia/admitancia constante"""
        if self.v_mag is None or self.v_mag <= 0:
            raise ValueError(f"Voltaje inválido de la carga {self.id_carga}")
            
        S = complex(self.P_mag, self.Q_mag)
        
        # Validación para evitar división por cero si la potencia es nula
        if abs(S) < 1e-8:
            self.Z_rect = complex(float('inf'), 0)
            self.Y_rect = 0.0
        else:
            self.Z_rect = (self.v_mag**2) / S.conjugate()
            self.Y_rect = 1.0 / self.Z_rect
            
        self.R_value = self.Z_rect.real
        self.X_value = self.Z_rect.imag
#===============================================================================
#                  DECLARACIÓN DE LA CLASE PARA LAS FALLAS
#===============================================================================
class Fallas3f:
    def __init__(self,id_linea:str,duracion:float,t_dspj:float,comp_falla:str,
                 barra_i:int,barra_j:Optional[int],porc_linea:Optional[float],
                 Z_f:Optional[complex],barra_falla:Optional[int]):
    #CARACTERÍSTICAS GENERALES
        self.id_linea = id_linea
        self.duracion = duracion
        self.tiempo_despeje = t_dspj
        self.componente_falla = comp_falla.lower()
        self.barra_i = barra_i
        self.barra_j = barra_j
        self.porc_linea = porc_linea
        self.Z_falla = Z_f or 0.0j
    #LOGICA DE UBICACIÓN DE LA FALLA
        self.barra_falla = barra_falla
