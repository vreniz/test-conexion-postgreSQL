"""
===============================================================================
CARGA DE TABLAS NORMALIZADAS A POSTGRESQL
===============================================================================
Este módulo NO lee CSV.

Recibe tres DataFrames ya limpios y normalizados desde
analisis_empleados_postgres.py y los carga directamente a PostgreSQL.
"""
import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def _crear_engine():
    """Crea la conexión usando variables de entorno."""
    usuario = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")
    base_datos = os.getenv("POSTGRES_DB", "tiendamax")

    if not password:
        raise RuntimeError(
            "Falta POSTGRES_PASSWORD. Configúrala como variable de entorno."
        )

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=usuario,
        password=password,
        host=host,
        port=int(puerto),
        database=base_datos,
    )
    return create_engine(url, future=True)


def _validar_dataframe(departamentos, sucursales, empleados):
    """Valida el contrato de datos antes de escribir en PostgreSQL."""
    esperadas_departamentos = {
        "id_departamento", "nombre_departamento", "jefe_departamento"
    }
    esperadas_sucursales = {"id_sucursal", "nombre_sucursal"}
    esperadas_empleados = {
        "id_empleado", "nombre_empleado", "id_departamento", "id_sucursal",
        "fecha_ingreso", "salario_base", "bono_pct", "horas_extra_mes",
        "activo", "evaluacion_desempeno"
    }

    if set(departamentos.columns) != esperadas_departamentos:
        raise ValueError(
            f"Columnas inesperadas en departamentos: {departamentos.columns.tolist()}"
        )
    if set(sucursales.columns) != esperadas_sucursales:
        raise ValueError(
            f"Columnas inesperadas en sucursales: {sucursales.columns.tolist()}"
        )
    if set(empleados.columns) != esperadas_empleados:
        raise ValueError(
            f"Columnas inesperadas en empleados: {empleados.columns.tolist()}"
        )

    if departamentos["id_departamento"].duplicated().any():
        raise ValueError("Hay IDs de departamento duplicados.")
    if sucursales["id_sucursal"].duplicated().any():
        raise ValueError("Hay IDs de sucursal duplicados.")
    if empleados["id_empleado"].duplicated().any():
        raise ValueError("Hay IDs de empleado duplicados.")

    if empleados["id_departamento"].isna().any():
        raise ValueError("Hay empleados sin id_departamento.")
    if empleados["id_sucursal"].isna().any():
        raise ValueError("Hay empleados sin id_sucursal.")


def cargar_tablas_normalizadas(departamentos, sucursales, empleados):
    """
    Carga los DataFrames normalizados directamente en PostgreSQL.

    Para un ejercicio ETL reproducible, se reemplaza el contenido de estas
    tres tablas dentro de una sola transacción. Si algo falla, PostgreSQL
    revierte los cambios.
    """
    _validar_dataframe(departamentos, sucursales, empleados)
    engine = _crear_engine()

    with engine.connect() as conexion:
        version = conexion.execute(text("SELECT version();")).scalar()
        print("\nConexión exitosa.")
        print("PostgreSQL responde:", version[:80], "...")

    with engine.begin() as conexion:
        # Se eliminan primero los hijos y luego las tablas padre.
        conexion.execute(text("DROP TABLE IF EXISTS empleados;"))
        conexion.execute(text("DROP TABLE IF EXISTS sucursales;"))
        conexion.execute(text("DROP TABLE IF EXISTS departamentos;"))

        conexion.execute(text("""
            CREATE TABLE departamentos (
                id_departamento INTEGER PRIMARY KEY,
                nombre_departamento VARCHAR(100) NOT NULL,
                jefe_departamento VARCHAR(150) NOT NULL
            );
        """))

        conexion.execute(text("""
            CREATE TABLE sucursales (
                id_sucursal INTEGER PRIMARY KEY,
                nombre_sucursal VARCHAR(100) NOT NULL
            );
        """))

        conexion.execute(text("""
            CREATE TABLE empleados (
                id_empleado INTEGER PRIMARY KEY,
                nombre_empleado VARCHAR(150) NOT NULL,
                id_departamento INTEGER NOT NULL,
                id_sucursal INTEGER NOT NULL,
                fecha_ingreso DATE NOT NULL,
                salario_base NUMERIC(12, 2) NOT NULL,
                bono_pct NUMERIC(8, 4) NOT NULL,
                horas_extra_mes INTEGER NOT NULL,
                activo VARCHAR(2) NOT NULL,
                evaluacion_desempeno NUMERIC(5, 2),
                CONSTRAINT fk_empleado_departamento
                    FOREIGN KEY (id_departamento)
                    REFERENCES departamentos(id_departamento),
                CONSTRAINT fk_empleado_sucursal
                    FOREIGN KEY (id_sucursal)
                    REFERENCES sucursales(id_sucursal)
            );
        """))

        # Aquí sí usamos to_sql(), pero NO desde CSV:
        # los datos vienen directamente de los DataFrames normalizados.
        departamentos.to_sql(
            "departamentos", conexion, if_exists="append", index=False, method="multi"
        )
        sucursales.to_sql(
            "sucursales", conexion, if_exists="append", index=False, method="multi"
        )
        empleados.to_sql(
            "empleados", conexion, if_exists="append", index=False, method="multi"
        )

        conteos = conexion.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM departamentos) AS departamentos,
                (SELECT COUNT(*) FROM sucursales) AS sucursales,
                (SELECT COUNT(*) FROM empleados) AS empleados;
        """)).mappings().one()

        if conteos["departamentos"] != len(departamentos):
            raise RuntimeError("El conteo de departamentos no coincide.")
        if conteos["sucursales"] != len(sucursales):
            raise RuntimeError("El conteo de sucursales no coincide.")
        if conteos["empleados"] != len(empleados):
            raise RuntimeError("El conteo de empleados no coincide.")

    print("\nCarga terminada correctamente.")
    print(f"  departamentos: {len(departamentos)} filas")
    print(f"  sucursales:    {len(sucursales)} filas")
    print(f"  empleados:     {len(empleados)} filas")
    print("Las tablas y llaves quedaron creadas en PostgreSQL.")
