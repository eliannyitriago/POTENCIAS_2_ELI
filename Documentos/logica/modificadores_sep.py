import sys
from logica.instanciadores import (Barra, LineaTrx)
#===============================================================================
#                       AJUSTE DE LAS BARRAS DE LAS FUENTES
#===============================================================================
def barra_en_bornes(sep_original):
    import copy
    # Importación local para evitar errores circulares
    from logica.instanciadores import Barra, LineaTrx
    
    sep = copy.deepcopy(sep_original)
    
    conteo_lineas = {gen.id_barra: 0 for gen in sep.generadores.values()}
    linea_conectada = {gen.id_barra: None for gen in sep.generadores.values()}
    
    for lineatrx in sep.lineasTrx.values():
        if lineatrx.barra_i in conteo_lineas:
            conteo_lineas[lineatrx.barra_i] += 1
            linea_conectada[lineatrx.barra_i] = lineatrx
        if lineatrx.barra_j in conteo_lineas:
            conteo_lineas[lineatrx.barra_j] += 1
            linea_conectada[lineatrx.barra_j] = lineatrx

    nuevas_barras = {}
    nuevas_lineas = {}
    
    for gen in sep.generadores.values():
        barra = gen.id_barra
        if conteo_lineas.get(barra, 0) == 1:
            linea = linea_conectada[barra]
            if linea is not None:
                linea.Z_serie += gen.Z_prima
                linea.Y_serie = 1.0 / linea.Z_serie
            gen.Z_prima = 0.0
        else:
            id_linea_nueva = f"linea_{gen.id_gen}" 
            barra_interna = int(barra) + 100 
            
            # 1. Creamos la barra ficticia (Nodos 101, 102...)
            nuevas_barras[barra_interna] = Barra(barra_interna, "interno", 0, 0, 0, 0, 1.0, 0.0, False)
            
            # 2. Conectamos la impedancia del generador con B_shunt = 0.0
            nuevas_lineas[id_linea_nueva] = LineaTrx(id_linea_nueva, barra_interna, int(barra), gen.Ra, gen.Xd_prima, 0.0)
            
            gen.id_barra = barra_interna
            gen.Z_prima = 0.0
            
    # Agregamos las nuevas barras y líneas al sistema
    for barra_id, nueva_barra in nuevas_barras.items():
        sep.barras[barra_id] = nueva_barra
    for linea_id, nueva_linea in nuevas_lineas.items():
        sep.lineasTrx[linea_id] = nueva_linea
        
    # 3. ACTUALIZACIÓN CRÍTICA: Forzamos a que la matriz YBUS crezca (ej. a 5x5)
    sep.numero_barras = len(sep.barras)
    sep.bus_to_idx = {id_b: idx for idx, id_b in enumerate(sep.barras.keys())}
    
    return sep
    