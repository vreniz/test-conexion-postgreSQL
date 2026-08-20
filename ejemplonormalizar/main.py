import pandas as pd

name_file = 'ventas_desnormalizado.csv'

# Leer el CSV
df = pd.read_csv(name_file)

# Eliminar duplicados generales
df = df.drop_duplicates(ignore_index=True)
# Normalizar los datos de la tabla
df["sucursal"] = df["sucursal"].str.strip().str.title() 
df["metodo_pago"] = df["metodo_pago"].str.capitalize()
df["total_venta"] = (df["cantidad"] * df["precio_unitario"] *(1 - df["descuento_pct"]))
df["fecha_venta"] = pd.to_datetime(df["fecha_venta"], format="mixed") 

# Crear tablas dimensionales eliminando duplicados
clientes_dim = df[["cliente_nombre", "cliente_email", "cliente_tipo"]].drop_duplicates(ignore_index=True)
sucursal_dim = df[["sucursal", "ciudad_sucursal"]].drop_duplicates(ignore_index=True)
producto_dim = df[["producto", "categoria_producto"]].drop_duplicates(ignore_index=True)



# Añadir columnas de indices
clientes_dim.insert(0, "id_cliente", range(1, len(clientes_dim) + 1))
producto_dim.insert(0, "id_producto", range(1, len(producto_dim) + 1))
sucursal_dim.insert(0, "id_sucursal", range(1, len(sucursal_dim) + 1))

# Creación y unificación de información en tabla ventas_FT

# Unificar los datos para las FK
df = df.merge(clientes_dim, on=["cliente_nombre", "cliente_email", "cliente_tipo"], how="left")
df = df.merge(producto_dim, on=["producto", "categoria_producto"], how="left")
df = df.merge(sucursal_dim, on=["sucursal", "ciudad_sucursal"], how="left")

# Crear la fact table de ventas
ventas_FT = df[["id_venta",
                "fecha_venta",
                "id_cliente", "id_sucursal",
                "vendedor",
                "id_producto",
                "precio_unitario",
                "cantidad",
                "descuento_pct",
                "metodo_pago",
                "total_venta"]]


# # Creación de CSV
# clientes_dim.to_csv("clientes.csv", index=False)
# producto_dim.to_csv("productos.csv", index=False)
# sucursal_dim.to_csv("sucursales.csv", index=False)
# ventas_FT.to_csv("ventas.csv", index=False)


print(f"""========= INFORMACION ===============0
    {clientes_dim}
    
    {sucursal_dim}
    
    {producto_dim}
    
    {ventas_FT}
    
    {df}
    """)

#PREGUNTAS
#1. ¿Cuáles son las 3 sucursales con mayor ingreso total después de aplicar los descuentos? 
