# raft_server.py
import sys
import os
import time
import json
import grpc
from concurrent import futures
import logging
import argparse
import threading

# Import our Raft implementation
from raft_node import RaftNode, NodeState

# Import the gRPC generated modules
import exp_pb2
import exp_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("raft_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add RPC definitions for Raft
class RaftServiceServicer(exp_pb2_grpc.RaftServiceServicer):
    """
    Implements the RaftService RPCs.
    """
    def __init__(self, raft_node):
        self.raft_node = raft_node

    def LeaderPing(self, request, context):
        """Handle LeaderPing RPC."""
        return self.raft_node.LeaderPing(request, context)

    def RequestVote(self, request, context):
        """Handle RequestVote RPC."""
        return self.raft_node.RequestVote(request, context)

    def AppendEntries(self, request, context):
        """Handle AppendEntries RPC."""
        return self.raft_node.AppendEntries(request, context)

class RaftMessagingServicer(exp_pb2_grpc.MessagingServiceServicer):
    """
    gRPC service implementation that delegates operations to a Raft node.
    """
    
    def __init__(self, raft_node):
        self.raft_node = raft_node

    
    def CreateAccount(self, request, context):
        """
        Create a new user account.
        
        This operation is forwarded to the Raft leader, which will replicate it to all nodes.
        """
        username = request.username
        password_hash = request.password_hash.hex()
        
        logger.info(f"(raft_server.py): Received CreateAccount request for user: {username}, at node: {self.raft_node.node_id}")

        success, token = self.raft_node.create_account(username, password_hash)
        
        if not success:

            logger.info(f"(raft_server.py): create_account failed: {token}")
            
            # If we're not the leader, inform the client
            if self.raft_node.state != NodeState.LEADER and self.raft_node.leader_id:
                # Return the leader's address so the client can redirect
                leader_addr = self.raft_node.cluster_config.get(self.raft_node.leader_id, "")
                context.set_details(f"Not the leader. Try {leader_addr}")
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                return exp_pb2.CreateAccountResponse()
            else:
                context.set_details("Failed to create account")
                context.set_code(grpc.StatusCode.INTERNAL)
                return exp_pb2.CreateAccountResponse()
        
        # Convert token hex to bytes for response
        session_token_bytes = bytes.fromhex(token)
        return exp_pb2.CreateAccountResponse(session_token=session_token_bytes)
    
    def Login(self, request, context):
        """Handle login requests."""
        username = request.username
        password_hash = request.password_hash.hex()
        
        logger.info(f"Received Login request for user: {username}")
        
        # Try to find the user
        success, user_id, token, unread_count = self.raft_node.login(username, password_hash)
        
        if not success:
            # If we're not the leader, inform the client
            if self.raft_node.state != NodeState.LEADER and self.raft_node.leader_id:
                leader_addr = self.raft_node.cluster_config.get(self.raft_node.leader_id, "")
                context.set_details(f"Not the leader. Try {leader_addr}")
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                return exp_pb2.LoginResponse()
            
            # Invalid credentials
            return exp_pb2.LoginResponse(
                status=exp_pb2.STATUS_FAILURE,
                session_token=b"",
                unread_count=0
            )
        
        # Convert token hex to bytes for response
        session_token_bytes = bytes.fromhex(token)
        return exp_pb2.LoginResponse(
            status=exp_pb2.STATUS_SUCCESS,
            session_token=session_token_bytes,
            unread_count=unread_count
        )
    
    def ListAccounts(self, request, context):
        """List accounts matching a wildcard pattern."""
        user_id = request.user_id
        session_token = request.session_token.hex()
        wildcard = request.wildcard
        
        logger.info(f"Received ListAccounts request with wildcard: {wildcard}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.ListAccountsResponse()
        
        # Get matching usernames
        usernames = self.raft_node.list_accounts(wildcard)
        
        return exp_pb2.ListAccountsResponse(
            account_count=len(usernames),
            usernames=usernames
        )
    
    def DisplayConversation(self, request, context):
        """Display conversation between two users."""
        user_id = request.user_id
        session_token = request.session_token.hex()
        conversant_id = request.conversant_id
        
        logger.info(f"Received DisplayConversation request between {user_id} and {conversant_id}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.DisplayConversationResponse()
        
        # Get conversation messages
        messages = self.raft_node.display_conversation(user_id, conversant_id)
        
        # Convert to ConversationMessage protos
        conv_msgs = []
        for msg in messages:
            is_sender = (msg.sender_id == user_id)
            conv_msgs.append(exp_pb2.ConversationMessage(
                message_id=msg.uid,
                sender_flag=is_sender,
                content=msg.contents
            ))
        
        return exp_pb2.DisplayConversationResponse(
            message_count=len(conv_msgs),
            messages=conv_msgs
        )
    
    def SendMessage(self, request, context):
        """Send a message from one user to another."""
        sender_id = request.sender_user_id
        session_token = request.session_token.hex()
        recipient_id = request.recipient_user_id
        content = request.message_content
        
        logger.info(f"Received SendMessage from {sender_id} to {recipient_id}")
        
        # Validate session token
        if not self.raft_node.validate_session(sender_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.SendMessageResponse()
        
        # Forward to the leader if we're not the leader
        if self.raft_node.state != NodeState.LEADER:
            if self.raft_node.leader_id and self.raft_node.leader_id in self.raft_node.peers:
                try:
                    stub = self.raft_node.peers[self.raft_node.leader_id]
                    return stub.SendMessage(request)
                except Exception as e:
                    logger.error(f"Failed to forward SendMessage to leader: {str(e)}")
                    context.set_details("Failed to forward to leader")
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    return exp_pb2.SendMessageResponse()
            else:
                context.set_details("No leader available")
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                return exp_pb2.SendMessageResponse()
        
        # If we are the leader, process the message
        success = self.raft_node.send_message(sender_id, recipient_id, content)
        
        if not success:
            context.set_details("Failed to send message")
            context.set_code(grpc.StatusCode.INTERNAL)
        
        return exp_pb2.SendMessageResponse()
    
    def ReadMessages(self, request, context):
        """Mark messages as read."""
        user_id = request.user_id
        session_token = request.session_token.hex()
        count = request.number_of_messages_req
        
        logger.info(f"Received ReadMessages request for user {user_id}, count {count}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.ReadMessagesResponse()
        
        # Forward to leader if needed
        if self.raft_node.state != NodeState.LEADER:
            if self.raft_node.leader_id and self.raft_node.leader_id in self.raft_node.peers:
                try:
                    stub = self.raft_node.peers[self.raft_node.leader_id]
                    return stub.ReadMessages(request)
                except Exception as e:
                    logger.error(f"Failed to forward ReadMessages to leader: {str(e)}")
                    context.set_details("Failed to forward to leader")
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    return exp_pb2.ReadMessagesResponse()
            else:
                context.set_details("No leader available")
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                return exp_pb2.ReadMessagesResponse()
        
        # Process on leader
        self.raft_node.read_messages(user_id, count)
        
        return exp_pb2.ReadMessagesResponse()
    
    def DeleteMessage(self, request, context):
        """Delete a message."""
        user_id = request.user_id
        message_uid = request.message_uid
        session_token = request.session_token.hex()
        
        logger.info(f"Received DeleteMessage request for message {message_uid}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.DeleteMessageResponse()
        
        # Forward to leader if needed
        if self.raft_node.state != NodeState.LEADER:
            if self.raft_node.leader_id and self.raft_node.leader_id in self.raft_node.peers:
                try:
                    stub = self.raft_node.peers[self.raft_node.leader_id]
                    return stub.DeleteMessage(request)
                except Exception as e:
                    logger.error(f"Failed to forward DeleteMessage to leader: {str(e)}")
                    context.set_details("Failed to forward to leader")
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    return exp_pb2.DeleteMessageResponse()
            else:
                context.set_details("No leader available")
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                return exp_pb2.DeleteMessageResponse()
        
        # Process on leader
        success = self.raft_node.delete_message(message_uid)
        
        if not success:
            context.set_details("Failed to delete message")
            context.set_code(grpc.StatusCode.INTERNAL)
        
        return exp_pb2.DeleteMessageResponse()
    
    def DeleteAccount(self, request, context):
        """Delete a user account."""
        user_id = request.user_id
        session_token = request.session_token.hex()
        
        logger.info(f"Received DeleteAccount request for user {user_id}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.DeleteAccountResponse()
        
        # Forward to leader if needed
        if self.raft_node.state != NodeState.LEADER:
            if self.raft_node.leader_id and self.raft_node.leader_id in self.raft_node.peers:
                try:
                    stub = self.raft_node.peers[self.raft_node.leader_id]
                    return stub.DeleteAccount(request)
                except Exception as e:
                    logger.error(f"Failed to forward DeleteAccount to leader: {str(e)}")
                    context.set_details("Failed to forward to leader")
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    return exp_pb2.DeleteAccountResponse()
            else:
                context.set_details("No leader available")
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                return exp_pb2.DeleteAccountResponse()
        
        # Process on leader
        success = self.raft_node.delete_account(user_id)
        
        if not success:
            context.set_details("Failed to delete account")
            context.set_code(grpc.StatusCode.INTERNAL)
        
        return exp_pb2.DeleteAccountResponse()
    
    def GetUnreadMessages(self, request, context):
        """Get unread messages for a user."""
        user_id = request.user_id
        session_token = request.session_token.hex()
        
        logger.info(f"Received GetUnreadMessages request for user {user_id}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.GetUnreadMessagesResponse()
        
        # Get unread messages (can work on any node, not just leader)
        unread_msgs = self.raft_node.get_unread_messages(user_id)
        
        # Convert to response format
        result_msgs = []
        for msg in unread_msgs:
            result_msgs.append(exp_pb2.UnreadMessageInfo(
                message_uid=msg[0],
                sender_id=msg[1],
                receiver_id=msg[2]
            ))
        
        return exp_pb2.GetUnreadMessagesResponse(
            count=len(result_msgs),
            messages=result_msgs
        )
    
    def GetMessageInformation(self, request, context):
        """Get information about a specific message."""
        user_id = request.user_id
        message_uid = request.message_uid
        session_token = request.session_token.hex()
        
        logger.info(f"Received GetMessageInformation request for message {message_uid}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.GetMessageInformationResponse()
        
        # Get message info (can work on any node)
        read_flag, sender_id, content, timestamp = self.raft_node.get_message_info(user_id, message_uid)
        
        content_bytes = content.encode() if content else b''
        
        return exp_pb2.GetMessageInformationResponse(
            read_flag=read_flag,
            sender_id=sender_id,
            content_length=len(content_bytes),
            message_content=content
        )
    
    def GetUsernameByID(self, request, context):
        """Get username from user ID."""
        user_id = request.user_id
        
        logger.info(f"Received GetUsernameByID request for user {user_id}")
        
        # This can be processed on any node
        username = self.raft_node.get_username_by_id(user_id)
        
        return exp_pb2.GetUsernameByIDResponse(
            username=username
        )
    
    def MarkMessageAsRead(self, request, context):
        """Mark a message as read."""
        user_id = request.user_id
        message_uid = request.message_uid
        session_token = request.session_token.hex()
        
        logger.info(f"Received MarkMessageAsRead request for message {message_uid}")
        
        # Validate session token
        if not self.raft_node.validate_session(user_id, session_token):
            context.set_details("Invalid session token")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return exp_pb2.MarkMessageAsReadResponse()
        
        # Forward to leader if needed
        if self.raft_node.state != NodeState.LEADER:
            if self.raft_node.leader_id and self.raft_node.leader_id in self.raft_node.peers:
                try:
                    stub = self.raft_node.peers[self.raft_node.leader_id]
                    return stub.MarkMessageAsRead(request)
                except Exception as e:
                    logger.error(f"Failed to forward MarkMessageAsRead to leader: {str(e)}")
                    context.set_details("Failed to forward to leader")
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    return exp_pb2.MarkMessageAsReadResponse()
            else:
                context.set_details("No leader available")
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                return exp_pb2.MarkMessageAsReadResponse()
        
        # Process on leader
        success = self.raft_node.mark_message_as_read(user_id, message_uid)
        
        if not success:
            context.set_details("Failed to mark message as read")
            context.set_code(grpc.StatusCode.INTERNAL)
        
        return exp_pb2.MarkMessageAsReadResponse()
    
    def GetUserByUsername(self, request, context):
        """Get user ID from username."""
        username = request.username
        
        logger.info(f"Received GetUserByUsername request for username {username}")
        
        # This can be processed on any node
        found, user_id = self.raft_node.get_user_by_username(username)
        
        if found:
            return exp_pb2.GetUserByUsernameResponse(
                status=exp_pb2.FOUND,
                user_id=user_id
            )
        else:
            return exp_pb2.GetUserByUsernameResponse(
                status=exp_pb2.NOT_FOUND,
                user_id=0
            )


def serve(node_id, cluster_config, data_dir, port=50051):
    """
    Start the gRPC server with both messaging and Raft services.
    
    Args:
        node_id: ID of this node in the cluster
        cluster_config: Dict mapping node_ids to addresses
        data_dir: Directory for persistent storage
        port: Port to listen on
    """
    # Initialize the Raft node
    raft_node = RaftNode(node_id, cluster_config, data_dir)
    
    # Create the gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    print(f"[DEBUG] Registering services for node {node_id}")
    print(f"[DEBUG] RaftNode inherits from: {RaftNode.__mro__}")
    print(f"[DEBUG] RaftNode implements RequestVote: {'RequestVote' in dir(raft_node)}")
    print(f"[DEBUG] RaftNode implements AppendEntries: {'AppendEntries' in dir(raft_node)}")
    
    # Add the messaging service
    messaging_servicer = RaftMessagingServicer(raft_node)
    exp_pb2_grpc.add_MessagingServiceServicer_to_server(messaging_servicer, server)
    
    # Add the Raft service
    # RaftService.add_to_server(raft_node, server)
    raft_servicer = RaftServiceServicer(raft_node)
    exp_pb2_grpc.add_RaftServiceServicer_to_server(raft_servicer, server)  
    
    # Start the server
    # server_address = f"[::]:{port}"
    server_address = f"0.0.0.0:{port}"
    server.add_insecure_port(server_address)
    server.start()
    
    logger.info(f"Server started as node {node_id} listening on {server_address}")
    logger.info(f"Cluster configuration: {cluster_config}")
    
    try:
        # Keep the server running
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        raft_node.stop()
        server.stop(0)
    
    logger.info("Server shutdown complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a Raft-based messaging server")
    parser.add_argument("--node-id", required=True, help="ID of this node")
    parser.add_argument("--config", required=True, help="Path to cluster configuration file")
    parser.add_argument("--data-dir", required=True, help="Directory for data storage")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on")
    
    args = parser.parse_args()
    
    # Load cluster configuration
    with open(args.config, 'r') as f:
        cluster_config = json.load(f)
    
    # Start the server
    serve(args.node_id, cluster_config, args.data_dir, args.port)
