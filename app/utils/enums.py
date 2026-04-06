import enum

class RecordType(str, enum.Enum):
    INCOME  = "income"
    EXPENSE = "expense"

class RecordStatus(str, enum.Enum):
    ACTIVE      = "active"
    ARCHIVED    = "archived"
    DELETED     = "deleted"

class CategoryType(str, enum.Enum):
    INCOME  = "income"
    EXPENSE = "expense"

class UserRoleEnum(str, enum.Enum):
    VIEWER  = "viewer"   
    ANALYST = "analyst"   
    ADMIN   = "admin"     


class PermissionAction(str, enum.Enum):
    VIEW_RECORDS = "view_records"
    CREATE_RECORDS = "create_records"
    UPDATE_RECORDS = "update_records"
    DELETE_RECORDS = "delete_records"
    VIEW_ANALYTICS = "view_analytics"
    ADVANCED_ANALYSIS = "advanced_analysis"
    MANAGE_USERS = "manage_users"
    ASSIGN_ROLES = "assign_roles"


ROLE_PERMISSIONS: dict[UserRoleEnum, set[PermissionAction]] = {
    UserRoleEnum.VIEWER: {
        PermissionAction.VIEW_RECORDS,
        PermissionAction.VIEW_ANALYTICS,
    },
    UserRoleEnum.ANALYST: {
        PermissionAction.VIEW_RECORDS,
        PermissionAction.VIEW_ANALYTICS,
        PermissionAction.ADVANCED_ANALYSIS,
    },
    UserRoleEnum.ADMIN: {
        PermissionAction.VIEW_RECORDS,
        PermissionAction.CREATE_RECORDS,
        PermissionAction.UPDATE_RECORDS,
        PermissionAction.DELETE_RECORDS,
        PermissionAction.VIEW_ANALYTICS,
        PermissionAction.ADVANCED_ANALYSIS,
        PermissionAction.MANAGE_USERS,
        PermissionAction.ASSIGN_ROLES,
    },
}

class UserStatus(str, enum.Enum):
    ACTIVE      = "active"
    INACTIVE    = "inactive"
    SUSPENDED   = "suspended"

class TimeRange(str, enum.Enum):
    DAILY   = "daily"
    WEEKLY  = "weekly"
    MONTHLY = "monthly"
    YEARLY  = "yearly"
