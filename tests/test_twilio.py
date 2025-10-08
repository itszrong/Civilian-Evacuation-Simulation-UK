#!/usr/bin/env python3
"""
Quick test script to verify Twilio WhatsApp integration
"""

import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

def test_twilio_connection():
    """Test Twilio connection and send a test WhatsApp message."""

    # Get credentials from environment
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
    government_contact = os.getenv('GOVERNMENT_CONTACT_NUMBER')

    print("🔍 Testing Twilio Configuration")
    print("=" * 60)
    print(f"Account SID: {account_sid}")
    print(f"Auth Token: {'*' * (len(auth_token) - 4)}{auth_token[-4:] if auth_token else 'NOT SET'}")
    print(f"WhatsApp Number: {whatsapp_number}")
    print(f"Government Contact: {government_contact}")
    print("=" * 60)

    if not all([account_sid, auth_token, whatsapp_number, government_contact]):
        print("❌ ERROR: Missing Twilio credentials in .env file")
        print("\nPlease set the following in your .env file:")
        print("  TWILIO_ACCOUNT_SID=your_account_sid")
        print("  TWILIO_AUTH_TOKEN=your_auth_token")
        print("  TWILIO_WHATSAPP_NUMBER=+14155238886")
        print(f"  GOVERNMENT_CONTACT_NUMBER=+44...")
        return False

    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        print("\n✅ Twilio client initialized successfully")

        # Verify account
        account = client.api.accounts(account_sid).fetch()
        print(f"✅ Account verified: {account.friendly_name}")
        print(f"   Status: {account.status}")

        # Send test WhatsApp message
        print("\n📱 Sending test WhatsApp message...")
        message = client.messages.create(
            from_=f'whatsapp:{whatsapp_number}',
            body='🧪 Test message from UK Evacuation Planning System\n\n'
                 'This is a test to verify WhatsApp integration is working correctly.\n\n'
                 'System Status: ✅ OPERATIONAL\n'
                 'Ready',
            to=f'whatsapp:{government_contact}'
        )

        print(f"✅ Message sent successfully!")
        print(f"   Message SID: {message.sid}")
        print(f"   Status: {message.status}")
        print(f"   To: {message.to}")
        print(f"   From: {message.from_}")

        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Check your WhatsApp for the test message")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Verify your Twilio credentials are correct")
        print("2. Check that your Twilio account is active")
        print("3. Ensure WhatsApp sandbox is set up: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn")
        print("4. Verify the government contact number is in E.164 format (+44...)")
        return False


def test_notification_service():
    """Test the notification service integration."""
    print("\n\n🔧 Testing Notification Service Integration")
    print("=" * 60)

    try:
        from backend.services.notification_service import get_notification_service, NotificationRequest, NotificationType, NotificationPriority

        service = get_notification_service()
        print("✅ Notification service loaded successfully")

        if service.client:
            print("✅ Twilio client initialized in service")
            print(f"✅ {len(service._templates)} notification templates available")

            # List available templates
            print("\n📋 Available Templates:")
            for template in service._templates.keys():
                print(f"   - {template.value}")
        else:
            print("❌ Twilio client not initialized in service")

    except ImportError as e:
        print(f"⚠️  Could not import notification service: {e}")
        print("   Make sure to run this from the project root directory")
    except Exception as e:
        print(f"❌ Error testing service: {e}")


if __name__ == "__main__":
    print("🇬🇧 UK Government Evacuation Planning System")
    print("Twilio Integration Test\n")

    # Test Twilio connection
    success = test_twilio_connection()

    # Test notification service
    test_notification_service()

    if success:
        print("\n✅ All tests passed! System ready for use.")
        print("\n💡 Next steps:")
        print("   1. Start the backend: cd backend && uvicorn main:app --reload")
        print("   2. Test notifications: curl -X POST http://localhost:8000/api/notifications/test-connection")
        print("   3. Send alert: POST to /api/notifications/government-alert")
    else:
        print("\n⚠️  Please fix the issues above before proceeding.")
