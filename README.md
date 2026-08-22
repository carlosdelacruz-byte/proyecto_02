# API de Fútbol

API REST para gestionar equipos de fútbol y sus fichajes. Cada equipo tiene un
presupuesto y al fichar un jugador se descuenta del presupuesto (si no alcanza,
no se permite el fichaje).

Los ejemplos usan al **Club Alianza Lima** y su estadio, el Alejandro Villanueva
(Matute).

Hecha con Flask, SQLAlchemy sobre PostgreSQL, autenticación por JWT y validación
de la entrada con Pydantic.

## Requisitos

- Python 3.12
- PostgreSQL instalado y corriendo, con una base de datos llamada `futbol`.

## Cómo correr

1. Crear la base de datos en PostgreSQL (con psql o pgAdmin):

   ```sql
   CREATE DATABASE futbol;
   ```

2. Crear un entorno virtual e instalar las dependencias:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Levantar la API:

   ```bash
   python app.py
   ```

La API queda en `http://localhost:5000`. Las tablas se crean solas al iniciar.

Por defecto se conecta a `postgresql://postgres:postgres@localhost:5432/futbol`.
Si tu PostgreSQL usa otro usuario o clave, configura la variable `DATABASE_URL`
antes de levantar la app.

### Variables de entorno

| Variable | Para qué sirve | Valor por defecto |
| --- | --- | --- |
| `DATABASE_URL` | Conexión a PostgreSQL | `postgresql://postgres:postgres@localhost:5432/futbol` |
| `JWT_SECRET_KEY` | Secreto para firmar los tokens | `dev-secret-change-me` |

## Autenticación

Casi todas las rutas necesitan token. El flujo es: registrarse, iniciar sesión
(el login devuelve un `access_token`) y enviar ese token en la cabecera
`Authorization: Bearer <token>` al llamar a las rutas protegidas.

Tanto el registro como el login reciben este body:

```json
{
  "username": "admin",
  "password": "123456"
}
```

## Endpoints

| Método | Ruta | Protegido | Descripción |
| --- | --- | :---: | --- |
| GET | `/` | no | Comprobar que la API responde |
| POST | `/auth/register` | no | Crear usuario |
| POST | `/auth/login` | no | Iniciar sesión y obtener el token |
| GET | `/equipos` | sí | Listar equipos |
| POST | `/equipos` | sí | Crear equipo |
| GET | `/equipos/<id>` | sí | Ver un equipo |
| PUT | `/equipos/<id>` | sí | Actualizar equipo |
| DELETE | `/equipos/<id>` | sí | Eliminar equipo |
| POST | `/equipos/<id>/imagen` | sí | Subir el escudo/foto del equipo |
| GET | `/equipos/<id>/imagen` | no | Ver la imagen del equipo |
| POST | `/fichajes` | sí | Fichar un jugador para un equipo |
| GET | `/fichajes` | sí | Listar fichajes |

## Datos de ejemplo

Crear un equipo (`POST /equipos`):

```json
{
  "nombre": "Alianza Lima",
  "ciudad": "Lima",
  "estadio": "Alejandro Villanueva",
  "presupuesto": "1000000.00",
  "activo": true
}
```

Fichar un jugador (`POST /fichajes`). Aquí está la lógica de negocio: se valida
que el equipo exista, que esté activo y que le alcance el presupuesto; si el
fichaje entra, se descuenta el costo del presupuesto del equipo.

```json
{
  "equipo_id": 1,
  "jugador": "Paolo Guerrero",
  "posicion": "Delantero",
  "costo": "300000.00"
}
```

Otros jugadores del plantel para probar: Hernán Barcos (Delantero), Carlos
Zambrano (Defensa) o Ángelo Campos (Portero). Si el costo supera el presupuesto
restante del equipo, la API responde con un `400`.

Para subir la imagen de un equipo se usa `POST /equipos/<id>/imagen`, enviando el
archivo como `form-data` en el campo `imagen` (png, jpg, jpeg, gif o webp, hasta
5 MB). Después queda disponible en `GET /equipos/<id>/imagen`.

## Stack

Flask · Flask-SQLAlchemy · PostgreSQL · Flask-JWT-Extended · Pydantic
