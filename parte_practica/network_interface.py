import json
import socket
import subprocess
import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

from game import Game, Player, Team

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.environ.get("PYTHON_NETWORK_LOG_FILE", 'network.log')
)
logger = logging.getLogger('network_interface')


class NetworkInterface:
    """Interface for communication with the Elixir P2P network application."""

    def __init__(self, host: str = None, port: int = None, elixir_path: str = None):
        """Initialize the network interface with the discovery server address."""
        self.discovery_host = host if host is not None else os.environ.get("GAME_DISCOVERY_HOST", 'localhost')
        self.discovery_port = port if port is not None else int(os.environ.get("GAME_DISCOVERY_PORT", "80"))
        self.game_client = None
        self.game_ports = {}  # game_id: port
        self.socket = None
        self.elixir_path = elixir_path if elixir_path is not None else os.environ.get("ELIXIR_PATH")
        self.elixir_proc = None
        self.connected = False

    def set_game_client(self, client):
        """Set the game client for this interface."""
        self.game_client = client

    def start_elixir_node(self) -> bool:
        """Start the Elixir node if path is provided."""
        if not self.elixir_path:
            logger.warning("No Elixir path provided, skipping Elixir node startup")
            return False
        
        try:
            # Start the Elixir node as a subprocess
            logger.info(f"Starting Elixir node at {self.elixir_path}")
            self.elixir_proc = subprocess.Popen(
                ["elixir", "--sname", "python_client", "-S", "mix", "run", "--no-halt"],
                cwd=self.elixir_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the Elixir node to start
            time.sleep(2)
            
            if self.elixir_proc.poll() is None:
                logger.info("Elixir node started successfully")
                return True
            else:
                stdout, stderr = self.elixir_proc.communicate(timeout=1)
                logger.error(f"Failed to start Elixir node: {stderr}")
                self.elixir_proc = None
                return False
        except Exception as e:
            logger.error(f"Error starting Elixir node: {e}")
            if self.elixir_proc:
                self.elixir_proc.terminate()
                self.elixir_proc = None
            return False

    def stop_elixir_node(self):
        """Stop the Elixir node if it's running."""
        if self.elixir_proc:
            try:
                self.elixir_proc.terminate()
                self.elixir_proc.wait(timeout=5)
                logger.info("Elixir node stopped")
            except Exception as e:
                logger.error(f"Error stopping Elixir node: {e}")
                try:
                    self.elixir_proc.kill()
                except:
                    pass
            self.elixir_proc = None

    def connect_to_discovery(self) -> bool:
        """Connect to the discovery server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.discovery_host, self.discovery_port))
            self.connected = True
            logger.info(f"Connected to discovery server at {self.discovery_host}:{self.discovery_port}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to discovery server: {e}")
            return False

    def disconnect_from_discovery(self):
        """Disconnect from the discovery server."""
        if self.socket:
            try:
                self.socket.close()
                logger.info("Disconnected from discovery server")
            except Exception as e:
                logger.error(f"Error disconnecting from discovery server: {e}")
            self.socket = None
            self.connected = False

    def send_message(self, message: Dict) -> Optional[Dict]:
        """Send a message to the server and get the response."""
        if not self.socket and not self.connect_to_discovery():
            logger.error("Failed to connect to discovery server")
            return None
            
        # Add protocol version and timestamp for the Elixir server
        message['protocol_version'] = '1.0'
        message['timestamp'] = int(time.time())

        try:
            # Convert message to JSON and add newline as message delimiter for Elixir
            message_bytes = (json.dumps(message) + "\n").encode('utf-8')
            
            # Send the message
            logger.debug(f"Sending message: {message}")
            self.socket.sendall(message_bytes)
            
            # Receive the response
            buffer = b''
            while True:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            # Parse the response
            response_str = buffer.decode('utf-8').strip()
            try:
                response = json.loads(response_str)
                logger.debug(f"Received response: {response}")
                return response
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response: {e}, response: {response_str}")
                return None
        except Exception as e:
            logger.error(f"Error communicating with server: {e}")
            self.disconnect_from_discovery()
            return None

    def create_game(self, game: Game) -> bool:
        """Send a message to create a new game."""
        message = {
            'action': 'create_game',
            'game_data': game.get_game_state(),
            'creator_id': game.creator_id
        }
        
        response = self.send_message(message)
        if response and response.get('status') == 'success':
            if 'port' in response:
                self.game_ports[game.game_id] = response['port']
            return True
        return False

    def get_available_games(self) -> List[str]:
        """Get a list of available games from the discovery server."""
        # Always disconnect first to ensure a fresh connection
        self.disconnect_from_discovery()
        
        # Reconnect to get fresh data
        if not self.connect_to_discovery():
            logger.error("Failed to connect to discovery server")
            return []
            
        message = {
            'action': 'list_games'
        }
        
        response = self.send_message(message)
        if response and response.get('status') == 'success':
            games = response.get('games', [])
            logger.info(f"Found {len(games)} available games")
            # Update the game ports
            for game in games:
                if 'game_id' in game and 'port' in game:
                    self.game_ports[game['game_id']] = game['port']
                    logger.info(f"Updated port for game {game['game_id']}: {game['port']}")
            
            # Format the games for display
            formatted_games = []
            for game in games:
                formatted = f"{game.get('game_id')} | {game.get('creator_name', 'Unknown')} | {game.get('state', 'unknown')}"
                formatted_games.append(formatted)
            
            return formatted_games
        return []

    def join_game(self, game_id: str, player_id: str, player_name: str) -> Optional[Game]:
        """Join a game with the given ID."""
        # First check if we have the port for this game
        if game_id not in self.game_ports:
            message = {
                'action': 'get_game_port',
                'game_id': game_id
            }
            
            response = self.send_message(message)
            if response and response.get('status') == 'success' and 'port' in response:
                self.game_ports[game_id] = response['port']
            else:
                return None
        
        # Now connect to the game master directly
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            # Send join message
            join_message = {
                'action': 'join_game',
                'game_id': game_id,
                'player_id': player_id,
                'player_name': player_name
            }
            
            game_socket.sendall(json.dumps(join_message).encode('utf-8'))
            
            # Receive the game state
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            if response and response.get('status') == 'success' and 'game_state' in response:
                # Create a Game object from the received state
                game_state = response['game_state']
                game = Game(
                    creator_id=game_state['creator_id'],
                    max_teams=game_state['max_teams'],
                    max_players_per_team=game_state['max_players_per_team'],
                    board_size=game_state['board_size'],
                    dice_min=game_state['dice_min'],
                    dice_max=game_state['dice_max'],
                    game_id=game_state['game_id']
                )
                
                # Set the game state
                game.started = game_state['started']
                game.turn_order = game_state['turn_order']
                game.current_team_index = game_state.get('current_team_index', 0)
                game.winner = game_state.get('winner')
                game.state = game_state.get('state', 'en espera')
                
                # Add players
                for player_data in game_state.get('players', []):
                    player = Player(player_data['name'])
                    player.id = player_data['id']
                    game.players[player.id] = player
                
                # Add teams
                for team_data in game_state.get('teams', {}).values():
                    team = Team(team_data['name'])
                    team.position = team_data['position']
                    
                    # Add players to team
                    for player_id in team_data.get('player_ids', []):
                        if player_id in game.players:
                            team.add_player(game.players[player_id])
                    
                    game.teams[team.name] = team
                
                return game
        except Exception as e:
            print(f"Error joining game: {e}")
        
        return None

    def create_team(self, game_id: str, team_name: str) -> bool:
        """Send a message to create a new team."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'create_team',
                'game_id': game_id,
                'team_name': team_name
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            return response and response.get('status') == 'success'
        except Exception as e:
            print(f"Error creating team: {e}")
        
        return False

    def join_team(self, game_id: str, team_name: str, player_id: str) -> bool:
        """Send a message to join a team or send join request."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'join_team',
                'game_id': game_id,
                'team_name': team_name,
                'player_id': player_id
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            return response and response.get('status') == 'success'
        except Exception as e:
            print(f"Error joining team: {e}")
        
        return False

    def vote_for_join(self, game_id: str, voter_id: str, player_id: str, team_name: str, vote: bool) -> bool:
        """Send a vote for a join request."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'vote',
                'game_id': game_id,
                'voter_id': voter_id,
                'player_id': player_id,
                'team_name': team_name,
                'vote': vote
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            return response and response.get('status') == 'success'
        except Exception as e:
            print(f"Error voting: {e}")
        
        return False

    def start_game(self, game_id: str) -> bool:
        """Send a request to start the game."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'start_game',
                'game_id': game_id
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            return response and response.get('status') == 'success'
        except Exception as e:
            print(f"Error starting game: {e}")
        
        return False

    def roll_dice(self, game_id: str, team_name: str, dice_roll: int, new_position: int) -> bool:
        """Send a dice roll update."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'roll_dice',
                'game_id': game_id,
                'team_name': team_name,
                'dice_roll': dice_roll,
                'new_position': new_position
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            return response and response.get('status') == 'success'
        except Exception as e:
            print(f"Error rolling dice: {e}")
        
        return False

    def leave_game(self, game_id: str, player_id: str) -> bool:
        """Send a request to leave the game."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'leave_game',
                'game_id': game_id,
                'player_id': player_id
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            if response and response.get('status') == 'success':
                if game_id in self.game_ports:
                    del self.game_ports[game_id]
                return True
        except Exception as e:
            print(f"Error leaving game: {e}")
        
        return False

    def delete_game(self, game_id: str) -> bool:
        """Send a request to delete the game (only for creator)."""
        if game_id not in self.game_ports:
            return False
        
        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'delete_game',
                'game_id': game_id
            }
            
            game_socket.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive the response
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer:
                    break
            
            response = json.loads(buffer.decode('utf-8'))
            game_socket.close()
            
            if response and response.get('status') == 'success':
                if game_id in self.game_ports:
                    del self.game_ports[game_id]
                return True
        except Exception as e:
            print(f"Error deleting game: {e}")
        
        return False

    def get_game_logs(self, game_id: str) -> Optional[List[str]]:
        """Retrieve game logs from the Elixir application."""
        if game_id not in self.game_ports:
            logger.error(f"Cannot get logs: Game ID {game_id} not found in game_ports.")
            # Attempt to get the port from discovery if not found
            message = {
                'action': 'get_game_port',
                'game_id': game_id
            }
            response = self.send_message(message) # Assumes send_message connects to discovery
            if response and response.get('status') == 'success' and 'port' in response:
                self.game_ports[game_id] = response['port']
                logger.info(f"Retrieved port {response['port']} for game {game_id} from discovery.")
            else:
                logger.error(f"Failed to retrieve port for game {game_id} from discovery.")
                return None

        if game_id not in self.game_ports: # Check again after attempting to retrieve port
             logger.error(f"Still cannot get logs: Game ID {game_id} port unknown.")
             return None

        try:
            game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to the specific game port
            game_socket.connect((self.discovery_host, self.game_ports[game_id]))
            
            message = {
                'action': 'get_game_logs',
                'game_id': game_id
            }
            
            # Send message and get response (similar to other methods)
            game_socket.sendall((json.dumps(message) + "\n").encode('utf-8'))
            
            buffer = b''
            while True:
                data = game_socket.recv(4096)
                if not data:
                    break
                buffer += data
                if b'\n' in buffer: # Assuming logs are sent as a JSON list with a newline
                    break
            
            game_socket.close()

            if buffer:
                response_str = buffer.decode('utf-8').strip()
                try:
                    response = json.loads(response_str)
                    if response and response.get('status') == 'success' and 'logs' in response:
                        logger.info(f"Successfully retrieved logs for game {game_id}")
                        return response.get('logs')
                    else:
                        logger.error(f"Failed to get logs from game {game_id}: {response.get('message', 'No specific error message.')}")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding logs response: {e}, response: {response_str}")
                    return None
            else:
                logger.warning(f"No response received when fetching logs for game {game_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting game logs for {game_id}: {e}")
            return None

    def handle_incoming_messages(self, game_client):
        """
        This method would be called by the P2P application to handle incoming messages
        and update the game client accordingly.
        """
        # This is a placeholder for the P2P application to implement
        pass
        
    def register_callbacks(self):
        """Register callback handlers for Elixir events."""
        if not self.connected:
            if not self.connect_to_discovery():
                logger.error("Failed to connect to register callbacks")
                return False
        
        message = {
            'action': 'register_callbacks',
            'callbacks': {
                'game_update': True,
                'player_join': True,
                'team_update': True,
                'game_start': True,
                'game_end': True,
                'dice_roll': True
            }
        }
        
        response = self.send_message(message)
        return response and response.get('status') == 'success'
    
    def process_elixir_message(self, message: Dict):
        """Process an incoming message from the Elixir application."""
        if not message or 'action' not in message:
            logger.warning(f"Received invalid message: {message}")
            return
            
        action = message.get('action')
        logger.info(f"Processing message with action: {action}")
        
        if action == 'game_update' and self.game_client and self.game_client.current_game:
            # Update the game state
            if 'game_state' in message:
                self._update_game_state(message['game_state'])
                
        elif action == 'player_join' and self.game_client and self.game_client.current_game:
            # New player joined
            player_id = message.get('player_id')
            player_name = message.get('player_name')
            if player_id and player_name:
                player = Player(player_name)
                player.id = player_id
                self.game_client.current_game.players[player_id] = player
                
        elif action == 'team_update' and self.game_client and self.game_client.current_game:
            # Team was updated
            team_name = message.get('team_name')
            if team_name and team_name in self.game_client.current_game.teams:
                team_data = message.get('team_data', {})
                team = self.game_client.current_game.teams[team_name]
                if 'position' in team_data:
                    team.position = team_data['position']
                
        elif action == 'game_start' and self.game_client and self.game_client.current_game:
            # Game started
            self.game_client.current_game.started = True
            self.game_client.current_game.state = "en juego"
            if 'turn_order' in message:
                self.game_client.current_game.turn_order = message['turn_order']
                
        elif action == 'game_end' and self.game_client and self.game_client.current_game:
            # Game ended
            winner = message.get('winner')
            if winner:
                self.game_client.current_game.winner = winner
                
        elif action == 'dice_roll' and self.game_client and self.game_client.current_game:
            # Dice was rolled
            team_name = message.get('team_name')
            dice_roll = message.get('dice_roll')
            new_position = message.get('new_position')
            if team_name and team_name in self.game_client.current_game.teams and dice_roll is not None:
                team = self.game_client.current_game.teams[team_name]
                team.position = new_position
                
                # Move to next team
                if 'next_team' in message:
                    next_team = message['next_team']
                    for i, team_name in enumerate(self.game_client.current_game.turn_order):
                        if team_name == next_team:
                            self.game_client.current_game.current_team_index = i
                            break
                else:
                    # If next_team not provided, just advance to the next team
                    self.game_client.current_game.current_team_index = (
                        self.game_client.current_game.current_team_index + 1
                    ) % len(self.game_client.current_game.turn_order)
    
    def _update_game_state(self, game_state: Dict):
        """Update the game state from an Elixir message."""
        if not self.game_client or not self.game_client.current_game:
            return
            
        game = self.game_client.current_game
        
        # Update game properties
        if 'started' in game_state:
            game.started = game_state['started']
        if 'state' in game_state:
            game.state = game_state['state']
        if 'winner' in game_state:
            game.winner = game_state['winner']
        if 'turn_order' in game_state:
            game.turn_order = game_state['turn_order']
        if 'current_team_index' in game_state:
            game.current_team_index = game_state['current_team_index']
            
        # Update teams
        if 'teams' in game_state:
            for team_name, team_data in game_state['teams'].items():
                if team_name not in game.teams:
                    game.teams[team_name] = Team(team_name)
                    
                team = game.teams[team_name]
                if 'position' in team_data:
                    team.position = team_data['position']
                    
                # Update players in team
                if 'players' in team_data:
                    for player_data in team_data['players']:
                        player_id = player_data.get('id')
                        if player_id and player_id not in game.players:
                            player = Player(player_data.get('name', 'Unknown'))
                            player.id = player_id
                            game.players[player_id] = player
                            
                        if player_id and player_id in game.players:
                            player = game.players[player_id]
                            if player not in team.players:
                                team.add_player(player)
