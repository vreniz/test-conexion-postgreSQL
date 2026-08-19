# PIPELINE DEL PROCESO DE ANALITICA DE DATOS

1. Crear el .env *esto para empaquetar en la versión correspondiente de mis librerias*
```bash
python -m venv env
```
Antes verificar que pyhton este instalado en PC `python --version` para windows python3 para mac

2. Activar el entorno virtual de python `env\Scripts\activate`
Sí ocurre algún problema utilizar este script `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
Luego volver intentar la activación.
En caso que requieras salir del entorno virtual usa `deactivate`
3. Se puede tener un archivo `requirements.txt` con todas las librerias que se necesiten.
Para instalarlas se hace con el entorno virtual activo de la siguiente manera `pip install -r requirements.txt`
4. 