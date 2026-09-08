import sys
from logica.instanciadores import (Barra, LineaTrx)
#===============================================================================
#                       AJUSTE DE LAS BARRAS DE LAS FUENTES
#===============================================================================
def barra_en_bornes(sep):
    #----------------------------------VALIDACION-------------------------------
    #Verificar que no haya más de un generador en la misma barra
    barras_ocupadas = set()
    for gen in sep.generadores.values():
        if gen.id_barra in barras_ocupadas:
            raise ValueError(
                f"Error: La barra '{gen.id_barra}' tiene más de un generador. "
                "El sistema requiere máximo 1 generador por barra."
            )
        barras_ocupadas.add(gen.id_barra)

    #Si no hay impedancias Z_prima a desplazar, se salta la función
    hay_impedancias = any(
        getattr(gen, 'Z_prima', 0) not in (0, None) 
        for gen in sep.generadores.values()
    )
    if not hay_impedancias:
        return sep
    #--------------------------DECLARACION DE VARIABLES-------------------------
    barras_gen = {gen.id_barra for gen in sep.generadores.values()}
    conteo_lineas = {barra:0 for barra in barras_gen}
    linea_conectada = {barra: None for barra in barras_gen}
    #--------------------------ALGORITMO DE LA FUNCION--------------------------
    #Busca cuantas lineas tiene conectada en las barras donde hay generadores
    for lineatrx in sep.lineasTrx.values():
        if lineatrx.barra_i in conteo_lineas:
            conteo_lineas[lineatrx.barra_i] += 1
            linea_conectada[lineatrx.barra_i] =lineatrx
        if lineatrx.barra_j in conteo_lineas:
            conteo_lineas[lineatrx.barra_j] += 1
            linea_conectada[lineatrx.barra_j] =lineatrx
    #Algoritmo principal
    nuevas_barras = {}
    nuevas_lineas = {}
    desplazador = sum(1 for valor in conteo_lineas.values() if valor > 1)
    for gen in sep.generadores.values():
        barra = gen.id_barra
        barra_desplazada = barra + desplazador
        #Suma la impedancia Z' con la del trx en linea
        if conteo_lineas.get(barra, 0) == 1:
            linea = linea_conectada[barra]
            if linea is not None:
                linea.Z_serie += gen.Z_prima
                linea.Y_serie = 1.0/linea.Z_serie
            gen.Z_prima = 0
        #Crea las barras en bornes y reestructura el sep
        else:
            id_linea_nueva = f"linea_{gen.id_gen}" 
            id_barra_nueva = f"barra_{gen.id_gen}"
            nuevas_barras[barra] = Barra(barra,id_barra_nueva,None,None,None,None,None,
                                    None,False)
            nuevas_lineas[id_linea_nueva] = LineaTrx(id_linea_nueva,barra,barra_desplazada,gen.Ra,
                                       gen.Xd_prima,None)
        # Actualizamos las variables de barras 
    for barra_id, nueva_barra in nuevas_barras.items():
        sep.barras[barra_id] = nueva_barra
    for linea_id, nueva_linea in nuevas_lineas.items():
        sep.lineasTrx[linea_id] = nueva_linea

    return sep
