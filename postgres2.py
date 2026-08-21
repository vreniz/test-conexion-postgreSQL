import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# =============================================================================
# DATOS DE CONEXION A POSTGRESQL
# =============================================================================
USUARIO = "postgres"
PASSWORD = "1234"  # Cambia esto por tu contraseña real
HOST = "localhost"
PUERTO = 5432
BASE_DATOS = "cruises_dw"


def _crear_engine():
    """Crea la conexión a PostgreSQL.""" # postgresql+psycopg2://USUARIO:PASSWORD@HOST:PUERTO/BASE_DATOS
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=USUARIO,
        password=PASSWORD,
        host=HOST,
        port=PUERTO,
        database=BASE_DATOS,
    )
    return create_engine(url, future=True)


def _validar_star_schema(
    ships, countries, suites, packages, booking_sources, bookings_fact
):
    """Valida el contrato de datos del esquema estrella antes de escribir."""

    contratos = {
        "ships_dim": {
            "id_ship",
            "ship_name",
            "company",
            "route_type",
            "total_cabins",
            "total_crew",
        },
        "countries_dim": {"id_country", "guest_country"},
        "suites_dim": {"id_suite", "suite_type"},
        "packages_dim": {"id_package", "package"},
        "booking_sources_dim": {"id_booking_source", "booking_source"},
        "bookings_fact": {
            "booking_id",
            "travel_date",
            "booking_date",
            "id_ship",
            "id_country",
            "id_suite",
            "id_package",
            "id_booking_source",
            "lead_time_days",
            "nights_of_stay",
            "booked_cabins",
            "passengers_on_booking",
            "cycle_occupancy_percentage",
            "total_reservation_income_usd",
            "average_daily_guest_spending_usd",
            "satisfaction_score",
        },
    }

    # 1. Validar nombres de columnas
    for nombre, df, esperadas in [
        ("ships_dim", ships, contratos["ships_dim"]),
        ("countries_dim", countries, contratos["countries_dim"]),
        ("suites_dim", suites, contratos["suites_dim"]),
        ("packages_dim", packages, contratos["packages_dim"]),
        (
            "booking_sources_dim",
            booking_sources,
            contratos["booking_sources_dim"],
        ),
        ("bookings_fact", bookings_fact, contratos["bookings_fact"]),
    ]:
        if set(df.columns) != esperadas:
            raise ValueError(
                f"Columnas inesperadas en {nombre}: {df.columns.tolist()}"
            )

    # 2. Validar Llaves Primarias únicas
    for nombre, df, col_id in [
        ("ships_dim", ships, "id_ship"),
        ("countries_dim", countries, "id_country"),
        ("suites_dim", suites, "id_suite"),
        ("packages_dim", packages, "id_package"),
        ("booking_sources_dim", booking_sources, "id_booking_source"),
        ("bookings_fact", bookings_fact, "booking_id"),
    ]:
        if df[col_id].duplicated().any():
            raise ValueError(
                f"Hay IDs duplicados en la columna {col_id} de {nombre}."
            )

    # 3. Validar Nulos en llaves foráneas
    llaves_foraneas = [
        "id_ship",
        "id_country",
        "id_suite",
        "id_package",
        "id_booking_source",
    ]
    for fk in llaves_foraneas:
        if bookings_fact[fk].isna().any():
            raise ValueError(
                f"Error Crítico: Hay registros en la tabla de hechos con {fk} nulo."
            )


def cargar_esquema_estrella(
    ships, countries, suites, packages, booking_sources, bookings_fact
):
    """Carga el modelo multidimensional completo en PostgreSQL dentro de una transacción."""

    _validar_star_schema(
        ships, countries, suites, packages, booking_sources, bookings_fact
    )

    engine = _crear_engine()

    # 1. Probar Conexión
    with engine.connect() as conexion:
        version = conexion.execute(text("SELECT version();")).scalar()
        print("\nConexión exitosa a PostgreSQL.")
        print("Versión del motor:", version[:80], "...")

    # 2. Ejecutar DDL e Ingesta Atómica
    with engine.begin() as conexion:

        print("Limpiando tablas previas...")
        conexion.execute(text("DROP TABLE IF EXISTS bookings_fact CASCADE;"))
        conexion.execute(text("DROP TABLE IF EXISTS ships_dim CASCADE;"))
        conexion.execute(text("DROP TABLE IF EXISTS countries_dim CASCADE;"))
        conexion.execute(text("DROP TABLE IF EXISTS suites_dim CASCADE;"))
        conexion.execute(text("DROP TABLE IF EXISTS packages_dim CASCADE;"))
        conexion.execute(
            text("DROP TABLE IF EXISTS booking_sources_dim CASCADE;")
        )

        print("Creando tablas de dimensiones...")
        conexion.execute(
            text(
                """
            CREATE TABLE ships_dim (
                id_ship SERIAL PRIMARY KEY,
                ship_name VARCHAR(150) NOT NULL,
                company VARCHAR(150) NOT NULL,
                route_type VARCHAR(100) NOT NULL,
                total_cabins INTEGER NOT NULL,
                total_crew INTEGER NOT NULL,
                CONSTRAINT uq_ship_name UNIQUE (ship_name)
            );

            CREATE TABLE countries_dim (
                id_country SERIAL PRIMARY KEY,
                guest_country VARCHAR(100) NOT NULL,
                CONSTRAINT uq_guest_country UNIQUE (guest_country)
            );

            CREATE TABLE suites_dim (
                id_suite SERIAL PRIMARY KEY,
                suite_type VARCHAR(50) NOT NULL,
                CONSTRAINT uq_suite_type UNIQUE (suite_type)
            );

            CREATE TABLE packages_dim (
                id_package SERIAL PRIMARY KEY,
                package VARCHAR(100) NOT NULL,
                CONSTRAINT uq_package UNIQUE (package)
            );

            CREATE TABLE booking_sources_dim (
                id_booking_source SERIAL PRIMARY KEY,
                booking_source VARCHAR(50) NOT NULL,
                CONSTRAINT uq_booking_source UNIQUE (booking_source)
            );
        """
            )
        )

        print("Creando tabla de hechos (bookings_fact)...")
        conexion.execute(
            text(
                """
            CREATE TABLE bookings_fact (
                booking_id SERIAL PRIMARY KEY,
                travel_date DATE NOT NULL,
                booking_date DATE NOT NULL,
                
                id_ship INTEGER NOT NULL,
                id_country INTEGER NOT NULL,
                id_suite INTEGER NOT NULL,
                id_package INTEGER NOT NULL,
                id_booking_source INTEGER NOT NULL,
                
                lead_time_days INTEGER NOT NULL,
                nights_of_stay INTEGER NOT NULL,
                booked_cabins INTEGER NOT NULL,
                passengers_on_booking INTEGER NOT NULL,
                
                cycle_occupancy_percentage NUMERIC(5, 2) NOT NULL,
                total_reservation_income_usd NUMERIC(12, 2) NOT NULL,
                average_daily_guest_spending_usd NUMERIC(10, 2) NOT NULL,
                satisfaction_score NUMERIC(3, 1),

                CONSTRAINT fk_fact_ships FOREIGN KEY (id_ship) REFERENCES ships_dim(id_ship),
                CONSTRAINT fk_fact_countries FOREIGN KEY (id_country) REFERENCES countries_dim(id_country),
                CONSTRAINT fk_fact_suites FOREIGN KEY (id_suite) REFERENCES suites_dim(id_suite),
                CONSTRAINT fk_fact_packages FOREIGN KEY (id_package) REFERENCES packages_dim(id_package),
                CONSTRAINT fk_fact_sources FOREIGN KEY (id_booking_source) REFERENCES booking_sources_dim(id_booking_source),
                
                CONSTRAINT ck_lead_time_positivo CHECK (lead_time_days >= 0),
                CONSTRAINT ck_nights_positivo CHECK (nights_of_stay > 0),
                CONSTRAINT ck_cabins_positivo CHECK (booked_cabins > 0),
                CONSTRAINT ck_passengers_positivo CHECK (passengers_on_booking > 0),
                CONSTRAINT ck_income_positivo CHECK (total_reservation_income_usd >= 0),
                CONSTRAINT ck_spending_positivo CHECK (average_daily_guest_spending_usd >= 0),
                CONSTRAINT ck_satisfaction_rango CHECK (satisfaction_score BETWEEN 0.0 AND 5.0)
            );
        """
            )
        )

        print("Insertando datos en las dimensiones...")
        ships.to_sql(
            "ships_dim", conexion, if_exists="append", index=False, method="multi"
        )
        countries.to_sql(
            "countries_dim",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )
        suites.to_sql(
            "suites_dim",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )
        packages.to_sql(
            "packages_dim",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )
        booking_sources.to_sql(
            "booking_sources_dim",
            conexion,
            if_exists="append",
            index=False,
            method="multi",
        )

        print("Insertando datos en la tabla de hechos en lotes (77,040 filas)...")
        # Uso de chunksize=5000 para rápida inserción por lotes
        bookings_fact.to_sql(
            "bookings_fact",
            conexion,
            if_exists="append",
            index=False,
            chunksize=5000,
            method="multi",
        )

        print("Creando índices de optimización...")
        # Crear los índices DESPUÉS de insertar agiliza la inserción
        for fk in [
            "id_ship",
            "id_country",
            "id_suite",
            "id_package",
            "id_booking_source",
            "travel_date",
            "booking_date",
        ]:
            conexion.execute(
                text(f"CREATE INDEX idx_fact_{fk} ON bookings_fact({fk});")
            )

        # 3. Validación final de conteos
        print("Validando consistencia de la carga...")
        conteos = (
            conexion.execute(
                text(
                    """
            SELECT
                (SELECT COUNT(*) FROM ships_dim) AS ships,
                (SELECT COUNT(*) FROM countries_dim) AS countries,
                (SELECT COUNT(*) FROM suites_dim) AS suites,
                (SELECT COUNT(*) FROM packages_dim) AS packages,
                (SELECT COUNT(*) FROM booking_sources_dim) AS sources,
                (SELECT COUNT(*) FROM bookings_fact) AS facts;
        """
                )
            )
            .mappings()
            .one()
        )

        if conteos["facts"] != len(bookings_fact):
            raise ValueError(
                f"Divergencia de datos: El DataFrame tiene {len(bookings_fact)} filas, "
                f"pero Postgres registró {conteos['facts']} filas."
            )

        print("\n🚀 ¡Carga completada exitosamente sin errores!")
        print(
            f" -> Dimensiones cargadas: Ships({conteos['ships']}), Countries({conteos['countries']}), "
            f"Suites({conteos['suites']}), Packages({conteos['packages']}), Sources({conteos['sources']})"
        )
        print(f" -> Tabla de Hechos cargada: Bookings({conteos['facts']} filas)")

        # 4. Mostrar vista previa (primeros 5 registros directamente consultados de Postgres)
        print("\n--- VISTA PREVIA DE LOS DATOS CARGADOS (PRIMERAS 5 FILAS) ---")
        preview_df = pd.read_sql_query(
            "SELECT * FROM bookings_fact LIMIT 5;", conexion
        )
        print(preview_df.to_string(index=False))