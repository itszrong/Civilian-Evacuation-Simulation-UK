"""
Notification service for London Evacuation Planning Tool.

This module handles emergency notifications via SMS and WhatsApp using Twilio,
specifically designed for UK government emergency communications.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import structlog
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from pydantic import BaseModel, Field

from core.config import get_settings

logger = structlog.get_logger(__name__)


class NotificationType(str, Enum):
    """Types of notifications that can be sent."""
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationTemplate(str, Enum):
    """Pre-defined notification templates for emergency scenarios."""
    EVACUATION_ALERT = "evacuation_alert"
    EVACUATION_UPDATE = "evacuation_update"
    EVACUATION_COMPLETE = "evacuation_complete"
    AREA_CLOSURE = "area_closure"
    TRANSPORT_UPDATE = "transport_update"
    SIMULATION_COMPLETE = "simulation_complete"
    DECISION_MEMO_READY = "decision_memo_ready"


class NotificationRequest(BaseModel):
    """Request for sending a notification."""
    recipient: str = Field(..., description="Phone number in E.164 format")
    message_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    template: Optional[NotificationTemplate] = None
    custom_message: Optional[str] = None
    template_data: Dict[str, Any] = Field(default_factory=dict)
    send_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class NotificationResponse(BaseModel):
    """Response from notification service."""
    message_sid: str
    recipient: str
    message_type: NotificationType
    status: str
    sent_at: datetime
    error_message: Optional[str] = None


class TwilioNotificationService:
    """Service for sending emergency notifications via Twilio."""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[Client] = None
        self._templates = self._load_message_templates()
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Twilio client."""
        try:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")

            if not account_sid or not auth_token:
                logger.warning("Twilio credentials not found in environment variables")
                return

            self.client = Client(account_sid, auth_token)
            logger.info("Twilio client initialized successfully")

            # Verify connection
            try:
                account = self.client.api.accounts(account_sid).fetch()
                logger.info("Twilio account verified", account_name=account.friendly_name)
            except Exception as e:
                logger.error("Failed to verify Twilio account", error=str(e))

        except Exception as e:
            logger.error("Failed to initialize Twilio client", error=str(e))
            self.client = None

    def _load_message_templates(self) -> Dict[NotificationTemplate, Dict[str, str]]:
        """Load message templates for different notification types."""
        return {
            NotificationTemplate.EVACUATION_ALERT: {
                "subject": "🚨 EMERGENCY EVACUATION ALERT",
                "sms": "EMERGENCY: Evacuation ordered for {area}. Follow Route {route_id}. Exit via {exit_points}. Do NOT use {closed_roads}. More info: {info_url}",
                "whatsapp": """🚨 *EMERGENCY EVACUATION ALERT*

📍 **Area**: {area}
🗺️ **Route**: Follow Route {route_id}
🚪 **Exits**: {exit_points}
⛔ **AVOID**: {closed_roads}

This is an official message from {authority}.
For updates: {info_url}"""
            },
            NotificationTemplate.EVACUATION_UPDATE: {
                "subject": "📋 Evacuation Update",
                "sms": "EVACUATION UPDATE: {status}. Current wait time: {wait_time}min. {additional_info}",
                "whatsapp": """📋 *EVACUATION UPDATE*

🚦 **Status**: {status}
⏱️ **Wait Time**: {wait_time} minutes
ℹ️ {additional_info}

Stay calm and follow instructions."""
            },
            NotificationTemplate.AREA_CLOSURE: {
                "subject": "⛔ Area Closure Notice",
                "sms": "AREA CLOSURE: {area} closed from {start_time}. Alternative routes: {alternatives}. Duration: {duration}",
                "whatsapp": """⛔ *AREA CLOSURE NOTICE*

📍 **Closed Area**: {area}
🕐 **From**: {start_time}
⏰ **Duration**: {duration}
🔄 **Alternatives**: {alternatives}"""
            },
            NotificationTemplate.TRANSPORT_UPDATE: {
                "subject": "🚇 Transport Update",
                "sms": "TRANSPORT: {service} - {status}. Alternative: {alternative}. Expected: {eta}",
                "whatsapp": """🚇 *TRANSPORT UPDATE*

🚌 **Service**: {service}
📊 **Status**: {status}
🔄 **Alternative**: {alternative}
⏰ **Expected**: {eta}"""
            },
            NotificationTemplate.SIMULATION_COMPLETE: {
                "subject": "✅ Simulation Complete",
                "sms": "Evacuation simulation complete. Best strategy: {best_scenario}. Clearance time: {clearance_time}min. View results: {results_url}",
                "whatsapp": """✅ *EVACUATION SIMULATION COMPLETE*

🏆 **Best Strategy**: {best_scenario}
⏱️ **Clearance Time**: {clearance_time} minutes
📊 **Confidence**: {confidence}%

View detailed results: {results_url}"""
            },
            NotificationTemplate.DECISION_MEMO_READY: {
                "subject": "📑 Decision Memo Ready",
                "sms": "Decision memo ready for Run {run_id}. Recommendation: {recommendation}. Confidence: {confidence}%. Access: {memo_url}",
                "whatsapp": """📑 *DECISION MEMO READY*

🆔 **Run ID**: {run_id}
💡 **Recommendation**: {recommendation}
📈 **Confidence**: {confidence}%

Access memo: {memo_url}

*Prepared for No 10 & National Situation Centre*"""
            }
        }

    async def send_notification(self, request: NotificationRequest) -> NotificationResponse:
        """Send a notification via SMS or WhatsApp."""
        if not self.client:
            raise ValueError("Twilio client not initialized. Check credentials.")

        logger.info("Sending notification",
                   recipient=request.recipient,
                   type=request.message_type,
                   priority=request.priority)

        try:
            # Get message content
            message_body = self._get_message_body(request)

            # Determine sender based on message type
            from_number = self._get_sender_number(request.message_type)

            # Send message
            if request.message_type == NotificationType.SMS:
                message = await self._send_sms(
                    to=request.recipient,
                    from_=from_number,
                    body=message_body
                )
            elif request.message_type == NotificationType.WHATSAPP:
                message = await self._send_whatsapp(
                    to=f"whatsapp:{request.recipient}",
                    from_=f"whatsapp:{from_number}",
                    body=message_body
                )
            else:
                raise ValueError(f"Unsupported message type: {request.message_type}")

            response = NotificationResponse(
                message_sid=message.sid,
                recipient=request.recipient,
                message_type=request.message_type,
                status=message.status,
                sent_at=datetime.now(timezone.utc)
            )

            logger.info("Notification sent successfully",
                       message_sid=message.sid,
                       status=message.status)

            return response

        except TwilioException as e:
            logger.error("Twilio API error", error=str(e), error_code=getattr(e, 'code', None))
            return NotificationResponse(
                message_sid="",
                recipient=request.recipient,
                message_type=request.message_type,
                status="failed",
                sent_at=datetime.now(timezone.utc),
                error_message=str(e)
            )
        except Exception as e:
            logger.error("Failed to send notification", error=str(e))
            raise

    async def send_bulk_notifications(self, requests: List[NotificationRequest]) -> List[NotificationResponse]:
        """Send multiple notifications concurrently."""
        logger.info("Sending bulk notifications", count=len(requests))

        # Send all notifications concurrently
        tasks = [self.send_notification(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error("Failed to send notification",
                           recipient=requests[i].recipient,
                           error=str(response))
                results.append(NotificationResponse(
                    message_sid="",
                    recipient=requests[i].recipient,
                    message_type=requests[i].message_type,
                    status="failed",
                    sent_at=datetime.now(timezone.utc),
                    error_message=str(response)
                ))
            else:
                results.append(response)

        successful = len([r for r in results if r.status != "failed"])
        logger.info("Bulk notifications complete",
                   total=len(requests),
                   successful=successful,
                   failed=len(requests) - successful)

        return results

    async def send_evacuation_alert(self,
                                  recipients: List[str],
                                  area: str,
                                  route_id: str,
                                  exit_points: str,
                                  closed_roads: str,
                                  info_url: str = "",
                                  authority: str = "UK Government Emergency Response") -> List[NotificationResponse]:
        """Send evacuation alert to multiple recipients."""
        template_data = {
            "area": area,
            "route_id": route_id,
            "exit_points": exit_points,
            "closed_roads": closed_roads,
            "info_url": info_url or "gov.uk/emergency",
            "authority": authority
        }

        requests = []
        for recipient in recipients:
            # Send both SMS and WhatsApp if possible
            requests.extend([
                NotificationRequest(
                    recipient=recipient,
                    message_type=NotificationType.SMS,
                    priority=NotificationPriority.CRITICAL,
                    template=NotificationTemplate.EVACUATION_ALERT,
                    template_data=template_data
                ),
                NotificationRequest(
                    recipient=recipient,
                    message_type=NotificationType.WHATSAPP,
                    priority=NotificationPriority.CRITICAL,
                    template=NotificationTemplate.EVACUATION_ALERT,
                    template_data=template_data
                )
            ])

        return await self.send_bulk_notifications(requests)

    async def notify_simulation_complete(self,
                                       recipients: List[str],
                                       run_id: str,
                                       best_scenario: str,
                                       clearance_time: float,
                                       confidence: float,
                                       results_url: str = "") -> List[NotificationResponse]:
        """Notify stakeholders when simulation is complete."""
        template_data = {
            "run_id": run_id,
            "best_scenario": best_scenario,
            "clearance_time": int(clearance_time),
            "confidence": int(confidence * 100),
            "results_url": results_url or f"localhost:3000/results/{run_id}"
        }

        requests = []
        for recipient in recipients:
            requests.append(NotificationRequest(
                recipient=recipient,
                message_type=NotificationType.WHATSAPP,
                priority=NotificationPriority.HIGH,
                template=NotificationTemplate.SIMULATION_COMPLETE,
                template_data=template_data
            ))

        return await self.send_bulk_notifications(requests)

    async def notify_decision_memo_ready(self,
                                       recipients: List[str],
                                       run_id: str,
                                       recommendation: str,
                                       confidence: float,
                                       memo_url: str = "") -> List[NotificationResponse]:
        """Notify decision makers when memo is ready."""
        template_data = {
            "run_id": run_id,
            "recommendation": recommendation,
            "confidence": int(confidence * 100),
            "memo_url": memo_url or f"localhost:3000/results/{run_id}"
        }

        requests = []
        for recipient in recipients:
            requests.append(NotificationRequest(
                recipient=recipient,
                message_type=NotificationType.WHATSAPP,
                priority=NotificationPriority.HIGH,
                template=NotificationTemplate.DECISION_MEMO_READY,
                template_data=template_data
            ))

        return await self.send_bulk_notifications(requests)

    def _get_message_body(self, request: NotificationRequest) -> str:
        """Get formatted message body."""
        if request.custom_message:
            return request.custom_message

        if not request.template:
            raise ValueError("Either custom_message or template must be provided")

        template = self._templates.get(request.template)
        if not template:
            raise ValueError(f"Unknown template: {request.template}")

        message_format = template.get(request.message_type.value)
        if not message_format:
            raise ValueError(f"No template for message type: {request.message_type}")

        try:
            return message_format.format(**request.template_data)
        except KeyError as e:
            raise ValueError(f"Missing template data: {e}")

    def _get_sender_number(self, message_type: NotificationType) -> str:
        """Get sender number based on message type."""
        if message_type == NotificationType.SMS:
            return os.getenv("TWILIO_SMS_NUMBER", "+442070000000")
        elif message_type == NotificationType.WHATSAPP:
            return os.getenv("TWILIO_WHATSAPP_NUMBER", "+442070000000")
        else:
            raise ValueError(f"Unsupported message type: {message_type}")

    async def _send_sms(self, to: str, from_: str, body: str):
        """Send SMS message."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(to=to, from_=from_, body=body)
        )

    async def _send_whatsapp(self, to: str, from_: str, body: str):
        """Send WhatsApp message."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(to=to, from_=from_, body=body)
        )


# Singleton instance
_notification_service: Optional[TwilioNotificationService] = None


def get_notification_service() -> TwilioNotificationService:
    """Get singleton notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = TwilioNotificationService()
    return _notification_service


# Convenience functions for common operations
async def send_government_alert(message: str, priority: NotificationPriority = NotificationPriority.HIGH) -> List[NotificationResponse]:
    """Send alert to the predefined government contact."""
    service = get_notification_service()

    government_contact = os.getenv("GOVERNMENT_CONTACT_NUMBER")

    requests = [
        NotificationRequest(
            recipient=government_contact,
            message_type=NotificationType.SMS,
            priority=priority,
            custom_message=f"🇬🇧 EVACUATION SYSTEM: {message}"
        ),
        NotificationRequest(
            recipient=government_contact,
            message_type=NotificationType.WHATSAPP,
            priority=priority,
            custom_message=f"🇬🇧 *UK EVACUATION PLANNING SYSTEM*\n\n{message}\n\n_Automated message from London Evacuation Planning Tool_"
        )
    ]

    return await service.send_bulk_notifications(requests)


async def notify_simulation_result(run_id: str, best_scenario: str, clearance_time: float, confidence: float) -> List[NotificationResponse]:
    """Quick function to notify simulation completion."""
    service = get_notification_service()
    government_contact = os.getenv("GOVERNMENT_CONTACT_NUMBER")

    return await service.notify_simulation_complete(
        recipients=[government_contact],
        run_id=run_id,
        best_scenario=best_scenario,
        clearance_time=clearance_time,
        confidence=confidence
    )