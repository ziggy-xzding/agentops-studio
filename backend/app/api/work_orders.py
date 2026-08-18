from fastapi import APIRouter

from app.api.runs import ServiceDependency
from app.schemas import WorkOrderRead

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


@router.get("", response_model=list[WorkOrderRead])
def list_work_orders(service: ServiceDependency):
    return service.list_work_orders()


@router.get("/{work_order_id}", response_model=WorkOrderRead)
def get_work_order(work_order_id: str, service: ServiceDependency):
    return service.get_work_order(work_order_id)
