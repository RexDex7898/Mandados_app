import os
import json
import uuid
import hashlib
from typing import List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import firebase_admin
from firebase_admin import credentials, messaging

import models
import schemas
from database import engine, get_db

# 1. Crear tablas si no existen
models.Base.metadata.create_all(bind=engine)

# 2. Inicializar Firebase Admin mediante la variable de entorno de Render
firebase_creds_raw = os.getenv("FIREBASE_CREDENTIALS_JSON")
if firebase_creds_raw and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_creds_raw)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK inicializado correctamente.")
    except Exception as e:
        print(f"Error al inicializar Firebase Admin: {e}")

def enviar_push_individual(token_fcm: str, titulo: str, cuerpo: str):
    """Envía notificación directa al dispositivo de un usuario específico (ej. Cliente)."""
    if not token_fcm or not firebase_admin._apps:
        return
    try:
        mensaje = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo
            ),
            token=token_fcm
        )
        messaging.send(mensaje)
    except Exception as err:
        print(f"Error al enviar push a token {token_fcm[:10]}...: {err}")

def notificar_tema_repartidores(titulo: str, cuerpo: str):
    """Emite una alerta a todos los repartidores suscritos al topic 'repartidores'."""
    if not firebase_admin._apps:
        return
    try:
        mensaje = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo
            ),
            topic="repartidores"
        )
        messaging.send(mensaje)
    except Exception as err:
        print(f"Error al notificar topic repartidores: {err}")

# 3. Inicializar FastAPI
app = FastAPI(
    title="API de Mandados y Envíos - Villa de Tezontepec",
    description="Backend en la nube con soporte Push Notification",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hashear_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

class PedidoUpdateGeneral(BaseModel):
    estado: Optional[str] = None
    repartidor_id: Optional[str] = None
    repartidor_nombre: Optional[str] = None
    repartidor_telefono: Optional[str] = None

# ==========================================
# RUTAS BÁSICAS Y AUTENTICACIÓN
# ==========================================

@app.get("/")
def estado_servidor():
    return {"estado": "online", "servicio": "Mandados Express API", "fcm_activo": bool(firebase_admin._apps)}

@app.post("/auth/registro", response_model=schemas.UsuarioResponse)
def registrar_usuario(datos: schemas.UsuarioRegistro, db: Session = Depends(get_db)):
    telefono_limpio = datos.telefono.strip()
    existe = db.query(models.Usuario).filter(models.Usuario.telefono == telefono_limpio).first()
    if existe:
        raise HTTPException(status_code=400, detail="Este número de teléfono ya está registrado")

    nuevo_usuario = models.Usuario(
        id=str(uuid.uuid4()),
        nombre=datos.nombre.strip(),
        telefono=telefono_limpio,
        password_hash=hashear_password(datos.password),
        rol=datos.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.post("/auth/login", response_model=schemas.UsuarioResponse)
def iniciar_sesion(datos: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    pwd_hash = hashear_password(datos.password)
    usuario = db.query(models.Usuario).filter(
        models.Usuario.telefono == datos.telefono.strip(),
        models.Usuario.password_hash == pwd_hash
    ).first()

    if not usuario:
        raise HTTPException(status_code=401, detail="Número de teléfono o contraseña incorrectos")
    return usuario

# ==========================================
# RUTAS DE PEDIDOS Y NOTIFICACIONES
# ==========================================

@app.post("/pedidos/", response_model=schemas.PedidoResponse)
def crear_pedido(pedido_in: schemas.PedidoCreate, db: Session = Depends(get_db)):
    nuevo_id = str(uuid.uuid4())
    costo_envio = 35.00
    pedido_db = models.Pedido(
        id=nuevo_id,
        cliente_id=pedido_in.cliente_id,
        cliente_nombre=pedido_in.cliente_nombre,
        cliente_telefono=pedido_in.cliente_telefono,
        cliente_fcm_token=pedido_in.cliente_fcm_token,
        descripcion=pedido_in.descripcion,
        origen_direccion=pedido_in.origen_direccion,
        origen_lat=pedido_in.origen_lat,
        origen_lng=pedido_in.origen_lng,
        destino_direccion=pedido_in.destino_direccion,
        destino_lat=pedido_in.destino_lat,
        destino_lng=pedido_in.destino_lng,
        costo_productos=pedido_in.costo_productos,
        metodo_pago=pedido_in.metodo_pago,
        tipo=pedido_in.tipo,
        estado="buscando_repartidor",
        costo_envio=costo_envio
    )
    db.add(pedido_db)
    db.commit()
    db.refresh(pedido_db)

    # 🔔 Alerta general a los repartidores
    total = pedido_db.costo_productos + costo_envio
    notificar_tema_repartidores(
        titulo="¡Nuevo Mandado Disponible! 🛵💨",
        cuerpo=f"{pedido_db.cliente_nombre} solicita: {pedido_db.descripcion} (Total: ${total:.2f})"
    )

    return pedido_db

@app.get("/pedidos/", response_model=List[schemas.PedidoResponse])
def listar_pedidos(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.Pedido).offset(skip).limit(limit).all()

@app.get("/pedidos/{pedido_id}", response_model=schemas.PedidoResponse)
def obtener_pedido(pedido_id: str, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido

@app.patch("/pedidos/{pedido_id}/tomar", response_model=schemas.PedidoResponse)
def tomar_pedido(pedido_id: str, datos: schemas.PedidoTomar, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    pedido.repartidor_id = datos.repartidor_id
    pedido.repartidor_nombre = datos.repartidor_nombre
    pedido.repartidor_telefono = datos.repartidor_telefono
    pedido.estado = "asignado"
    
    db.commit()
    db.refresh(pedido)

    # 🔔 Notificación al Cliente: Repartidor Asignado
    if pedido.cliente_fcm_token:
        enviar_push_individual(
            token_fcm=pedido.cliente_fcm_token,
            titulo="¡Repartidor Encontrado! 🛵",
            cuerpo=f"{datos.repartidor_nombre} aceptó tu mandado y va a prepararlo."
        )

    return pedido

@app.patch("/pedidos/{pedido_id}/estado", response_model=schemas.PedidoResponse)
def cambiar_estado_pedido(pedido_id: str, datos: schemas.PedidoUpdateEstado, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    estados_validos = ["buscando_repartidor", "asignado", "en_camino", "en_domicilio", "entregado", "cancelado"]
    if datos.estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado no válido")

    pedido.estado = datos.estado
    db.commit()
    db.refresh(pedido)

    # 🔔 Matriz de Notificaciones automáticas al Cliente según el estado
    mensajes_estado = {
        "en_camino": (
            "¡Tu mandado va en camino! 🛒➡️🏠",
            f"{pedido.repartidor_nombre} ya tiene tus productos y se dirige a tu domicilio."
        ),
        "en_domicilio": (
            "¡Tu repartidor está afuera! 🚪🔔",
            f"{pedido.repartidor_nombre} ha llegado con tu pedido. Por favor sal a recibirlo."
        ),
        "entregado": (
            "Mandado Entregado Con Éxito ✅",
            "¡Muchas gracias por usar Mandados Express Villa de Tezontepec!"
        ),
        "cancelado": (
            "Mandado Cancelado ⚠️",
            "Tu pedido ha sido cancelado. Contáctanos si requieres asistencia."
        )
    }

    if datos.estado in mensajes_estado and pedido.cliente_fcm_token:
        titulo, cuerpo = mensajes_estado[datos.estado]
        enviar_push_individual(pedido.cliente_fcm_token, titulo, cuerpo)

    return pedido

@app.put("/pedidos/{pedido_id}", response_model=schemas.PedidoResponse)
def actualizar_pedido_general(pedido_id: str, datos: PedidoUpdateGeneral, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if datos.estado:
        pedido.estado = datos.estado
    if datos.repartidor_id:
        pedido.repartidor_id = datos.repartidor_id
    if datos.repartidor_nombre:
        pedido.repartidor_nombre = datos.repartidor_nombre
    if datos.repartidor_telefono:
        pedido.repartidor_telefono = datos.repartidor_telefono

    db.commit()
    db.refresh(pedido)
    return pedido

if __name__ == "__main__":
    import uvicorn
    puerto = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=puerto, reload=False)

    # Esquema para recibir el token
class RepartidorToken(BaseModel):
    token: str

@app.post("/notificaciones/suscribir-repartidor")
def suscribir_repartidor_topic(datos: RepartidorToken):
    if not firebase_admin._apps:
        raise HTTPException(status_code=500, detail="Firebase no configurado")
    try:
        # Suscribe el celular al canal general "repartidores"
        res = messaging.subscribe_to_topic([datos.token], "repartidores")
        return {"ok": True, "suscrito": res.success_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))