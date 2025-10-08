"""
Notifications API for London Evacuation Planning Tool.
Provides endpoints for sending emergency notifications via SMS and WhatsApp.
"""

import os
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import structlog

from services.notification_service import (
    get_notification_service,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
    NotificationPriority,
    NotificationTemplate,
    send_government_alert,
    notify_simulation_result
)

router = APIRouter()
logger = structlog.get_logger(__name__)


class SendNotificationRequest(BaseModel):
    """Request to send a single notification."""
    recipient: str = Field(..., description="Phone number in E.164 format (e.g., +44XXXXXXXXXX)")
    message_type: NotificationType = NotificationType.WHATSAPP
    priority: NotificationPriority = NotificationPriority.MEDIUM
    template: NotificationTemplate = None
    custom_message: str = None
    template_data: Dict[str, Any] = Field(default_factory=dict)


class BulkNotificationRequest(BaseModel):
    """Request to send multiple notifications."""
    notifications: List[SendNotificationRequest] = Field(..., min_items=1, max_items=100)


class EvacuationAlertRequest(BaseModel):
    """Request to send evacuation alert."""
    recipients: List[str] = Field(..., description="List of phone numbers")
    area: str = Field(..., description="Area being evacuated")
    route_id: str = Field(..., description="Recommended evacuation route")
    exit_points: str = Field(..., description="Exit points to use")
    closed_roads: str = Field(..., description="Roads to avoid")
    info_url: str = Field(default="gov.uk/emergency", description="URL for more information")
    authority: str = Field(default="UK Government Emergency Response", description="Issuing authority")


class SimulationCompleteRequest(BaseModel):
    """Request to notify simulation completion."""
    recipients: List[str] = Field(default_factory=lambda: [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")])
    run_id: str = Field(..., description="Simulation run ID")
    best_scenario: str = Field(..., description="Name of best evacuation scenario")
    clearance_time: float = Field(..., description="Evacuation clearance time in minutes")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    results_url: str = Field(default="", description="URL to view results")


class GovernmentAlertRequest(BaseModel):
    """Request to send alert to government contacts."""
    message: str = Field(..., max_length=1000, description="Alert message")
    priority: NotificationPriority = NotificationPriority.HIGH


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    background_tasks: BackgroundTasks
) -> NotificationResponse:
    """Send a single notification via SMS or WhatsApp."""
    try:
        service = get_notification_service()

        notification_request = NotificationRequest(
            recipient=request.recipient,
            message_type=request.message_type,
            priority=request.priority,
            template=request.template,
            custom_message=request.custom_message,
            template_data=request.template_data
        )

        response = await service.send_notification(notification_request)

        logger.info("Notification sent via API",
                   recipient=request.recipient,
                   type=request.message_type,
                   status=response.status)

        return response

    except Exception as e:
        logger.error("Failed to send notification via API", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk", response_model=List[NotificationResponse])
async def send_bulk_notifications(
    request: BulkNotificationRequest,
    background_tasks: BackgroundTasks
) -> List[NotificationResponse]:
    """Send multiple notifications concurrently."""
    try:
        service = get_notification_service()

        notification_requests = [
            NotificationRequest(
                recipient=req.recipient,
                message_type=req.message_type,
                priority=req.priority,
                template=req.template,
                custom_message=req.custom_message,
                template_data=req.template_data
            )
            for req in request.notifications
        ]

        responses = await service.send_bulk_notifications(notification_requests)

        successful = len([r for r in responses if r.status != "failed"])
        logger.info("Bulk notifications sent via API",
                   total=len(request.notifications),
                   successful=successful)

        return responses

    except Exception as e:
        logger.error("Failed to send bulk notifications via API", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evacuation-alert", response_model=List[NotificationResponse])
async def send_evacuation_alert(
    request: EvacuationAlertRequest,
    background_tasks: BackgroundTasks
) -> List[NotificationResponse]:
    """Send evacuation alert to multiple recipients."""
    try:
        service = get_notification_service()

        responses = await service.send_evacuation_alert(
            recipients=request.recipients,
            area=request.area,
            route_id=request.route_id,
            exit_points=request.exit_points,
            closed_roads=request.closed_roads,
            info_url=request.info_url,
            authority=request.authority
        )

        logger.info("Evacuation alert sent",
                   area=request.area,
                   recipients_count=len(request.recipients))

        return responses

    except Exception as e:
        logger.error("Failed to send evacuation alert", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation-complete", response_model=List[NotificationResponse])
async def notify_simulation_complete(
    request: SimulationCompleteRequest,
    background_tasks: BackgroundTasks
) -> List[NotificationResponse]:
    """Notify stakeholders when simulation is complete."""
    try:
        service = get_notification_service()

        responses = await service.notify_simulation_complete(
            recipients=request.recipients,
            run_id=request.run_id,
            best_scenario=request.best_scenario,
            clearance_time=request.clearance_time,
            confidence=request.confidence,
            results_url=request.results_url
        )

        logger.info("Simulation completion notification sent",
                   run_id=request.run_id,
                   recipients_count=len(request.recipients))

        return responses

    except Exception as e:
        logger.error("Failed to send simulation completion notification", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decision-memo-ready", response_model=List[NotificationResponse])
async def notify_decision_memo_ready(
    run_id: str,
    recommendation: str,
    confidence: float,
    recipients: List[str] = None,
    memo_url: str = "",
    background_tasks: BackgroundTasks = None
) -> List[NotificationResponse]:
    """Notify decision makers when memo is ready."""
    try:
        service = get_notification_service()

        if recipients is None:
            recipients = [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")]

        responses = await service.notify_decision_memo_ready(
            recipients=recipients,
            run_id=run_id,
            recommendation=recommendation,
            confidence=confidence,
            memo_url=memo_url
        )

        logger.info("Decision memo notification sent",
                   run_id=run_id,
                   recipients_count=len(recipients))

        return responses

    except Exception as e:
        logger.error("Failed to send decision memo notification", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/government-alert", response_model=List[NotificationResponse])
async def send_government_alert_endpoint(
    request: GovernmentAlertRequest,
    background_tasks: BackgroundTasks
) -> List[NotificationResponse]:
    """Send immediate alert to government contacts."""
    try:
        responses = await send_government_alert(
            message=request.message,
            priority=request.priority
        )

        logger.info("Government alert sent", message=request.message[:50] + "...")

        return responses

    except Exception as e:
        logger.error("Failed to send government alert", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=Dict[str, Dict[str, str]])
async def get_notification_templates():
    """Get available notification templates."""
    service = get_notification_service()
    return {
        template.value: content
        for template, content in service._templates.items()
    }


@router.post("/test-connection")
async def test_twilio_connection():
    """Test Twilio connection and configuration."""
    try:
        service = get_notification_service()

        if not service.client:
            raise HTTPException(status_code=503, detail="Twilio client not initialized")

        # Test with a simple message to the government number
        test_request = NotificationRequest(
            recipient=os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX"),
            message_type=NotificationType.WHATSAPP,
            priority=NotificationPriority.LOW,
            custom_message="🧪 Test message from London Evacuation Planning Tool. System operational."
        )

        response = await service.send_notification(test_request)

        return {
            "status": "success",
            "message": "Twilio connection verified",
            "test_message_sid": response.message_sid,
            "test_status": response.status
        }

    except Exception as e:
        logger.error("Twilio connection test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.get("/status")
async def get_service_status():
    """Get notification service status."""
    try:
        service = get_notification_service()

        return {
            "service": "London Evacuation Planning Tool - Notifications",
            "twilio_initialized": service.client is not None,
            "available_templates": list(service._templates.keys()),
            "supported_types": [t.value for t in NotificationType],
            "priority_levels": [p.value for p in NotificationPriority],
            "government_contact_configured": bool(os.getenv("GOVERNMENT_CONTACT_NUMBER")),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error("Failed to get service status", error=str(e))
        return {
            "service": "London Evacuation Planning Tool - Notifications",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }