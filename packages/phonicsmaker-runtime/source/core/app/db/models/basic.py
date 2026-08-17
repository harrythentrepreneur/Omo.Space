import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from sqlalchemy.dialects.postgresql import JSON


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String, nullable=False)
    email = Column(String, nullable=False)
    full_name = Column(String)
    avatar_url = Column(String)
    billing_address = Column(String)
    payment_method = Column(String)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    customer = relationship("Customer", back_populates="user", uselist=False)
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    user_pref = relationship("UserPreference", back_populates="user", uselist=False)
    user_generation = relationship(
        "UserGeneration", back_populates="user", uselist=False
    )


class Customer(Base):
    __tablename__ = "customers"
    email = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    stripe_customer_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="customer")


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    email = Column(String)
    status = Column(String)
    price_id = Column(String)
    quantity = Column(Integer)
    cancel_at_period_end = Column(Boolean)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    ended_at = Column(DateTime)
    cancel_at = Column(DateTime)
    canceled_at = Column(DateTime)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    subscription_created_at = Column(DateTime)
    subscription_ended_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="subscription")


class UserPreference(Base):
    __tablename__ = "user_prefs"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    email = Column(String, nullable=False)
    description = Column(String)
    timezone = Column(String, default="UTC")
    phone = Column(String)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="user_pref")


class UserGeneration(Base):
    __tablename__ = "user_generations"

    task_id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email = Column(String)
    result_url = Column(String)
    thumbnail_url = Column(String)
    status = Column(String, nullable=False)  # queued, processing, completed, failed
    task_metadata = Column(JSON)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="user_generation")
