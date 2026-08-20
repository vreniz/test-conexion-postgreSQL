
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

