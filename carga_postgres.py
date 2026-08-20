import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# =============================================================================
# DATOS DE CONEXION A POSTGRESQL
# =============================================================================
USUARIO = "postgres"
PASSWORD = "1234"       # Cambia esto por tu contraseña real
HOST = "localhost"
PUERTO = 5432
BASE_DATOS = "tiendamax"


def _crear_engine():
    """Crea la conexión a PostgreSQL."""
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=USUARIO,
        password=PASSWORD,
        host=HOST,
        port=PUERTO,
        database=BASE_DATOS,
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
            f"Columnas inesperadas en departamentos: "
            f"{departamentos.columns.tolist()}"
        )

    if set(sucursales.columns) != esperadas_sucursales:
        raise ValueError(
            f"Columnas inesperadas en sucursales: "
            f"{sucursales.columns.tolist()}"
        )

    if set(empleados.columns) != esperadas_empleados:
        raise ValueError(
            f"Columnas inesperadas en empleados: "
            f"{empleados.columns.tolist()}"
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

    Para este ejercicio ETL reproducible, se reemplaza el contenido de
    las tres tablas dentro de una sola transacción. Si algo falla,
    PostgreSQL revierte los cambios.
    """
    _validar_dataframe(departamentos, sucursales, empleados)

    engine = _crear_engine()

    # -------------------------------------------------------------------------
    # 1. PROBAR CONEXION
    # -------------------------------------------------------------------------
    with engine.connect() as conexion:
        version = conexion.execute(text("SELECT version();")).scalar()

        print("\nConexión exitosa.")
        print("PostgreSQL responde:", version[:80], "...")

    # -------------------------------------------------------------------------
    # 2. CREAR TABLAS Y CARGAR DATOS
    # -------------------------------------------------------------------------
    with engine.begin() as conexion:

        # Se eliminan primero las tablas hijas y luego las tablas padre.
        conexion.execute(text("DROP TABLE IF EXISTS empleados;"))
        conexion.execute(text("DROP TABLE IF EXISTS sucursales;"))
        conexion.execute(text("DROP TABLE IF EXISTS departamentos;"))

        # ---------------------------------------------------------------------
        # TABLA DEPARTAMENTOS
        # ---------------------------------------------------------------------
        conexion.execute(text("""
            CREATE TABLE departamentos (
                id_departamento INTEGER PRIMARY KEY,
                nombre_departamento VARCHAR(100) NOT NULL,
                jefe_departamento VARCHAR(150) NOT NULL,

                CONSTRAINT uq_departamento_nombre
                    UNIQUE (nombre_departamento)
            );
        """))

        # ---------------------------------------------------------------------
        # TABLA SUCURSALES
        # ---------------------------------------------------------------------
        conexion.execute(text("""
            CREATE TABLE sucursales (
                id_sucursal INTEGER PRIMARY KEY,
                nombre_sucursal VARCHAR(100) NOT NULL,

                CONSTRAINT uq_sucursal_nombre
                    UNIQUE (nombre_sucursal)
            );
        """))

        # ---------------------------------------------------------------------
        # TABLA EMPLEADOS
        # ---------------------------------------------------------------------
        conexion.execute(text("""
            CREATE TABLE empleados (
                id_empleado VARCHAR(10) PRIMARY KEY,
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
                    REFERENCES sucursales(id_sucursal),

                CONSTRAINT ck_salario_positivo
                    CHECK (salario_base >= 0),

                CONSTRAINT ck_bono_valido
                    CHECK (bono_pct >= 0),

                CONSTRAINT ck_horas_extra_validas
                    CHECK (horas_extra_mes >= 0),

                CONSTRAINT ck_activo_valido
                    CHECK (activo IN ('Si', 'No'))
            );
        """))

        # ---------------------------------------------------------------------
        # 3. INDICES PARA LAS LLAVES FORANEAS
        # ---------------------------------------------------------------------
        conexion.execute(text("""
            CREATE INDEX idx_empleados_departamento
            ON empleados(id_departamento);
        """))

        conexion.execute(text("""
            CREATE INDEX idx_empleados_sucursal
            ON empleados(id_sucursal);
        """))

        # ---------------------------------------------------------------------
        # 4. CARGAR DATAFRAMES DIRECTAMENTE
        # ---------------------------------------------------------------------
        # NO se usan CSV aquí.
        # Estos datos vienen directamente de los DataFrames normalizados.
        departamentos.to_sql(
            "departamentos",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )

        sucursales.to_sql(
            "sucursales",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )

        empleados.to_sql(
            "empleados",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )

        # ---------------------------------------------------------------------
        # 5. VALIDAR QUE LA CARGA COINCIDE CON LOS DATAFRAMES
        # ---------------------------------------------------------------------
        conteos = conexion.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM departamentos) AS departamentos,
                (SELECT COUNT(*) FROM sucursales) AS sucursales,
                (SELECT COUNT(*) FROM empleados) AS empleados;
        """)).mappings().one()

        if conteos["departamentos"] != len(departamentos):
            raise RuntimeError(
                "El conteo de departamentos no coincide."
            )

        if conteos["sucursales"] != len(sucursales):
            raise RuntimeError(
                "El conteo de sucursales no coincide."
            )

        if conteos["empleados"] != len(empleados):
            raise RuntimeError(
                "El conteo de empleados no coincide."
            )

    print("\nCarga terminada correctamente.")
    print(f"  departamentos: {len(departamentos)} filas")
    print(f"  sucursales:    {len(sucursales)} filas")
    print(f"  empleados:     {len(empleados)} filas")
    print("Las tablas, llaves y restricciones quedaron creadas en PostgreSQL.")