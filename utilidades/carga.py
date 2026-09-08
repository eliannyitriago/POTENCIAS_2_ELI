import sys
import time
import threading
#===============================================================================
#                       ANIMACIONES DE CARGA DEL PROGRAMA
#===============================================================================
def ejecutar_con_animacion(mensaje: str, funcion, *args, **kwargs):
    """
    Ejecuta cualquier función en segundo plano mientras muestra
    una animación de carga en la terminal.
    """
    #-----------------DECLARACIÓN DE FUNCIONES Y VARIABLES----------------------
    calculando = True

    def animacion():
        #DECLARACION DE VARIABLES
        spinner = ['|', '/', '-', '\\']
        i = 0
        #CODIGO DE LA ANIMACION
        print()
        while calculando:
            simbolo = spinner[i % len(spinner)]
            sys.stdout.write(f"\033[F\033[K[ \033[96m{simbolo}\033[0m ] {mensaje}\n")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write(f"\033[F\033[K[ \033[92mOK\033[0m ] {mensaje} completado.\n")
        sys.stdout.flush()
    #----------------------INICIAR EL HILO DE ANIMACION-------------------------
    hilo = threading.Thread(target=animacion, daemon=True)
    hilo.start()
    #----------------------EJECUTAR LA RUTINA DE CALCULO------------------------
    try:
        resultado = funcion(*args, **kwargs)
    finally:
        #Detener la animación independientemente de si hubo error
        calculando = False
        hilo.join()
    return resultado
