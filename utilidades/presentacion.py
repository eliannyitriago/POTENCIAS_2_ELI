import cmath
import numpy as np
#===============================================================================
#           CONFIGURACIONES GENERALES Y DECLARACION DE VARIABLES
#===============================================================================
#Configuracion de los colores
RESET = "\033[0m"
AZUL_CORCHETE = "\033[1;35m"  # Magenta en negrita para [ ]
COLOR_COMPLEJO = "\033[36m"  # Cian para números complejos (j)
COLOR_REAL = "\033[32m"  # Verde para parte real
COLOR_CERO = "\033[90m"  # Gris para ceros
#===============================================================================
#           FUNCIONES PARA MOSTRAR LA MATRIZ DE ADMITANCIA NODAL
#===============================================================================
def formatear_elemento(z, decimales=2):
    """Convierte un número a string formateado."""
    real, imag = round(z.real, decimales), round(z.imag, decimales)
    if abs(real) < 1e-9 and abs(imag) < 1e-9:
        return "0", COLOR_CERO
    elif abs(real) < 1e-9:
        val_str = f"{imag:g}j" if imag < 0 else f"{imag:g}j"
        return val_str, COLOR_COMPLEJO
    elif abs(imag) < 1e-9:
        return f"{real:g}", COLOR_REAL
    else:
        signo = "+" if imag >= 0 else ""
        return f"{real:g}{signo}{imag:g}j", COLOR_COMPLEJO


def embellecer_matriz_color(matriz):
    """Imprime una matriz formateada, alineada y con colores."""
    #---------------DECLARACION DE VARIABLES Y CONFIGURACIONES------------------
    matriz = np.array(matriz)
    if matriz.ndim == 1:
        matriz = matriz.reshape(1, -1)
    filas, cols = matriz.shape
    textos = np.empty((filas, cols), dtype=object)
    colores = np.empty((filas, cols), dtype=object)
    #------------------------FORMATEO DE LA MATRIZ------------------------------
    #Asignando colores a los textos
    for r in range(filas):
        for c in range(cols):
            txt, col = formatear_elemento(matriz[r, c])
            textos[r, c] = txt
            colores[r, c] = col

    #Ancho de columna basado en el texto plano
    anchos_cols = [
        max(len(textos[r, c]) for r in range(filas)) for c in range(cols)
    ]

    #Construcción visual con colores
    for r in range(filas):
        elementos_fila = []
        for c in range(cols):
            txt_alineado = textos[r, c].rjust(anchos_cols[c])
            color = colores[r, c]
            elementos_fila.append(f"{color}{txt_alineado}{RESET}")

        contenido = "   ".join(elementos_fila)
        print(f"{AZUL_CORCHETE}[{RESET} {contenido} {AZUL_CORCHETE}]{RESET}")

#===============================================================================
#           FUNCIÓN PARA MOSTRAR LA INFORMACIÓN GENERAL DEL SEP
#===============================================================================
def mostrar_informacion_sep(sep):
    """
    Muestra la información del SEP adaptando la columna derecha
    al número de generadores ingresados.
    """
    #-----------------------DECLARACION DE VARIABLES----------------------------
    num_gen = len(sep.generadores)
    frec_str = f"{sep.frecuencia} Hz" 
    col_izquierda = [
        f"📊  N° de Barras:       {len(sep.barras)}",
        f"⚙️  N° de Generadores:  {len(sep.generadores)} ",
        f"💡  N° de Cargas:       {len(sep.cargas)}",
        f"〰️  Frecuencia:        {sep.frecuencia}",
        f"📈  N° de Líneas:       {len(sep.lineasTrx)}"
    ]
    #-------------------------CONST. COLUMNA DERECHA----------------------------
    col_derecha = []
    for g in sep.generadores.values():
        e_mag = g.E_mag if g.E_mag is not None else 0.0
        e_angle = g.E_angle if g.E_angle is not None else 0.0
        gid = g.id_gen
        ig = f"{np.round(abs(g.I_iny),3)} ∠ {np.round(cmath.phase(g.I_iny),3)}° p.u."
        eg = f"{e_mag:.3f} ∠ {e_angle:.3f}° p.u."
        
        col_derecha.append(f"⚡ {gid} I_iny: {ig}")
        col_derecha.append(f"🔌 {gid} E': {eg}")
        col_derecha.append("")
    #Quita la última linea en blanco de la columna derecha
    if col_derecha and col_derecha[-1] == "":
        col_derecha.pop()
    #Igualar la cantidad de filas entre ambas columnas para no romper el cuadro
    max_filas = max(len(col_izquierda), len(col_derecha))
    while len(col_izquierda) < max_filas:
        col_izquierda.append("")
    while len(col_derecha) < max_filas:
        col_derecha.append("")
    #Renderizado en consola
    ancho_col = 40
    print(" ┌───── D A T O S   G E N E R A L E S " + "─" * 4 + "┬──────── G E N E R A D O R E S " + "─" * 10 + "┐")
    print(f" │{' ' * ancho_col}│{' ' * ancho_col} │")

    # Imprimir fila por fila alineando con f-strings
    for izq, der in zip(col_izquierda, col_derecha):
        print(f" │ {izq:<39}│ {der:<39}│")

    print(f" │{' ' * ancho_col}│{' ' * ancho_col}│")
    print(" └" + "─" * ancho_col + "┴" + "─" * ancho_col + "┘")
    print("=" * 86)

#===============================================================================
#           FUNCIÓN PARA MOSTRAR LA INFORMACIÓN GENERAL DEL SEP
#===============================================================================
def ancho_visible(texto):
    """Calcula el ancho real en consola compensando emojis."""
    texto_limpio = texto.replace('\ufe0f', '')
    emojis = ["📊", "📍", "⚡", "💡", "〰️", "📈", "⚙️", "🔌"]
    num_emojis = sum(texto_limpio.count(e) for e in emojis)
    return len(texto_limpio) + num_emojis


def mostrar_informacion_barras_tabla(sep):
    """
    Muestra la información de las barras en un formato de tabla
    con columnas divididas para Tensión y Potencia Neta.
    """
    # ---------------------------- RENDERIZADO ------------------------------------
    # Encabezados de la tabla
    encabezado = " │   BARRA   │  MAGNITUD |V|  │    ÁNGULO θ    │   P NETA (p.u.)  │   Q NETA (p.u.)  │"
    print(encabezado)
    print(" ├───────────┼────────────────┼────────────────┼──────────────────┼──────────────────┤")

    for id_bar, b in sep.barras.items():
        # Valores por defecto en caso de nulos
        v_mag = b.v_mag 
        v_ang = b.v_ang 
        p_neta = b.P_neta 
        q_neta = b.Q_neta

        # Formato de variables alineadas
        str_barra = f"📍 {id_bar}"
        str_v_mag = f"{v_mag:.3f} p.u."
        str_v_ang = f"{v_ang:.2f}°"
        str_p = f"{p_neta:.3f}"
        str_q = f"{q_neta:.3f}"

        # Ajuste de ancho exacto para la primera columna por el emoji
        pad_barra = 9 - (ancho_visible(str_barra) - len(str_barra))

        # Impresión de la fila formateada
        print(f" │ {str_barra:<{pad_barra}} │ {str_v_mag:^14} │ {str_v_ang:^14} │ {str_p:^16} │ {str_q:^16} │")

    print(" └───────────┴────────────────┴────────────────┴──────────────────┴──────────────────┘")
    print("=" * 86)
