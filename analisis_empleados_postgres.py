"""
===============================================================================
EJERCICIO 2 - RECURSOS HUMANOS (TiendaMax)
Analisis, limpieza y normalizacion de empleados_desnormalizado.csv
===============================================================================
Este script hace el pipeline completo.
Lee el CSV original, limpia, normaliza a 3FN y entrega los DataFrames
normalizados directamente a PostgreSQL, sin crear CSV intermedios.

Como se ejecuta:
    python analisis_empleados.py
===============================================================================
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # permite guardar la imagen aunque no haya pantalla
import matplotlib.pyplot as plt
import os
from cargar_a_postgres_directo import cargar_tablas_normalizadas

# Crea la carpeta donde vamos a guardar los resultados
os.makedirs("salidas", exist_ok=True)

# Hace que pandas imprima todas las columnas sin cortarlas
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def titulo(texto):
    """Imprime un titulo bonito para separar cada paso en la consola."""
    print("\n" + "=" * 79)
    print(texto)
    print("=" * 79)


def sub(texto):
    print("\n--- " + texto + " ---")


# =============================================================================
# PASO 1 - LEER EL CSV
# =============================================================================
titulo("PASO 1 - LEER EL CSV")

df_original = pd.read_csv("empleados_desnormalizado.csv")

# Guardamos una copia intacta para poder comparar ANTES vs DESPUES al final.
# .copy() crea una copia de verdad; si no lo pones, las dos variables
# apuntarian al mismo dato y se ensuciarian juntas.
df = df_original.copy()

print(f"El archivo tiene {df.shape[0]} filas y {df.shape[1]} columnas.")
sub("Primeras 5 filas")
print(df.head())


# =============================================================================
# PASO 2 - EXPLORAR (esta es la foto del ANTES)
# =============================================================================
titulo("PASO 2 - EXPLORAR LOS DATOS SUCIOS (ANTES)")

sub("2.1 Tipos de dato de cada columna (df.info)")
df.info()
# Fijate en dos cosas:
#   - fecha_ingreso aparece como 'object' (texto), no como fecha.
#   - salario_base y evaluacion_desempeno tienen menos valores que filas -> hay nulos.

sub("2.2 Cuantos nulos hay por columna")
nulos_antes = df.isnull().sum()
print(nulos_antes)

sub("2.3 Cuantas filas duplicadas exactas hay")
duplicados_antes = df.duplicated().sum()
print(f"Filas duplicadas: {duplicados_antes}")
print("Filas repetidas encontradas:")
print(df[df.duplicated(keep=False)].sort_values("id_empleado"))

sub("2.4 Valores distintos en la columna 'activo' (aqui esta el desorden)")
activo_antes = df["activo"].value_counts(dropna=False)
print(activo_antes)

sub("2.5 Estadisticas basicas de las columnas numericas")
print(df.describe())

# Guardamos la foto del ANTES en un archivo para el informe
with open("salidas/reporte_antes.txt", "w", encoding="utf-8") as f:
    f.write("FOTO ANTES DE LA LIMPIEZA\n")
    f.write("=" * 40 + "\n")
    f.write(f"Filas: {df.shape[0]}\nColumnas: {df.shape[1]}\n\n")
    f.write("Nulos por columna:\n" + nulos_antes.to_string() + "\n\n")
    f.write(f"Filas duplicadas: {duplicados_antes}\n\n")
    f.write("Valores de 'activo':\n" + activo_antes.to_string() + "\n\n")
    f.write("Tipo de dato de fecha_ingreso: " + str(df["fecha_ingreso"].dtype) + "\n")


# =============================================================================
# PASO 3 - LIMPIEZA
# =============================================================================
titulo("PASO 3 - LIMPIEZA")

# -----------------------------------------------------------------------------
# 3.1 DUPLICADOS
# -----------------------------------------------------------------------------
sub("3.1 Eliminar filas duplicadas exactas")

# Antes de borrar, calculamos la nomina CON duplicados.
# Nos sirve para responder la pregunta 4 (que tanto afecta el duplicado).
# OJO: la columna se llama bono_pct = porcentaje. El bono en dinero es
# salario_base * bono_pct, y el costo total es salario_base + bono.
tmp = df.copy()
tmp["activo_norm"] = tmp["activo"].str.strip().str.capitalize()
tmp["salario_tmp"] = tmp["salario_base"].fillna(
    tmp.groupby("departamento")["salario_base"].transform("median")
)
tmp["costo_tmp"] = tmp["salario_tmp"] * (1 + tmp["bono_pct"])
nomina_con_duplicados = tmp.loc[tmp["activo_norm"] == "Si", "costo_tmp"].sum()

filas_antes = len(df)
df = df.drop_duplicates()          # borra filas 100% identicas
df = df.reset_index(drop=True)     # renumera el indice 0,1,2,... despues de borrar
filas_despues = len(df)

print(f"ANTES:   {filas_antes} filas")
print(f"DESPUES: {filas_despues} filas")
print(f"Se eliminaron {filas_antes - filas_despues} fila(s) duplicada(s).")

# -----------------------------------------------------------------------------
# 3.2 COLUMNA 'activo' (texto inconsistente)
# -----------------------------------------------------------------------------
sub("3.2 Normalizar la columna 'activo'")
print("ANTES:")
print(df["activo"].value_counts(dropna=False))

# .str.strip()     -> quita espacios al inicio y al final
# .str.capitalize()-> deja la primera letra en mayuscula y el resto en minuscula
#                     "si" -> "Si", "SI" -> "Si", "No" -> "No"
# NO lo convertimos a True/False porque el ejercicio no lo pide.
df["activo"] = df["activo"].str.strip().str.capitalize()

print("\nDESPUES:")
print(df["activo"].value_counts(dropna=False))

# -----------------------------------------------------------------------------
# 3.3 FECHAS
# -----------------------------------------------------------------------------
sub("3.3 Convertir fecha_ingreso de texto a fecha real")
print("ANTES ->  tipo:", df["fecha_ingreso"].dtype, "| ejemplo:", df["fecha_ingreso"].iloc[0])

# format="%Y/%m/%d" describe como viene escrita la fecha: año/mes/dia
# %Y = año de 4 digitos, %m = mes de 2 digitos, %d = dia de 2 digitos
df["fecha_ingreso"] = pd.to_datetime(df["fecha_ingreso"], format="%Y/%m/%d")

print("DESPUES ->  tipo:", df["fecha_ingreso"].dtype, "| ejemplo:", df["fecha_ingreso"].iloc[0])

# -----------------------------------------------------------------------------
# 3.4 TEXTO DE LAS DEMAS COLUMNAS
# -----------------------------------------------------------------------------
sub("3.4 Limpiar espacios en las columnas de texto")
for col in ["nombre_empleado", "departamento", "jefe_departamento", "sucursal"]:
    df[col] = df[col].str.strip()
print("Espacios sobrantes eliminados en: nombre_empleado, departamento, jefe_departamento, sucursal")

# -----------------------------------------------------------------------------
# 3.5 NULOS
# -----------------------------------------------------------------------------
sub("3.5 Manejo de nulos")
print("Nulos ANTES:")
print(df.isnull().sum())

# CRITERIO 1: salario_base
# Un empleado no puede tener salario vacio, y borrar la fila seria perder
# informacion. Lo rellenamos con la MEDIANA de su departamento (la mediana
# no se desordena por sueldos muy altos, como si le pasa al promedio).
print("\nFilas con salario nulo:")
print(df[df["salario_base"].isnull()][["id_empleado", "nombre_empleado", "departamento", "salario_base"]])

mediana_por_depto = df.groupby("departamento")["salario_base"].transform("median")
df["salario_base"] = df["salario_base"].fillna(mediana_por_depto)
# Por si algun departamento quedara entero en nulo, rellenamos con la mediana general
df["salario_base"] = df["salario_base"].fillna(df["salario_base"].median())

# CRITERIO 2: evaluacion_desempeno
# Aqui NO inventamos nota. Una evaluacion que no existe no se puede adivinar
# sin falsear el analisis. La dejamos en nulo y simplemente la ignoramos
# cuando calculemos la correlacion (asi lo pide la pregunta 2).
print("\nFilas con evaluacion nula (se dejan tal cual):")
print(df[df["evaluacion_desempeno"].isnull()][["id_empleado", "nombre_empleado", "evaluacion_desempeno"]])

print("\nNulos DESPUES:")
print(df.isnull().sum())

# -----------------------------------------------------------------------------
# 3.6 TIPOS DE DATO
# -----------------------------------------------------------------------------
sub("3.6 Ajustar tipos de dato")
df["horas_extra_mes"] = df["horas_extra_mes"].astype(int)
df["salario_base"] = df["salario_base"].astype(float)
df["bono_pct"] = df["bono_pct"].astype(float)
df.info()

# -----------------------------------------------------------------------------
# 3.7 COLUMNAS CALCULADAS
# -----------------------------------------------------------------------------
sub("3.7 Crear columnas calculadas")
df["bono"] = df["salario_base"] * df["bono_pct"]          # el bono en dinero
df["costo_total"] = df["salario_base"] + df["bono"]       # lo que cuesta el empleado
hoy = pd.Timestamp.today()
df["antiguedad_anios"] = (hoy - df["fecha_ingreso"]).dt.days / 365.25
print(df[["id_empleado", "salario_base", "bono_pct", "bono", "costo_total", "antiguedad_anios"]].head())

# El DataFrame limpio permanece en memoria; no se crea un CSV intermedio.


# =============================================================================
# PASO 4 - COMPARACION ANTES vs DESPUES
# =============================================================================
titulo("PASO 4 - TABLA COMPARATIVA: ANTES vs DESPUES DE LA LIMPIEZA")

comparacion = pd.DataFrame({
    "Aspecto": [
        "Cantidad de filas",
        "Filas duplicadas",
        "Nulos en salario_base",
        "Nulos en evaluacion_desempeno",
        "Valores distintos en 'activo'",
        "Tipo de dato de fecha_ingreso",
        "Cantidad de columnas",
    ],
    "ANTES": [
        df_original.shape[0],
        df_original.duplicated().sum(),
        df_original["salario_base"].isnull().sum(),
        df_original["evaluacion_desempeno"].isnull().sum(),
        df_original["activo"].nunique(),
        str(df_original["fecha_ingreso"].dtype),
        df_original.shape[1],
    ],
    "DESPUES": [
        df.shape[0],
        df.duplicated().sum(),
        df["salario_base"].isnull().sum(),
        df["evaluacion_desempeno"].isnull().sum(),
        df["activo"].nunique(),
        str(df["fecha_ingreso"].dtype),
        df.shape[1],
    ],
})
print(comparacion.to_string(index=False))
# La comparación queda en consola/reporte; no se crea un CSV intermedio.


# =============================================================================
# PASO 5 - NORMALIZACION A 3FN
# =============================================================================
titulo("PASO 5 - NORMALIZAR EN 3 TABLAS (3FN)")

# Problema del CSV original: el nombre del departamento y su jefe se repiten en
# cada fila. Si el jefe de Logistica cambia, habria que editar muchas filas.
# Solucion: sacar esa informacion a su propia tabla y dejar solo un ID como
# referencia (llave foranea).

# ---- TABLA departamentos -----------------------------------------------------
departamentos = (
    df[["departamento", "jefe_departamento"]]
    .drop_duplicates()
    .sort_values("departamento")
    .reset_index(drop=True)
)
departamentos.insert(0, "id_departamento", range(1, len(departamentos) + 1))
departamentos = departamentos.rename(columns={"departamento": "nombre_departamento"})
sub("Tabla departamentos")
print(departamentos)

# ---- TABLA sucursales --------------------------------------------------------
sucursales = (
    df[["sucursal"]]
    .drop_duplicates()
    .sort_values("sucursal")
    .reset_index(drop=True)
)
sucursales.insert(0, "id_sucursal", range(1, len(sucursales) + 1))
sucursales = sucursales.rename(columns={"sucursal": "nombre_sucursal"})
sub("Tabla sucursales")
print(sucursales)

# ---- TABLA empleados ---------------------------------------------------------
# merge() = el JOIN de SQL pero en pandas. Pegamos los IDs y borramos el texto.
empleados = df.merge(
    departamentos,
    left_on=["departamento", "jefe_departamento"],
    right_on=["nombre_departamento", "jefe_departamento"],
    how="left",
)
empleados = empleados.merge(
    sucursales, left_on="sucursal", right_on="nombre_sucursal", how="left"
)

empleados = empleados[[
    "id_empleado", "nombre_empleado", "id_departamento", "id_sucursal",
    "fecha_ingreso", "salario_base", "bono_pct", "horas_extra_mes",
    "activo", "evaluacion_desempeno",
]]

sub("Tabla empleados (ya sin texto repetido, solo IDs)")
print(empleados.head(10))

# Validacion: ningun empleado se puede quedar sin departamento o sucursal
print("\nValidacion de llaves foraneas:")
print("  Empleados sin id_departamento:", empleados["id_departamento"].isnull().sum())
print("  Empleados sin id_sucursal    :", empleados["id_sucursal"].isnull().sum())

print("\nTablas normalizadas creadas en memoria:")
print(f"  departamentos: {len(departamentos)} filas")
print(f"  sucursales:    {len(sucursales)} filas")
print(f"  empleados:     {len(empleados)} filas")


# =============================================================================
# PASO 6 - RESPONDER LAS PREGUNTAS
# =============================================================================
titulo("PASO 6 - RESPUESTAS")

# ---- PREGUNTA 1 --------------------------------------------------------------
sub("PREGUNTA 1: costo total de nomina por departamento (solo activos)")
activos = df[df["activo"] == "Si"]
nomina = (
    activos.groupby("departamento")["costo_total"]
    .sum()
    .sort_values(ascending=False)
)
print(nomina.to_string())
print(f"\nEmpleados activos: {len(activos)} de {len(df)}")
print(f"Nomina total de activos: {nomina.sum():,.2f}")

# ---- PREGUNTA 2 --------------------------------------------------------------
sub("PREGUNTA 2: correlacion entre horas extra y evaluacion")
datos_corr = df.dropna(subset=["evaluacion_desempeno"])
correlacion = datos_corr["horas_extra_mes"].corr(datos_corr["evaluacion_desempeno"])
print(f"Registros usados: {len(datos_corr)} (se ignoraron {len(df) - len(datos_corr)} sin evaluacion)")
print(f"Coeficiente de correlacion de Pearson: {correlacion:.4f}")

# Como se lee: va de -1 a 1. Cerca de 0 = no hay relacion.
if abs(correlacion) < 0.3:
    fuerza = "DEBIL (practicamente no hay relacion)"
elif abs(correlacion) < 0.7:
    fuerza = "MODERADA"
else:
    fuerza = "FUERTE"
sentido = "positiva (suben juntas)" if correlacion > 0 else "negativa (una sube, la otra baja)"
print(f"Interpretacion: correlacion {fuerza}, {sentido}.")

# ---- PREGUNTA 3 --------------------------------------------------------------
sub("PREGUNTA 3: sucursal con mayor antiguedad promedio")
antiguedad = (
    df.groupby("sucursal")["antiguedad_anios"]
    .mean()
    .sort_values(ascending=False)
)
print(antiguedad.round(2).to_string())
print(f"\nGanadora: {antiguedad.idxmax()} con {antiguedad.max():.2f} años promedio.")

# ---- PREGUNTA 4 --------------------------------------------------------------
sub("PREGUNTA 4: efecto de eliminar duplicados")
diferencia = nomina_con_duplicados - nomina.sum()
print(f"Filas antes de limpiar:        {filas_antes}")
print(f"Filas despues de limpiar:      {filas_despues}")
print(f"Duplicados eliminados:         {filas_antes - filas_despues}")
print(f"Nomina CON duplicados:         {nomina_con_duplicados:,.2f}")
print(f"Nomina SIN duplicados (real):  {nomina.sum():,.2f}")
print(f"Diferencia (dinero fantasma):  {diferencia:,.2f}")
if nomina_con_duplicados:
    print(f"Es decir, estabamos inflando la nomina un {diferencia / nomina_con_duplicados * 100:.2f}%.")

# ---- PREGUNTA 5 --------------------------------------------------------------
sub("PREGUNTA 5: cuartiles de salario")
# qcut parte los datos en 4 grupos con la MISMA CANTIDAD de empleados cada uno.
# Q1 = los sueldos mas bajos ... Q4 = los sueldos mas altos.
df["cuartil_salario"] = pd.qcut(df["salario_base"], 4, labels=["Q1", "Q2", "Q3", "Q4"])

print("Empleados por cuartil:")
print(df["cuartil_salario"].value_counts().sort_index().to_string())

print("\nRango de salario de cada cuartil:")
print(df.groupby("cuartil_salario", observed=True)["salario_base"]
        .agg(["min", "max", "count"]).to_string())

cuartil_alto = df[df["cuartil_salario"] == "Q4"]
conteo_q4 = cuartil_alto["departamento"].value_counts()
print("\nEmpleados en el cuartil mas alto (Q4) por departamento:")
print(conteo_q4.to_string())
print(f"\nDepartamento que concentra mas empleados en Q4: {conteo_q4.idxmax()} ({conteo_q4.max()} empleados).")

tabla_cruzada = pd.crosstab(df["departamento"], df["cuartil_salario"])
print("\nTabla cruzada departamento vs cuartil:")
print(tabla_cruzada.to_string())


# =============================================================================
# PASO 7 - DASHBOARD DE 4 PANELES
# =============================================================================
titulo("PASO 7 - GRAFICO FINAL")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("TiendaMax - Dashboard de Recursos Humanos", fontsize=16, fontweight="bold")

# Panel 1: nomina por departamento
axes[0, 0].bar(nomina.index, nomina.values, color="#4C72B0")
axes[0, 0].set_title("Costo de nomina por departamento (solo activos)")
axes[0, 0].set_ylabel("Costo total")
axes[0, 0].tick_params(axis="x", rotation=45)
for i, v in enumerate(nomina.values):
    axes[0, 0].text(i, v, f"{v/1000:.0f}k", ha="center", va="bottom", fontsize=9)

# Panel 2: horas extra vs evaluacion
axes[0, 1].scatter(
    datos_corr["horas_extra_mes"], datos_corr["evaluacion_desempeno"],
    color="#DD8452", s=80, alpha=0.7, edgecolors="black",
)
axes[0, 1].set_title(f"Horas extra vs evaluacion (r = {correlacion:.3f})")
axes[0, 1].set_xlabel("Horas extra al mes")
axes[0, 1].set_ylabel("Evaluacion de desempeño")
axes[0, 1].grid(alpha=0.3)

# Panel 3: antiguedad por sucursal
axes[1, 0].bar(antiguedad.index, antiguedad.values, color="#55A868")
axes[1, 0].set_title("Antiguedad promedio por sucursal")
axes[1, 0].set_ylabel("Años")
for i, v in enumerate(antiguedad.values):
    axes[1, 0].text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)

# Panel 4: empleados por cuartil salarial
conteo_cuartiles = df["cuartil_salario"].value_counts().sort_index()
axes[1, 1].bar(conteo_cuartiles.index.astype(str), conteo_cuartiles.values, color="#C44E52")
axes[1, 1].set_title("Distribucion de empleados por cuartil salarial")
axes[1, 1].set_ylabel("Cantidad de empleados")
for i, v in enumerate(conteo_cuartiles.values):
    axes[1, 1].text(i, v, str(v), ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig("salidas/ej2_dashboard.png", dpi=150)
print("Grafico guardado en salidas/ej2_dashboard.png")
# plt.show()  # descomenta esta linea si quieres que se abra la ventana del grafico

# =============================================================================
# PASO 8 - CARGAR DIRECTAMENTE A POSTGRESQL
# =============================================================================
titulo("PASO 8 - CARGAR TABLAS NORMALIZADAS DIRECTAMENTE A POSTGRESQL")

print("Los DataFrames normalizados siguen en memoria.")
print("No se generan CSV intermedios para departamentos, sucursales ni empleados.")

cargar_tablas_normalizadas(
    departamentos=departamentos,
    sucursales=sucursales,
    empleados=empleados,
)

titulo("LISTO. PIPELINE COMPLETO: CSV -> LIMPIEZA -> NORMALIZACION -> POSTGRESQL")
