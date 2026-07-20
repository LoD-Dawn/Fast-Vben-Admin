import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class DataScope(StrEnum):
    ALL = "all"
    DEPARTMENT = "department"
    DEPARTMENT_AND_CHILDREN = "department_and_children"
    SELF = "self"
    CUSTOM = "custom"


class DepartmentBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    parent_id: uuid.UUID | None = None
    leader_user_id: uuid.UUID | None = None
    sort: int = 0
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    leader_user_id: uuid.UUID | None = None
    sort: int | None = None
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class Department(DepartmentBase, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_id", "tenant_id"],
            ["department.id", "department.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["leader_user_id", "tenant_id"],
            ["tenantmembership.user_id", "tenantmembership.tenant_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "code", name="uq_department_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_department_id_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    archived_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), index=True  # type: ignore
    )


class DepartmentPublic(DepartmentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DepartmentsPublic(SQLModel):
    items: list[DepartmentPublic]
    total: int
    page: int
    page_size: int


class PostBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    sort: int = 0
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class PostCreate(PostBase):
    pass


class PostUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    sort: int | None = None
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class Post(PostBase, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_post_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_post_id_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    archived_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), index=True  # type: ignore
    )


class PostPublic(PostBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PostsPublic(SQLModel):
    items: list[PostPublic]
    total: int
    page: int
    page_size: int


class UserPost(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["tenantmembership.user_id", "tenantmembership.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["post_id", "tenant_id"],
            ["post.id", "post.tenant_id"],
            ondelete="CASCADE",
        ),
    )

    user_id: uuid.UUID = Field(primary_key=True)
    post_id: uuid.UUID = Field(primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID, primary_key=True, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserRole(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["tenantmembership.user_id", "tenantmembership.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["role_id", "tenant_id"],
            ["role.id", "role.tenant_id"],
            ondelete="CASCADE",
        ),
    )

    user_id: uuid.UUID = Field(primary_key=True)
    role_id: uuid.UUID = Field(primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID, primary_key=True, index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class RoleMenu(SQLModel, table=True):
    role_id: uuid.UUID = Field(
        foreign_key="role.id", primary_key=True, ondelete="CASCADE"
    )
    menu_id: uuid.UUID = Field(
        foreign_key="menu.id", primary_key=True, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class RoleBase(SQLModel):
    code: str = Field(min_length=1, max_length=100, index=True)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    sort: int = 0
    is_active: bool = True
    is_system: bool = False
    data_scope: DataScope = Field(default=DataScope.SELF, sa_type=String(32))


class RoleCreate(RoleBase):
    custom_department_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(SQLModel):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    sort: int | None = None
    is_active: bool | None = None
    is_system: bool | None = None
    data_scope: DataScope | None = None
    custom_department_ids: list[uuid.UUID] | None = None


class Role(RoleBase, table=True):
    __table_args__ = (
        CheckConstraint(
            "data_scope IN ('all', 'department', 'department_and_children', 'self', 'custom')",
            name="ck_role_data_scope",
        ),
        UniqueConstraint("tenant_id", "code", name="uq_role_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_role_id_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        nullable=False,
        ondelete="CASCADE",
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class RolePublic(RoleBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    custom_department_ids: list[uuid.UUID] = Field(default_factory=list)


class RolesPublic(SQLModel):
    items: list[RolePublic]
    total: int
    page: int
    page_size: int


class RoleMenuUpdate(SQLModel):
    menu_ids: list[uuid.UUID]


class RoleDataScopeDepartment(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["role_id", "tenant_id"],
            ["role.id", "role.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["department_id", "tenant_id"],
            ["department.id", "department.tenant_id"],
            ondelete="CASCADE",
        ),
    )

    role_id: uuid.UUID = Field(primary_key=True)
    department_id: uuid.UUID = Field(primary_key=True)
    tenant_id: uuid.UUID = Field(primary_key=True, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserRoleUpdate(SQLModel):
    role_ids: list[uuid.UUID]


class UserPostUpdate(SQLModel):
    post_ids: list[uuid.UUID]


class MenuBase(SQLModel):
    title: str = Field(min_length=1, max_length=100)
    type: str = Field(default="menu", max_length=20)
    parent_id: uuid.UUID | None = Field(default=None, foreign_key="menu.id")
    route_path: str | None = Field(default=None, max_length=255)
    route_name: str | None = Field(default=None, max_length=100)
    component: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    permission_code: str | None = Field(default=None, max_length=100, index=True)
    sort: int = 0
    is_visible: bool = True
    is_keep_alive: bool = False
    is_active: bool = True


class MenuCreate(MenuBase):
    pass


class MenuUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, max_length=20)
    parent_id: uuid.UUID | None = None
    route_path: str | None = Field(default=None, max_length=255)
    route_name: str | None = Field(default=None, max_length=100)
    component: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    permission_code: str | None = Field(default=None, max_length=100)
    sort: int | None = None
    is_visible: bool | None = None
    is_keep_alive: bool | None = None
    is_active: bool | None = None


class Menu(MenuBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class MenuPublic(MenuBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MenusPublic(SQLModel):
    items: list[MenuPublic]
    total: int
    page: int
    page_size: int
