import os
import uuid
import hashlib
from typing import List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db

# 1. Crear las tablas automáticamente en la base de datos de Railway
models.Base.metadata.create_all(bind=engine)

# 2. Inicializar FastAPI
app = FastAPI(
    title="API de Mandados y Envíos - Villa de Tezontepec",
    description="Backend en la nube para pedidos en tiempo real",
    version="1.0.0"
)

# 3. Configurar CORS (Permite llamadas desde Android y navegadores)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hashear_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

# Esquema auxiliar para actualizar pedidos vía PUT
class PedidoUpdateGeneral(BaseModel):
    estado: Optional[str] = None
    repartidor_id: Optional[str] = None
    repartidor_nombre: Optional[str] = None
    repartidor_telefono: Optional[str] = None

# ==========================================
# RUTA DE HEALTHCHECK
# ==========================================
@app.get("/")
def estado_servidor():
    return {
        "estado": "online",
        "servicio": "Mandados Express API",
        "municipio": "Villa de Tezontepec"
    }

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================

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
# RUTAS DE PEDIDOS
# ==========================================

@app.post("/pedidos/", response_model=schemas.PedidoResponse)
def crear_pedido(pedido_in: schemas.PedidoCreate, db: Session = Depends(get_db)):
    nuevo_id = str(uuid.uuid4())
    pedido_db = models.Pedido(
        id=nuevo_id,
        cliente_id=pedido_in.cliente_id,
        cliente_nombre=pedido_in.cliente_nombre,
        cliente_telefono=pedido_in.cliente_telefono,
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
        costo_envio=35.00
    )
    db.add(pedido_db)
    db.commit()
    db.refresh(pedido_db)
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

# Endpoint unificado PUT para compatibilidad total con la app móvil
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
    return pedido

@app.patch("/pedidos/{pedido_id}/estado", response_model=schemas.PedidoResponse)
def cambiar_estado_pedido(
    pedido_id: str, 
    datos: schemas.PedidoUpdateEstado, 
    db: Session = Depends(get_db)
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    estados_validos = ["buscando_repartidor", "asignado", "en_camino", "entregado", "cancelado"]
    if datos.estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado no válido")

    pedido.estado = datos.estado
    db.commit()
    db.refresh(pedido)
    return pedido

if __name__ == "__main__":
    import uvicorn
    puerto = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=puerto, reload=False)