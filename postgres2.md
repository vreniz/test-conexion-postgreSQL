# BREAKDOWN POSTGRESQL DATA UPLOAD 

## 1. Importe de librerias
```
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
``` 
` from sqlalchemy import create_engine, text:` Importa dos herramientas clave de SQLAlchemy (el motor de conexión a bases de datos más popular de Python): 

`create_engine:` Es la función que genera el "motor" o gestor de conexiones con tu base de datos (por ejemplo, PostgreSQL, MySQL o SQLite).

`text:` Permite escribir y ejecutar consultas SQL en texto plano (como SELECT * FROM tabla) de forma segura y compatible con los estándares modernos de la librería.

`from sqlalchemy.engine import URL:` Importa un módulo que te permite estructurar los datos de conexión (usuario, contraseña, host, puerto y base de datos) como un objeto estructurado, evitando concatenar textos largos y previniendo errores de formato.


## 2. Configuración de Credenciales
```
# =============================================================================
# DATOS DE CONEXION A POSTGRESQL
# =============================================================================
USUARIO = "postgres"
PASSWORD = "1234"  # Cambia esto por tu contraseña real
HOST = "localhost"
PUERTO = 5432
BASE_DATOS = "cruises_dw"
```
> Variables globales: Almacenan los parámetros de acceso a PostgreSQL (cruises_dw es la base de datos del Data Warehouse).

## 3. Creacion de la conexión a PostgreSQL (fuente de la conexión)
```
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
```
`def _crear_engine():` El guion bajo _ al inicio indica que es una función privada/interna del módulo.

`URL.create(...):` Construye la estructura de conexión. Especifica postgresql+psycopg2 como el conector/driver de Python hacia PostgreSQL.

`create_engine(url, future=True)`: Genera el motor de SQLAlchemy. future=True activa la sintaxis moderna de SQLAlchemy (versión 2.0+)

## 4. Funcion de control de calidad

```
def _validar_star_schema(
    ships, countries, suites, packages, booking_sources, bookings_fact
):
```
> Recibe los 6 DataFrames de Pandas que contienen los datos que van a ser insertados.

```
contratos = {
        "ships_dim": {
            "id_ship",
            "ship_name",
            "company",
            "route_type",
            "total_cabins",
            "total_crew",
        },
        ...
    }
```
`contratos:` Un diccionario que define la estructura esperada ("contrato de datos"). Cada clave contiene un conjunto (set) con los nombres exactos de las columnas necesarias.

```
# 1. Validar nombres de columnas
    for nombre, df, esperadas in [
        ("ships_dim", ships, contratos["ships_dim"]),
        ...
    ]:
        if set(df.columns) != esperadas:
            raise ValueError(
                f"Columnas inesperadas en {nombre}: {df.columns.tolist()}"
            )
```
Recorre uno a uno los `DataFrames` y compara si las columnas presentes `(set(df.columns))` son exactamente iguales a las definidas en el contrato. Si falta o sobra una columna, detiene el programa lanzando un ValueError.

```
# 2. Validar Llaves Primarias únicas
    for nombre, df, col_id in [
        ("ships_dim", ships, "id_ship"),
        ...
    ]:
        if df[col_id].duplicated().any():
            raise ValueError(
                f"Hay IDs duplicados en la columna {col_id} de {nombre}."
            )
```
df[col_id].duplicated().any(): Revisa si existen IDs repetidos en los identificadores de cada tabla. Si hay duplicados en una llave primaria, interrumpe el proceso.

```
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
```
Revisa la tabla de hechos `(bookings_fact)` y verifica con `.isna().any()` que ningún registro tenga valores vacíos/nulos en las llaves foráneas `(id_ship, id_country, etc.)`.

## 5. Función Principal de Carga (ETL)
```
def cargar_esquema_estrella(
    ships, countries, suites, packages, booking_sources, bookings_fact
):
```

Inicia la función que creará el modelo dimensional e insertará la información en la base de datos.

```
_validar_star_schema(
        ships, countries, suites, packages, booking_sources, bookings_fact
    )
    engine = _crear_engine()
```

Ejecuta primero las validaciones de calidad. Si todo es correcto, obtiene el motor de conexión a PostgreSQL.

```
# 1. Probar Conexión
    with engine.connect() as conexion:
        version = conexion.execute(text("SELECT version();")).scalar()
        print("\nConexión exitosa a PostgreSQL.")
        print("Versión del motor:", version[:80], "...")
```

`with engine.connect() as conexion:` : Abre una conexión simple.

`conexion.execute(text("SELECT version();")).scalar()`: Ejecuta SQL directo para preguntar la versión de Postgres instalada y obtiene el valor directo con `.scalar()`

## 6. Transacción Atómica y Creación de Tablas (DDL)
```
# 2. Ejecutar DDL e Ingesta Atómica
    with engine.begin() as conexion:
```
`with engine.begin() as conexion:`: CRÍTICO. Inicia una transacción atómica. Si ocurre un error en cualquier instrucción dentro de este bloque with, la base de datos cancelará automáticamente todo lo hecho (ROLLBACK), evitando dejar tablas creadas a la mitad.

```
print("Limpiando tablas previas...")
        conexion.execute(text("DROP TABLE IF EXISTS bookings_fact CASCADE;"))
        ...
```
Borra las tablas si ya existían previamente. Se usa CASCADE para eliminar también las restricciones de clave foránea asociadas.

```
print("Creando tablas de dimensiones...")
        conexion.execute(text("""
            CREATE TABLE ships_dim (
                id_ship SERIAL PRIMARY KEY,
                ship_name VARCHAR(150) NOT NULL,
                company VARCHAR(150) NOT NULL,
                route_type VARCHAR(100) NOT NULL,
                total_cabins INTEGER NOT NULL,
                total_crew INTEGER NOT NULL,
                CONSTRAINT uq_ship_name UNIQUE (ship_name)
            );
            ...
        """))
```
Ejecuta código SQL para crear las tablas de dimensiones `(ships_dim, countries_dim, etc.)`.

`SERIAL`: Campo autoincremental de Postgres.

`PRIMARY KEY`: Establece el identificador único.

`UNIQUE`: Evita nombres o registros repetidos a nivel de SQL

```
print("Creando tabla de hechos (bookings_fact)...")
        conexion.execute(text("""
            CREATE TABLE bookings_fact (
                booking_id SERIAL PRIMARY KEY,
                travel_date DATE NOT NULL,
                ...
                CONSTRAINT fk_fact_ships FOREIGN KEY (id_ship) REFERENCES ships_dim(id_ship),
                ...
                CONSTRAINT ck_lead_time_positivo CHECK (lead_time_days >= 0),
                ...
            );
        """))
```

Crea la tabla principal del modelo estrella (bookings_fact).

`FOREIGN KEY (...) REFERENCES ...`: Define la integridad referencial con las tablas de dimensiones.

`CHECK (...)`: Aplica reglas de negocio en la base de datos (ej. las noches de estadía deben ser mayores a 0, el puntaje de satisfacción debe estar entre 0.0 y 5.0).

## 7. Inserción de Datos

```
print("Insertando datos en las dimensiones...")
        ships.to_sql(
            "ships_dim", conexion, if_exists="append", index=False, method="multi"
        )
        ...
```

`to_sql(...)`: Método de Pandas para escribir el DataFrame directamente en Postgres.

`if_exists="append"`: Agrega las filas a la tabla recién creada.

`index=False`: Ignora el índice numérico propio de Pandas.

`method="multi"`: Agrupa múltiples inserciones en una sola consulta `SQL (INSERT INTO ... VALUES (...), (...))` para que sea mucho más rápido.

```
print("Insertando datos en la tabla de hechos en lotes (77,040 filas)...")
        bookings_fact.to_sql(
            "bookings_fact",
            conexion,
            if_exists="append",
            index=False,
            chunksize=5000,
            method="multi",
        )
```

`chunksize=5000`: Inserta la tabla de hechos procesando bloques de 5,000 filas a la vez. Esto evita saturar la memoria RAM o la conexión a la base de datos con ~77 mil registros simultáneos.

## 8. Creación de Índices y Verificación Final

```
print("Creando índices de optimización...")
        for fk in [
            "id_ship", "id_country", "id_suite", "id_package",
            "id_booking_source", "travel_date", "booking_date",
        ]:
            conexion.execute(
                text(f"CREATE INDEX idx_fact_{fk} ON bookings_fact({fk});")
            )
```
Crea índices en PostgreSQL (CREATE INDEX) para acelerar las futuras consultas analíticas sobre las llaves foráneas y fechas. Nota: Se crean después de la inserción de datos para hacer el proceso de carga mucho más rápido.

```
print("Validando consistencia de la carga...")
        conteos = (
            conexion.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM ships_dim) AS ships,
                ...
                (SELECT COUNT(*) FROM bookings_fact) AS facts;
            """))
            .mappings()
            .one()
        )
```

Consulta con SQL los conteos reales de filas creadas en PostgreSQL.

`.mappings():` Convierte los resultados de SQL en un formato tipo diccionario de Python `({'ships': 10, 'facts': 77040})`.

`.one()`: Retorna exactamente esa fila de resultado.

```
if conteos["facts"] != len(bookings_fact):
            raise ValueError(
                f"Divergencia de datos: El DataFrame tiene {len(bookings_fact)} filas, "
                f"pero Postgres registró {conteos['facts']} filas."
            )
```

Compara que las filas en Postgres coincidan exactamente con la cantidad de filas que tenía el DataFrame en Python. Si difieren, interrumpe la transacción.

```
print("\n🚀 ¡Carga completada exitosamente sin errores!")
        ...
```
Muestra resúmenes por consola confirmando que todo salió bien.


```
# 4. Mostrar vista previa
        print("\n--- VISTA PREVIA DE LOS DATOS CARGADOS (PRIMERAS 5 FILAS) ---")
        preview_df = pd.read_sql_query(
            "SELECT * FROM bookings_fact LIMIT 5;", conexion
        )
        print(preview_df.to_string(index=False))
```
`pd.read_sql_query(...)`: Consulta las primeras 5 filas insertadas directamente desde PostgreSQL y las imprime en la terminal para confirmar visualmente el resultado final.