import logging
import asyncio
import json
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class ConnectionType(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    PARENT = "parent"
    CASHIER = "cashier"

class WebSocketService:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            ConnectionType.ADMIN: set(),
            ConnectionType.TEACHER: set(),
            ConnectionType.PARENT: set(),
            ConnectionType.CASHIER: set()
        }
        self.user_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        self.initialized = False
        
    async def initialize(self):
        """Initialize WebSocket service"""
        try:
            self.initialized = True
            logger.info("WebSocket service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket service: {e}")
    
    async def connect(self, websocket: WebSocket, user_id: str, connection_type: ConnectionType, metadata: Dict = None):
        """Connect a new WebSocket client"""
        try:
            await websocket.accept()
            
            # Store connection
            self.user_connections[user_id] = websocket
            self.active_connections[connection_type].add(websocket)
            
            # Store metadata
            self.connection_metadata[websocket] = {
                "user_id": user_id,
                "connection_type": connection_type,
                "connected_at": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            # Send welcome message
            await self.send_personal_message(
                websocket,
                {
                    "type": "connection_established",
                    "message": "Connected to Fee Master real-time updates",
                    "user_id": user_id,
                    "connection_type": connection_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Broadcast user connected event
            await self.broadcast_to_type(
                connection_type,
                {
                    "type": "user_connected",
                    "user_id": user_id,
                    "connection_type": connection_type,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_websocket=websocket
            )
            
            logger.info(f"WebSocket connected: {user_id} ({connection_type})")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            raise
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        try:
            metadata = self.connection_metadata.get(websocket, {})
            user_id = metadata.get("user_id")
            connection_type = metadata.get("connection_type")
            
            if user_id:
                self.user_connections.pop(user_id, None)
            
            if connection_type:
                self.active_connections[connection_type].discard(websocket)
            
            self.connection_metadata.pop(websocket, None)
            
            # Broadcast user disconnected event
            if user_id and connection_type:
                await self.broadcast_to_type(
                    connection_type,
                    {
                        "type": "user_disconnected",
                        "user_id": user_id,
                        "connection_type": connection_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            logger.info(f"WebSocket disconnected: {user_id} ({connection_type})")
            
        except Exception as e:
            logger.error(f"Failed to disconnect WebSocket: {e}")
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)
    
    async def send_to_user(self, user_id: str, message: Dict):
        """Send message to specific user"""
        try:
            websocket = self.user_connections.get(user_id)
            if websocket:
                await self.send_personal_message(websocket, message)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return False
    
    async def broadcast_to_type(self, connection_type: ConnectionType, message: Dict, exclude_websocket: WebSocket = None):
        """Broadcast message to all connections of a specific type"""
        try:
            disconnected = set()
            
            for websocket in self.active_connections[connection_type]:
                if websocket != exclude_websocket:
                    try:
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Failed to broadcast to {connection_type}: {e}")
                        disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected:
                await self.disconnect(websocket)
                
        except Exception as e:
            logger.error(f"Failed to broadcast to {connection_type}: {e}")
    
    async def broadcast_to_all(self, message: Dict, exclude_websocket: WebSocket = None):
        """Broadcast message to all connected clients"""
        try:
            for connection_type in ConnectionType:
                await self.broadcast_to_type(connection_type, message, exclude_websocket)
        except Exception as e:
            logger.error(f"Failed to broadcast to all: {e}")
    
    async def send_payment_notification(self, payment_data: Dict):
        """Send payment notification to relevant users"""
        try:
            message = {
                "type": "payment_received",
                "data": {
                    "receipt_number": payment_data.get("receipt_number"),
                    "amount": payment_data.get("amount"),
                    "student_name": payment_data.get("student_name"),
                    "payment_method": payment_data.get("payment_method"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to cashiers and admins
            await self.broadcast_to_type(ConnectionType.CASHIER, message)
            await self.broadcast_to_type(ConnectionType.ADMIN, message)
            
            # Send to specific parent if available
            if payment_data.get("parent_id"):
                await self.send_to_user(payment_data["parent_id"], message)
                
        except Exception as e:
            logger.error(f"Failed to send payment notification: {e}")
    
    async def send_fee_reminder_notification(self, reminder_data: Dict):
        """Send fee reminder notification"""
        try:
            message = {
                "type": "fee_reminder",
                "data": {
                    "student_name": reminder_data.get("student_name"),
                    "amount_due": reminder_data.get("amount_due"),
                    "due_date": reminder_data.get("due_date"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to admins and teachers
            await self.broadcast_to_type(ConnectionType.ADMIN, message)
            await self.broadcast_to_type(ConnectionType.TEACHER, message)
            
            # Send to specific parent
            if reminder_data.get("parent_id"):
                await self.send_to_user(reminder_data["parent_id"], message)
                
        except Exception as e:
            logger.error(f"Failed to send fee reminder notification: {e}")
    
    async def send_system_alert(self, alert_data: Dict):
        """Send system alert to all users"""
        try:
            message = {
                "type": "system_alert",
                "data": {
                    "title": alert_data.get("title"),
                    "message": alert_data.get("message"),
                    "severity": alert_data.get("severity", "info"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            await self.broadcast_to_all(message)
            
        except Exception as e:
            logger.error(f"Failed to send system alert: {e}")
    
    async def send_dashboard_update(self, dashboard_data: Dict, connection_type: ConnectionType = None):
        """Send dashboard update to relevant users"""
        try:
            message = {
                "type": "dashboard_update",
                "data": dashboard_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if connection_type:
                await self.broadcast_to_type(connection_type, message)
            else:
                await self.broadcast_to_all(message)
                
        except Exception as e:
            logger.error(f"Failed to send dashboard update: {e}")
    
    async def send_student_update(self, student_data: Dict):
        """Send student update notification"""
        try:
            message = {
                "type": "student_update",
                "data": {
                    "student_id": student_data.get("id"),
                    "student_name": student_data.get("name"),
                    "action": student_data.get("action"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to admins, teachers, and cashiers
            await self.broadcast_to_type(ConnectionType.ADMIN, message)
            await self.broadcast_to_type(ConnectionType.TEACHER, message)
            await self.broadcast_to_type(ConnectionType.CASHIER, message)
            
        except Exception as e:
            logger.error(f"Failed to send student update: {e}")
    
    async def send_attendance_update(self, attendance_data: Dict):
        """Send attendance update notification"""
        try:
            message = {
                "type": "attendance_update",
                "data": {
                    "class_name": attendance_data.get("class_name"),
                    "date": attendance_data.get("date"),
                    "present_count": attendance_data.get("present_count"),
                    "absent_count": attendance_data.get("absent_count"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to teachers and admins
            await self.broadcast_to_type(ConnectionType.TEACHER, message)
            await self.broadcast_to_type(ConnectionType.ADMIN, message)
            
        except Exception as e:
            logger.error(f"Failed to send attendance update: {e}")
    
    async def handle_websocket_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self.send_personal_message(websocket, {"type": "pong"})
            elif message_type == "subscribe":
                # Handle subscription to specific events
                events = data.get("events", [])
                metadata = self.connection_metadata.get(websocket, {})
                metadata["subscribed_events"] = events
                await self.send_personal_message(websocket, {
                    "type": "subscribed",
                    "events": events
                })
            elif message_type == "unsubscribe":
                # Handle unsubscription
                metadata = self.connection_metadata.get(websocket, {})
                metadata["subscribed_events"] = []
                await self.send_personal_message(websocket, {
                    "type": "unsubscribed"
                })
            else:
                # Unknown message type
                await self.send_personal_message(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except json.JSONDecodeError:
            await self.send_personal_message(websocket, {
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Failed to handle WebSocket message: {e}")
            await self.send_personal_message(websocket, {
                "type": "error",
                "message": "Internal server error"
            })
    
    async def get_connection_stats(self) -> Dict:
        """Get WebSocket connection statistics"""
        try:
            stats = {
                "total_connections": len(self.user_connections),
                "connections_by_type": {},
                "active_since": datetime.utcnow().isoformat()
            }
            
            for connection_type in ConnectionType:
                stats["connections_by_type"][connection_type] = len(self.active_connections[connection_type])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {}
    
    async def cleanup_inactive_connections(self):
        """Clean up inactive WebSocket connections"""
        try:
            inactive_websockets = []
            
            for websocket, metadata in self.connection_metadata.items():
                connected_at = metadata.get("connected_at")
                if connected_at:
                    # Check if connection is older than 24 hours
                    if (datetime.utcnow() - connected_at).total_seconds() > 86400:
                        inactive_websockets.append(websocket)
            
            for websocket in inactive_websockets:
                await self.disconnect(websocket)
                
            if inactive_websockets:
                logger.info(f"Cleaned up {len(inactive_websockets)} inactive connections")
                
        except Exception as e:
            logger.error(f"Failed to cleanup inactive connections: {e}")

# Initialize service
websocket_service = WebSocketService()
