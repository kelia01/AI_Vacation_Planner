from sqlalchemy import Column, Integer, Float, String,ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trips = relationship("Trip", back_populates="owner", cascade="all , delete-orphan")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    destination = Column(String(100), nullable=False)
    days = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)
    trip_style = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="trips")
    itinerary = relationship("Itinerary", back_populates="trip", uselist=False,
    cascade="all delete-orphan")

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trip = relationship("Trip", back_populates="itinerary")
    days = relationship("ItineraryDay", back_populates="itinerary", cascade="all delete-orphan")

class ItineraryDay(Base):
    __tablename__ = "itinerary_days"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"), nullable=False)

    day_number = Column(Integer, nullable=False)
    activities = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    itinerary = relationship("Itinerary", back_populates="days")



