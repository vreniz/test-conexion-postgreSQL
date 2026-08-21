import pandas as pd
import os
from postgres import cargar_esquema_estrella


# Crea la carpeta donde vamos a guardar los resultados
os.makedirs("salidas2", exist_ok=True)

# Hace que pandas imprima todas las columnas sin cortarlas
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

# Estilo de titulo y subtitulo para separar cada paso en la consola 
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

df_original = pd.read_csv("cruiseships.csv")

df = df_original.copy() # saving a copy of the original dataframe 

print(f"El archivo tiene {df.shape[0]} filas y {df.shape[1]} columnas.")
sub("Primeras 5 filas")
print(df.head())

titulo("Información del DataFrame for cleaning")

sub("Estadísticas descriptivas")
print(df.describe())

print("\n🚨 ---  NULL VALUE AUDIT ---")
print(df.isnull().sum())

sub("Información del DataFrame")
print(df.info())



titulo("PASO 2 - LIMPIEZA DE DATOS")

# Cleaning and Feature Conversion
# Convert date columns to datetime format

print("Tipo antes del cambio (travel_date):", df['travel_date'].dtype)
print("Tipo antes del cambio (booking_date):", df['booking_date'].dtype)
# After Converting date columns to datetime format

df['travel_date'] = pd.to_datetime(df['travel_date'])
df['booking_date'] = pd.to_datetime(df['booking_date'])

print("Tipo después del cambio (travel_date):", df['travel_date'].dtype)
print("Tipo después del cambio (booking_date):", df['booking_date'].dtype)

# Check for duplicates
print("Número de filas duplicadas:", df.duplicated().sum())

# Handle duplicate rows if present
initial_count = len(df)
df = df.drop_duplicates()
print(f"\n Removed {initial_count - len(df)} duplicate records. Total clean records: {len(df)}")

# =============================================================================
# PASO  - NORMALIZACION A 3FN
# =============================================================================
titulo("PASO  - NORMALIZAR EN 3 TABLAS (3FN)")



# =============================================================================
# STEP 5 - NORMALIZATION INTO STAR SCHEMA
# =============================================================================
titulo("STEP 5 - NORMALIZE INTO STAR SCHEMA")


# =============================================================================
# SHIPS DIMENSION
# =============================================================================

# Each ship appears many times in the original dataset.
# We extract the information that describes each ship into a dimension table.

ships_dim = (
    df[
        [
            "ship_name",
            "company",
            "route_type",
            "total_cabins",
            "total_crew"
        ]
    ]
    .drop_duplicates(ignore_index=True)
    .sort_values("ship_name")
    .reset_index(drop=True)
)

# Create ship ID
ships_dim.insert(
    0,
    "id_ship",
    range(1, len(ships_dim) + 1)
)

sub("ships_dim")
print(ships_dim.to_string(index=False))


# =============================================================================
# COUNTRIES DIMENSION
# =============================================================================

# Each country appears in many bookings.
# We create a separate dimension table.

countries_dim = (
    df[
        [
            "guest_country"
        ]
    ]
    .drop_duplicates(ignore_index=True)
    .sort_values("guest_country")
    .reset_index(drop=True)
)

# Create country ID
countries_dim.insert(
    0,
    "id_country",
    range(1, len(countries_dim) + 1)
)

sub("countries_dim")
print(countries_dim.to_string(index=False))


# =============================================================================
# SUITES DIMENSION
# =============================================================================

# Extract the different suite types.

suites_dim = (
    df[
        [
            "suite_type"
        ]
    ]
    .drop_duplicates(ignore_index=True)
    .sort_values("suite_type")
    .reset_index(drop=True)
)

# Create suite ID
suites_dim.insert(
    0,
    "id_suite",
    range(1, len(suites_dim) + 1)
)

sub("suites_dim")
print(suites_dim.to_string(index=False))


# =============================================================================
# PACKAGES DIMENSION
# =============================================================================

# Extract the different packages available in the dataset.

packages_dim = (
    df[
        [
            "package"
        ]
    ]
    .drop_duplicates(ignore_index=True)
    .sort_values("package")
    .reset_index(drop=True)
)

# Create package ID
packages_dim.insert(
    0,
    "id_package",
    range(1, len(packages_dim) + 1)
)


sub("packages_dim")
print(packages_dim.to_string(index=False))


# =============================================================================
# BOOKING SOURCES DIMENSION
# =============================================================================

# Extract the different booking channels.

booking_sources_dim = (
    df[
        [
            "booking_source"
        ]
    ]
    .drop_duplicates(ignore_index=True)
    .sort_values("booking_source")
    .reset_index(drop=True)
)

# Create booking source ID
booking_sources_dim.insert(
    0,
    "id_booking_source",
    range(1, len(booking_sources_dim) + 1)
)

sub("booking_sources_dim")
print(booking_sources_dim.to_string(index=False))


# =============================================================================
# MERGE DIMENSION IDs INTO THE ORIGINAL DATAFRAME
# =============================================================================

# merge() works like a SQL JOIN.
# We add the dimension IDs to the original dataframe.

df = df.merge(
    ships_dim,
    on=[
        "ship_name",
        "company",
        "route_type",
        "total_cabins",
        "total_crew"
    ],
    how="left"
)

df = df.merge(
    countries_dim,
    on="guest_country",
    how="left"
)

df = df.merge(
    suites_dim,
    on="suite_type",
    how="left"
)

df = df.merge(
    packages_dim,
    on="package",
    how="left"
)

df = df.merge(
    booking_sources_dim,
    on="booking_source",
    how="left"
)


# =============================================================================
# BOOKINGS FACT TABLE
# =============================================================================

# One row in bookings_fact represents ONE BOOKING.
#
# The descriptive information stays in the dimension tables.
# The fact table contains:
# - booking identifier
# - dimension IDs
# - dates
# - numerical measures
# - booking-level attributes

bookings_fact = df[
    [
        "booking_id",

        # Dates
        "travel_date",
        "booking_date",

        # Dimension IDs
        "id_ship",
        "id_country",
        "id_suite",
        "id_package",
        "id_booking_source",

        # Booking information
        "lead_time_days",
        "nights_of_stay",
        "booked_cabins",
        "passengers_on_booking",

        # Occupancy
        "cycle_occupancy_percentage",

        # Revenue
        "total_reservation_income_usd",

        # Guest spending
        "average_daily_guest_spending_usd",

        # Customer satisfaction
        "satisfaction_score"
    ]
].copy()


# =============================================================================
# DISPLAY RESULTS
# =============================================================================

sub("bookings_fact")
print(bookings_fact.head(10).to_string(index=False))


# =============================================================================
# FINAL TABLE INFORMATION
# =============================================================================

print("\nStar schema tables created:")
print(f"  ships_dim:             {len(ships_dim)} rows")
print(f"  countries_dim:         {len(countries_dim)} rows")
print(f"  suites_dim:            {len(suites_dim)} rows")
print(f"  packages_dim:          {len(packages_dim)} rows")
print(f"  booking_sources_dim:   {len(booking_sources_dim)} rows")
print(f"  bookings_fact:         {len(bookings_fact)} rows")

# Al final de tu script principal, ejecutas la carga:
cargar_esquema_estrella(
    ships=ships_dim,
     countries=countries_dim,
     suites=suites_dim,
     packages=packages_dim,
     booking_sources=booking_sources_dim,
    bookings_fact=bookings_fact
)

# =============================================================================
# OPTIONAL: EXPORT NORMALIZED TABLES TO CSV
# =============================================================================

# Uncomment these lines if you want to save the normalized tables
# before uploading them to PostgreSQL.

# ships_dim.to_csv("ships_dim.csv", index=False)
# countries_dim.to_csv("countries_dim.csv", index=False)
# suites_dim.to_csv("suites_dim.csv", index=False)
# packages_dim.to_csv("packages_dim.csv", index=False)
# booking_sources_dim.to_csv("booking_sources_dim.csv", index=False)
# bookings_fact.to_csv("bookings_fact.csv", index=False)