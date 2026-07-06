from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database import Base

class User(Base):
    # Namespaced to avoid colliding with other apps' "users" table in the
    # shared Postgres database.
    __tablename__ = "datagen_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # format: "salt$hash"
    datetime_created = Column(DateTime, default=datetime.utcnow)

class Generator(Base):
    __tablename__ = "generators"
    id = Column(Integer, primary_key=True, index=True)
    # Owner; nullable so pre-auth rows don't break, but queries scope by owner.
    user_id = Column(Integer, ForeignKey("datagen_users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String)
    description = Column(String)
    interval_ms = Column(Integer, default=1000)
    is_api_enabled = Column(Boolean, default=False)
    is_message_broker_enabled = Column(Boolean, default=False)
    is_database_enabled = Column(Boolean, default=False)
    # Persisted destination selections so they survive page reloads / restarts
    selected_api_id = Column(Integer, nullable=True)
    selected_mqtt_id = Column(Integer, nullable=True)
    selected_db_id = Column(Integer, nullable=True)
    datetime_created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships to Children
    nodes = relationship("Node", back_populates="generator", cascade="all, delete-orphan")
    # A generator can have multiple API/MQTT configs assigned to it
    apis = relationship("API", back_populates="generator", cascade="all, delete-orphan")
    mqtts = relationship("MQTT", back_populates="generator", cascade="all, delete-orphan")

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    generator_id = Column(Integer, ForeignKey("generators.id", ondelete="CASCADE"))
    node_name = Column(String)
    data_type_enum = Column(String)
    generation_mode = Column(String)
    fixed_value = Column(String, nullable=True)
    value_list = Column(String, nullable=True)
    min_range = Column(Float, nullable=True)
    max_range = Column(Float, nullable=True)
    faker_type = Column(String, nullable=True)  # provider name for the "Faker" mode
    
    generator = relationship("Generator", back_populates="nodes")

class API(Base):
    __tablename__ = "apis"
    APIid = Column(Integer, primary_key=True, index=True)
    # Optional link to a Parent Generator (destinations are shared/global by default)
    generator_id = Column(Integer, ForeignKey("generators.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("datagen_users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    APIName = Column(String, nullable=False)
    TargetUrl = Column(String, nullable=False)
    Method = Column(String, default="POST")
    HeaderName = Column(String, nullable=True)
    HeaderValue = Column(String, nullable=True)
    DatetimeCreated = Column(DateTime, default=datetime.utcnow)
    DatetimeUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    generator = relationship("Generator", back_populates="apis")

class MQTT(Base):
    __tablename__ = "mqtt_configs"
    MQTTid = Column(Integer, primary_key=True, index=True)
    # Optional link to a Parent Generator (destinations are shared/global by default)
    generator_id = Column(Integer, ForeignKey("generators.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("datagen_users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    MQTTName = Column(String, nullable=False)
    Host = Column(String, nullable=False, default="localhost")
    Port = Column(Integer, nullable=False, default=1883)
    Topic = Column(String, nullable=False)
    DatetimeCreated = Column(DateTime, default=datetime.utcnow)
    DatetimeUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    generator = relationship("Generator", back_populates="mqtts")

class Database(Base):
    __tablename__ = "datagen_databases"
    DBid = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("datagen_users.id", ondelete="CASCADE"), nullable=True, index=True)

    DBName = Column(String, nullable=False)
    DBType = Column(String, nullable=False, default="PostgreSQL")  # PostgreSQL | Oracle | MongoDB (future)
    ConnectionString = Column(String, nullable=False)
    TableName = Column(String, nullable=False)
    DatetimeCreated = Column(DateTime, default=datetime.utcnow)
    DatetimeUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)