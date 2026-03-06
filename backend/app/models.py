import enum
import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Column, Enum, Field, Relationship, SQLModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AdjustmentType(str, enum.Enum):
    DEDUCTION = "DEDUCTION"
    BONUS = "BONUS"


class RemittanceStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ===========================  USER  =========================================


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    hourly_rate: float = Field(default=25.0)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    worklogs: list["WorkLog"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    remittances: list["Remittance"] = Relationship(
        back_populates="user", cascade_delete=True
    )


class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ===========================  ITEM  =========================================


class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ===========================  WORKLOG  ======================================


class WorkLog(SQLModel, table=True):
    __tablename__ = "worklog"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User | None = Relationship(back_populates="worklogs")
    time_segments: list["TimeSegment"] = Relationship(
        back_populates="worklog", cascade_delete=True
    )
    adjustments: list["Adjustment"] = Relationship(
        back_populates="worklog", cascade_delete=True
    )
    line_items: list["RemittanceLineItem"] = Relationship(
        back_populates="worklog", cascade_delete=True
    )


# ===========================  TIME SEGMENT  =================================


class TimeSegment(SQLModel, table=True):
    __tablename__ = "time_segment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    worklog_id: uuid.UUID = Field(
        foreign_key="worklog.id", nullable=False, ondelete="CASCADE", index=True
    )
    start_time: datetime
    end_time: datetime
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    worklog: WorkLog | None = Relationship(back_populates="time_segments")


# ===========================  ADJUSTMENT  ===================================


class Adjustment(SQLModel, table=True):
    __tablename__ = "adjustment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    worklog_id: uuid.UUID = Field(
        foreign_key="worklog.id", nullable=False, ondelete="CASCADE", index=True
    )
    amount: float = Field(default=0.0)
    reason: str | None = Field(default=None, max_length=1024)
    adjustment_type: AdjustmentType = Field(
        sa_column=Column(Enum(AdjustmentType), nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    worklog: WorkLog | None = Relationship(back_populates="adjustments")


# ===========================  REMITTANCE  ===================================


class Remittance(SQLModel, table=True):
    __tablename__ = "remittance"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    total_amount: float = Field(default=0.0)
    status: RemittanceStatus = Field(
        sa_column=Column(
            Enum(RemittanceStatus),
            nullable=False,
            default=RemittanceStatus.PENDING,
        )
    )
    period_label: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User | None = Relationship(back_populates="remittances")
    line_items: list["RemittanceLineItem"] = Relationship(
        back_populates="remittance", cascade_delete=True
    )


# ===========================  REMITTANCE LINE ITEM  =========================


class RemittanceLineItem(SQLModel, table=True):
    __tablename__ = "remittance_line_item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    remittance_id: uuid.UUID = Field(
        foreign_key="remittance.id", nullable=False, ondelete="CASCADE", index=True
    )
    worklog_id: uuid.UUID = Field(
        foreign_key="worklog.id", nullable=False, ondelete="CASCADE", index=True
    )
    amount_settled: float = Field(default=0.0)

    # Relationships
    remittance: Remittance | None = Relationship(back_populates="line_items")
    worklog: WorkLog | None = Relationship(back_populates="line_items")


# ===========================  GENERIC / AUTH  ===============================


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ===========================  API RESPONSE SCHEMAS  =========================


class TimeSegmentPublic(SQLModel):
    id: uuid.UUID
    start_time: datetime
    end_time: datetime
    is_active: bool
    created_at: datetime


class AdjustmentPublic(SQLModel):
    id: uuid.UUID
    amount: float
    reason: str | None
    adjustment_type: AdjustmentType
    created_at: datetime


class WorkLogPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    created_at: datetime
    amount: float
    remittance_status: str
    time_segments: list[TimeSegmentPublic]
    adjustments: list[AdjustmentPublic]


class WorkLogListResponse(SQLModel):
    data: list[WorkLogPublic]
    count: int


class RemittanceLineItemPublic(SQLModel):
    id: uuid.UUID
    worklog_id: uuid.UUID
    amount_settled: float


class RemittancePublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    total_amount: float
    status: RemittanceStatus
    period_label: str
    created_at: datetime
    line_items: list[RemittanceLineItemPublic]


class RemittanceGenerateResponse(SQLModel):
    message: str
    remittances: list[RemittancePublic]
    total_users_processed: int
