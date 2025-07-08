# test_graylog.py
import socket
import json
import time

def test_graylog_connection():
    try:
        # Create a test message
        test_message = {
            "version": "1.1",
            "host": "test-host",
            "short_message": "Test message from Python",
            "timestamp": time.time(),
            "level": 1,
            "facility": "SITSecure",
            "_event_type": "test_connection"
        }
        
        # Send via UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        message = json.dumps(test_message).encode('utf-8')
        sock.sendto(message, ('localhost', 12201))
        sock.close()
        
        print("✅ Test message sent successfully!")
        print("Check Graylog for: facility:SITSecure AND event_type:test_connection")
        
    except Exception as e:
        print(f"❌ Error sending test message: {e}")

if __name__ == "__main__":
    test_graylog_connection()