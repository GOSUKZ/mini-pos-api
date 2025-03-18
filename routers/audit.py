from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
import logging
from utils.dependencies import get_db_service, has_role
from core.database import DatabaseService
from core.models import User

logger = logging.getLogger("audit_router")

# Создаем роутер
router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    responses={404: {"description": "Not found"}},
)


@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    entity: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(has_role(["admin"])),
):
    """
    Получение записей из лога аудита с фильтрацией.
    Требуются права администратора.
    """
    logger.info(f"Запрос журнала аудита пользователем {current_user.username}")

    try:
        logs = await db_service.get_audit_logs(
            skip=skip,
            limit=limit,
            entity=entity,
            action=action,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
        )

        # Записываем в аудит запрос логов
        await db_service.add_audit_log(
            action="read",
            entity="audit_logs",
            entity_id="list",
            user_id=current_user.username,
            details=f"Retrieved audit logs with filters: entity={entity}, action={action}, user_id={user_id}",
        )

        return logs
    except Exception as e:
        logger.error(f"Ошибка при получении записей аудита: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
