import sys
import os
import argparse
import logging
import time
import threading
import socket
import json
from game import GameClient
from network_interface import NetworkInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='connector.log'
)
logger = logging.getLogger('connector')

# Global variable for the message listener thread
message_listener = None

def listen_for_messages(interface, client):
    """Listen for messages from the Elixir application."""
    logger.info("Starting message listener thread")
    sock = None
    try:
        # Create a socket for receiving messages from Elixir
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('localhost', 4040))  # Use a dedicated port for callbacks
        sock.listen(5)
        
        logger.info("Listening for Elixir messages on port 4040")
        
        # Register our callback socket with the Elixir application
        register_message = {
            'action': 'register_callback_socket',
            'port': 4040
        }
        interface.send_message(register_message)
        
        while True:
            client_socket, addr = sock.accept()
            logger.info(f"Accepted connection from {addr}")
            
            # Handle the message
            buffer = b''
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            if buffer:
                try:
                    message = json.loads(buffer.decode('utf-8').strip())
                    logger.debug(f"Received message: {message}")
                    interface.process_elixir_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding message: {e}, message: {buffer}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
            
            client_socket.close()
            
    except Exception as e:
        logger.error(f"Error in message listener: {e}")
    finally:
        if sock:
            sock.close()
        logger.info("Message listener thread stopped")

def main():
    """Main function to run the game with network capabilities."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Board Game Connector')
    parser.add_argument('--host', default='localhost', help='Hostname of the discovery server')
    parser.add_argument('--port', type=int, default=80, help='Port of the discovery server')
    parser.add_argument('--elixir-path', help='Path to the Elixir application')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    logger.info(f"Starting connector with host={args.host}, port={args.port}, elixir_path={args.elixir_path}")
    
    # Create the network interface
    interface = NetworkInterface(host=args.host, port=args.port, elixir_path=args.elixir_path)
    
    # Start the Elixir node if path is provided
    if args.elixir_path:
        if interface.start_elixir_node():
            logger.info("Elixir node started successfully")
        else:
            logger.warning("Failed to start Elixir node")
    
    # Create the game client
    client = GameClient()
    
    # Connect them to each other
    client.set_network_interface(interface)
    interface.set_game_client(client)
    
    # Start the message listener thread
    global message_listener
    message_listener = threading.Thread(
        target=listen_for_messages,
        args=(interface, client),
        daemon=True
    )
    message_listener.start()
    
    try:
        # Now run the game client's main function
        from game import main as game_main
        game_main(client)
    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
    except Exception as e:
        logger.error(f"Error running game: {e}", exc_info=True)
    finally:
        # Clean up
        logger.info("Cleaning up resources")
        interface.disconnect_from_discovery()
        interface.stop_elixir_node()

if __name__ == "__main__":
    main()
