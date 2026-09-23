import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:@localhost:3306/mandados_db"
)

# Adaptar el protocolo si viene como mysql://
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# Argumentos de conexión
connect_args = {}

# Si nos conectamos a TiDB Cloud en producción, activamos SSL con los certificados del sistema
if "tidbcloud.com" in DATABASE_URL:
    ca_path = "/etc/ssl/certs/ca-certificates.crt"
    if os.path.exists(ca_path):
        connect_args["ssl"] = {"ca": ca_path}
    else:
        connect_args["ssl"] = {"ssl_mode": "VERIFY_IDENTITY"}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()