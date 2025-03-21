"""
Custom Logstash handler for Django.
"""
import logging
import socket
import time
from logging.handlers import SocketHandler


class RobustTCPLogstashHandler(SocketHandler):
    """
    A logging handler that sends logs to Logstash via TCP.
    This handler is designed to be robust against connection failures.
    """
    
    def __init__(self, host, port, formatter=None, tags=None, message_type="logstash", fqdn=False, version=1):
        """
        Initialize the handler with host and port.
        
        Args:
            host (str): The host to connect to
            port (int): The port to connect to
            formatter: The formatter to use for formatting log records
            tags (list): Tags to add to the Logstash message
            message_type (str): The type of the message
            fqdn (bool): Whether to use the fully qualified domain name
            version (int): The version of the Logstash event schema
        """
        super().__init__(host, port)
        self.host = host
        self.port = port
        self.tags = tags or []
        self.message_type = message_type
        self.fqdn = fqdn
        self.version = version
        self.sock = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.last_connection_attempt = 0
        self.connection_attempt_timeout = 5  # seconds
        
        if formatter:
            self.setFormatter(formatter)
    
    def connect(self):
        """
        Connect to the Logstash server.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        # Check if we've exceeded the maximum number of connection attempts
        if self.connection_attempts >= self.max_connection_attempts:
            # Check if enough time has passed since the last connection attempt
            if time.time() - self.last_connection_attempt < self.connection_attempt_timeout:
                return False
            # Reset the connection attempts counter
            self.connection_attempts = 0
        
        # Update the last connection attempt time
        self.last_connection_attempt = time.time()
        # Increment the connection attempts counter
        self.connection_attempts += 1
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1)  # Set a timeout of 1 second
            self.sock.connect((self.host, self.port))
            # Reset the connection attempts counter on successful connection
            self.connection_attempts = 0
            return True
        except (socket.error, socket.timeout):
            self.sock = None
            return False
    
    def emit(self, record):
        """
        Emit a record.
        
        Args:
            record: The log record to emit
        """
        try:
            # Format the record
            msg = self.format(record)
            
            # Try to send the log to Logstash
            try:
                # Connect if not connected
                if not self.sock:
                    if not self.connect():
                        return
                
                # Convert to bytes if necessary
                if isinstance(msg, str):
                    msg = msg.encode("utf-8")
                
                # Add newline if not present
                if not msg.endswith(b"\n"):
                    msg = msg + b"\n"
                
                # Send the log
                self.sock.sendall(msg)
            except (socket.error, socket.timeout):
                # Close the socket and try to reconnect next time
                self.sock = None
        except Exception:
            self.handleError(record)
    
    def close(self):
        """
        Close the connection.
        """
        if self.sock:
            self.sock.close()
            self.sock = None
        super().close()


class RobustHTTPHandler(logging.Handler):
    """
    A logging handler that sends logs to Logstash via HTTP.
    This handler is designed to be robust against connection failures.
    """
    
    def __init__(self, host, url, method="POST", formatter=None):
        """
        Initialize the handler.
        
        Args:
            host (str): The host to connect to (e.g., 'logstash:5044')
            url (str): The URL to send logs to (e.g., '/')
            method (str): The HTTP method to use (e.g., 'POST')
            formatter: The formatter to use for formatting log records
        """
        super().__init__()
        self.host = host
        self.url = url
        self.method = method
        if formatter:
            self.setFormatter(formatter)
    
    def emit(self, record):
        """
        Emit a record.
        
        Args:
            record: The log record to emit
        """
        try:
            # Format the record
            msg = self.format(record)
            
            # Try to send the log to Logstash
            try:
                # Import here to avoid circular imports
                import http.client
                
                # Parse host and port
                if ":" in self.host:
                    host, port = self.host.split(":")
                    port = int(port)
                else:
                    host = self.host
                    port = 80
                
                # Create connection
                conn = http.client.HTTPConnection(host, port, timeout=1)
                
                # Send request
                headers = {"Content-Type": "application/json"}
                conn.request(self.method, self.url, msg, headers)
                
                # Close connection
                conn.close()
            except Exception:
                # Silently ignore connection errors
                pass
        except Exception:
            self.handleError(record)


# For backward compatibility, keep the original class name
CustomTCPLogstashHandler = RobustTCPLogstashHandler
