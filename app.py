import os
from decimal import Decimal

from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_sqlalchemy import SQLAlchemy
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import Numeric
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


db = SQLAlchemy()
jwt = JWTManager()


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Equipo(db.Model):
    __tablename__ = "equipos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ciudad = db.Column(db.String(80), nullable=False)
    estadio = db.Column(db.String(100), nullable=False)
    presupuesto = db.Column(Numeric(12, 2), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    imagen = db.Column(db.String(255), nullable=True)  # escudo/foto del equipo

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "ciudad": self.ciudad,
            "estadio": self.estadio,
            "presupuesto": float(self.presupuesto),
            "activo": self.activo,
            "imagen": self.imagen,
        }


class Fichaje(db.Model):
    __tablename__ = "fichajes"

    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipos.id"), nullable=False)
    jugador = db.Column(db.String(100), nullable=False)
    posicion = db.Column(db.String(50), nullable=False)
    costo = db.Column(Numeric(12, 2), nullable=False)
    equipo = db.relationship("Equipo")

    def to_dict(self):
        return {
            "id": self.id,
            "equipo_id": self.equipo_id,
            "equipo": self.equipo.nombre if self.equipo else None,
            "jugador": self.jugador,
            "posicion": self.posicion,
            "costo": float(self.costo),
        }


class AuthSchema(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class EquipoSchema(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    ciudad: str = Field(min_length=2, max_length=80)
    estadio: str = Field(min_length=2, max_length=100)
    presupuesto: Decimal = Field(gt=0, decimal_places=2)
    activo: bool = True


class FichajeSchema(BaseModel):
    equipo_id: int = Field(gt=0)
    jugador: str = Field(min_length=2, max_length=100)
    posicion: str = Field(min_length=2, max_length=50)
    costo: Decimal = Field(gt=0, decimal_places=2)


def validar_json(schema):
    # Devuelve (datos, None) si valida, o (None, respuesta_error) si no
    try:
        return schema.model_validate(request.get_json(silent=True) or {}), None
    except ValidationError as error:
        return None, (jsonify({"errores": error.errors()}), 400)


EXTENSIONES_IMAGEN = {"png", "jpg", "jpeg", "gif", "webp"}


def extension_permitida(nombre):
    return "." in nombre and nombre.rsplit(".", 1)[1].lower() in EXTENSIONES_IMAGEN


def create_app():
    app = Flask(__name__)
    # La conexion y el secreto vienen por variables de entorno.
    # Los valores por defecto son solo para correr en local.
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/futbol",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # limite de 5 MB por imagen
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        db.create_all()

    @app.get("/")
    def home():
        return jsonify({
            "mensaje": "API Futbol",
            "endpoints": ["/auth/register", "/auth/login", "/equipos", "/fichajes"],
        })

    @app.post("/auth/register")
    def register():
        data, error = validar_json(AuthSchema)
        if error:
            return error

        if Usuario.query.filter_by(username=data.username).first():
            return jsonify({"msg": "El usuario ya existe"}), 409

        usuario = Usuario(
            username=data.username,
            password_hash=generate_password_hash(data.password),
        )
        db.session.add(usuario)
        db.session.commit()

        return jsonify({"msg": "Usuario creado"}), 201

    @app.post("/auth/login")
    def login():
        data, error = validar_json(AuthSchema)
        if error:
            return error

        usuario = Usuario.query.filter_by(username=data.username).first()
        if not usuario or not check_password_hash(usuario.password_hash, data.password):
            return jsonify({"msg": "Credenciales invalidas"}), 401

        token = create_access_token(identity=str(usuario.id))
        return jsonify({"access_token": token})

    @app.get("/equipos")
    @jwt_required()
    def listar_equipos():
        equipos = Equipo.query.order_by(Equipo.id).all()
        return jsonify([equipo.to_dict() for equipo in equipos])

    @app.post("/equipos")
    @jwt_required()
    def crear_equipo():
        data, error = validar_json(EquipoSchema)
        if error:
            return error

        equipo = Equipo(**data.model_dump())
        db.session.add(equipo)
        db.session.commit()
        return jsonify(equipo.to_dict()), 201

    @app.get("/equipos/<int:equipo_id>")
    @jwt_required()
    def obtener_equipo(equipo_id):
        equipo = Equipo.query.get_or_404(equipo_id)
        return jsonify(equipo.to_dict())

    @app.put("/equipos/<int:equipo_id>")
    @jwt_required()
    def actualizar_equipo(equipo_id):
        equipo = Equipo.query.get_or_404(equipo_id)
        data, error = validar_json(EquipoSchema)
        if error:
            return error

        equipo.nombre = data.nombre
        equipo.ciudad = data.ciudad
        equipo.estadio = data.estadio
        equipo.presupuesto = data.presupuesto
        equipo.activo = data.activo
        db.session.commit()
        return jsonify(equipo.to_dict())

    @app.delete("/equipos/<int:equipo_id>")
    @jwt_required()
    def eliminar_equipo(equipo_id):
        equipo = Equipo.query.get_or_404(equipo_id)
        db.session.delete(equipo)
        db.session.commit()
        return jsonify({"msg": "Equipo eliminado"})

    @app.post("/equipos/<int:equipo_id>/imagen")
    @jwt_required()
    def subir_imagen_equipo(equipo_id):
        equipo = Equipo.query.get_or_404(equipo_id)

        if "imagen" not in request.files:
            return jsonify({"msg": "Falta el archivo en el campo 'imagen'"}), 400

        archivo = request.files["imagen"]
        if archivo.filename == "":
            return jsonify({"msg": "No se selecciono ningun archivo"}), 400
        if not extension_permitida(archivo.filename):
            return jsonify({"msg": "Formato no permitido (png, jpg, jpeg, gif, webp)"}), 400

        # Guardamos como equipo_<id>.<ext> para evitar colisiones de nombres.
        extension = secure_filename(archivo.filename).rsplit(".", 1)[1].lower()
        nombre = f"equipo_{equipo.id}.{extension}"
        archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre))

        equipo.imagen = nombre
        db.session.commit()
        return jsonify(equipo.to_dict())

    @app.get("/equipos/<int:equipo_id>/imagen")
    def ver_imagen_equipo(equipo_id):
        equipo = Equipo.query.get_or_404(equipo_id)
        if not equipo.imagen:
            return jsonify({"msg": "El equipo no tiene imagen"}), 404
        return send_from_directory(app.config["UPLOAD_FOLDER"], equipo.imagen)

    @app.post("/fichajes")
    @jwt_required()
    def crear_fichaje():
        data, error = validar_json(FichajeSchema)
        if error:
            return error

        # Regla de negocio: el equipo debe existir, estar activo
        # y tener presupuesto suficiente para pagar el fichaje.
        equipo = Equipo.query.get(data.equipo_id)
        if not equipo:
            return jsonify({"msg": "Equipo no encontrado"}), 404
        if not equipo.activo:
            return jsonify({"msg": "El equipo no esta activo"}), 400
        if data.costo > equipo.presupuesto:
            return jsonify({"msg": "El costo supera el presupuesto del equipo"}), 400

        fichaje = Fichaje(
            equipo_id=equipo.id,
            jugador=data.jugador,
            posicion=data.posicion,
            costo=data.costo,
        )
        equipo.presupuesto = equipo.presupuesto - data.costo
        db.session.add(fichaje)
        db.session.commit()

        return jsonify({
            "fichaje": fichaje.to_dict(),
            "presupuesto_restante": float(equipo.presupuesto),
        }), 201

    @app.get("/fichajes")
    @jwt_required()
    def listar_fichajes():
        fichajes = Fichaje.query.order_by(Fichaje.id).all()
        return jsonify([fichaje.to_dict() for fichaje in fichajes])

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
