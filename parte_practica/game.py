import json
import os
import random
import socket
import sys
import uuid
from typing import Dict, List, Optional, Tuple, Union


class Player:
    """Class representing a player in the game."""

    def __init__(self, name: str):
        """Initialize a new player with a name and a unique ID."""
        self.name = name
        self.id = str(uuid.uuid4())
        self.team_name = None

    def to_dict(self) -> Dict:
        """Convert player to a dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "team_name": self.team_name
        }

    def __str__(self) -> str:
        """Return string representation of the player."""
        return f"{self.name} (ID: {self.id[:8]}{'...' if len(self.id) > 8 else ''})"
        self.team = None

    def to_dict(self) -> Dict:
        """Convert player to a dictionary for serialization."""
        return {
            "name": self.name,
            "id": self.id,
            "team_name": self.team.name if self.team else None
        }

    def __str__(self) -> str:
        """Return string representation of the player."""
        return f"{self.name} (ID: {self.id})"


class Team:
    """Class representing a team in the game."""

    def __init__(self, name: str):
        """Initialize a new team with a name and an empty list of players."""
        self.name = name
        self.players: List[Player] = []
        self.position = 0
        self.join_requests: Dict[str, List[str]] = {}  # player_id: [votes]

    def add_player(self, player: Player) -> bool:
        """Add a player to the team."""
        if player.team:
            return False
        self.players.append(player)
        player.team = self
        return True

    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the team."""
        for i, player in enumerate(self.players):
            if player.id == player_id:
                player.team = None
                self.players.pop(i)
                return True
        return False

    def roll_dice(self, dice_min: int, dice_max: int) -> int:
        """Roll dice for all players in the team and return the total."""
        if not self.players:
            return 0
        
        total = 0
        for player in self.players:
            roll = random.randint(dice_min, dice_max)
            total += roll
        
        return total

    def advance(self, steps: int) -> None:
        """Advance the team's position by the given number of steps."""
        self.position += steps

    def send_join_request(self, player_id: str) -> None:
        """Send a join request for a player to the team."""
        self.join_requests[player_id] = []

    def vote_for_join_request(self, voter_id: str, player_id: str, vote: bool) -> None:
        """Vote for a join request."""
        if player_id not in self.join_requests:
            return
        
        # Check if the voter is in the team
        voter_in_team = False
        for player in self.players:
            if player.id == voter_id:
                voter_in_team = True
                break
        
        if not voter_in_team:
            return
        
        if vote:
            self.join_requests[player_id].append(voter_id)

    def count_votes(self, player_id: str) -> Tuple[int, int]:
        """Count votes for a join request."""
        if player_id not in self.join_requests:
            return 0, 0
        
        yes_votes = len(self.join_requests[player_id])
        total_voters = len(self.players)
        
        return yes_votes, total_voters

    def to_dict(self) -> Dict:
        """Convert team to a dictionary for serialization."""
        return {
            "name": self.name,
            "position": self.position,
            "players": [player.to_dict() for player in self.players[:5]],  # First 5 players
            "total_players": len(self.players),
            "join_requests": list(self.join_requests.keys())
        }

    def __str__(self) -> str:
        """Return string representation of the team."""
        player_str = ", ".join(player.name for player in self.players[:5])
        if len(self.players) > 5:
            player_str += f" and {len(self.players) - 5} more"
        return f"Team {self.name} - Position: {self.position} - Players: {player_str if self.players else 'None'}"


class Game:
    """Class representing a game."""

    def __init__(self, creator_id: str, max_teams: int, max_players_per_team: int, 
                 board_size: int, dice_min: int, dice_max: int, game_id: str = None):
        """Initialize a new game with the given parameters."""
        self.creator_id = creator_id
        self.max_teams = max(2, min(max_teams, 50))  # Between 2 and 50
        self.max_players_per_team = max(1, min(max_players_per_team, 50))  # Between 1 and 50
        self.board_size = max(10, min(board_size, 1_000_000))  # Between 10 and 1,000,000
        self.dice_min = max(1, min(dice_min, self.board_size))  # At least 1, at most board_size
        self.dice_max = max(self.dice_min, min(dice_max, self.board_size))  # At least dice_min, at most board_size
        self.game_id = game_id if game_id else str(uuid.uuid4())
        self.teams: Dict[str, Team] = {}
        self.players: Dict[str, Player] = {}
        self.started = False
        self.current_team_index = 0
        self.turn_order: List[str] = []  # List of team names in order of play
        self.winner = None
        self.state = "en espera"  # "en espera" or "en juego"

    def add_player(self, name: str) -> str:
        """Add a new player to the game."""
        player = Player(name)
        self.players[player.id] = player
        return player.id

    def create_team(self, name: str) -> bool:
        """Create a new team with the given name."""
        if self.started or len(self.teams) >= self.max_teams or name in self.teams:
            return False
        
        self.teams[name] = Team(name)
        return True

    def player_join_team(self, player_id: str, team_name: str) -> bool:
        """Add a player to a team immediately (if team is empty) or send join request."""
        if player_id not in self.players or team_name not in self.teams:
            return False
        
        team = self.teams[team_name]
        player = self.players[player_id]
        
        # If the team is empty, join directly
        if not team.players:
            return team.add_player(player)
        
        # If team has space, send join request
        if len(team.players) < self.max_players_per_team:
            team.send_join_request(player_id)
            return True
        
        return False

    def vote_for_team_join(self, voter_id: str, player_id: str, team_name: str, vote: bool) -> bool:
        """Vote for a player join request."""
        if team_name not in self.teams or voter_id not in self.players or player_id not in self.players:
            return False
        
        team = self.teams[team_name]
        team.vote_for_join_request(voter_id, player_id, vote)
        
        # Check if majority of votes received
        yes_votes, total_voters = team.count_votes(player_id)
        if yes_votes > total_voters / 2:  # Majority approved
            player = self.players[player_id]
            result = team.add_player(player)
            if result:
                # Remove the join request
                del team.join_requests[player_id]
            return result
        
        return False

    def start_game(self) -> bool:
        """Start the game if at least 2 teams have players."""
        if self.started:
            return False
        
        # Count teams with at least one player
        teams_with_players = 0
        valid_teams = []
        for team_name, team in self.teams.items():
            if team.players:
                teams_with_players += 1
                valid_teams.append(team_name)
        
        if teams_with_players < 2:
            return False
        
        # Remove empty teams
        teams_to_remove = []
        for team_name, team in self.teams.items():
            if not team.players:
                teams_to_remove.append(team_name)
        
        for team_name in teams_to_remove:
            del self.teams[team_name]
        
        # Set turn order randomly
        self.turn_order = list(self.teams.keys())
        random.shuffle(self.turn_order)
        self.current_team_index = 0
        
        self.started = True
        self.state = "en juego"
        return True

    def get_current_team(self) -> Optional[Team]:
        """Get the team whose turn it is."""
        if not self.started or not self.turn_order:
            return None
        
        return self.teams[self.turn_order[self.current_team_index]]

    def next_turn(self) -> Tuple[str, int, int]:
        """Move to the next turn and return (team_name, dice_roll, new_position)."""
        if not self.started or self.winner:
            return None, 0, 0
        
        current_team = self.get_current_team()
        dice_roll = current_team.roll_dice(self.dice_min, self.dice_max)
        current_team.advance(dice_roll)
        
        # Check for winner
        if current_team.position >= self.board_size:
            self.winner = current_team.name
        
        # Move to next team
        self.current_team_index = (self.current_team_index + 1) % len(self.turn_order)
        
        return current_team.name, dice_roll, current_team.position

    def get_game_state(self) -> Dict:
        """Get the current state of the game."""
        team_states = {name: team.to_dict() for name, team in self.teams.items()}
        
        return {
            "game_id": self.game_id,
            "creator_id": self.creator_id,
            "max_teams": self.max_teams,
            "max_players_per_team": self.max_players_per_team,
            "board_size": self.board_size,
            "dice_min": self.dice_min,
            "dice_max": self.dice_max,
            "started": self.started,
            "state": self.state,
            "current_team": self.turn_order[self.current_team_index] if self.started and self.turn_order else None,
            "turn_order": self.turn_order,
            "teams": team_states,
            "winner": self.winner
        }

    def to_list_format(self, creator_name: str) -> str:
        """Format game information for listing in the main menu."""
        return f"{self.game_id} | {creator_name} | {self.state}"


class GameClient:
    """Client for the game, handles user interface and communicates with network."""

    def __init__(self):
        """Initialize a new game client."""
        self.player_id = None
        self.player_name = None
        self.current_game: Optional[Game] = None
        self.network_interface = None  # This will be set by the network application

    def set_network_interface(self, interface):
        """Set the network interface for communication."""
        self.network_interface = interface

    def create_player(self, name: str) -> str:
        """Create a new player with the given name."""
        self.player_name = name
        self.player_id = str(uuid.uuid4())
        return self.player_id

    def create_game(self, max_teams: int, max_players_per_team: int, 
                   board_size: int, dice_min: int, dice_max: int) -> Game:
        """Create a new game with the given parameters."""
        if not self.player_id:
            print("Error: Player not created yet.")
            return None
        
        game = Game(
            creator_id=self.player_id, 
            max_teams=max_teams, 
            max_players_per_team=max_players_per_team, 
            board_size=board_size, 
            dice_min=dice_min, 
            dice_max=dice_max
        )
        
        # Add creator to the game's player list
        game.players[self.player_id] = Player(self.player_name)
        game.players[self.player_id].id = self.player_id
        
        self.current_game = game
        
        # If network interface is available, send game creation message
        if self.network_interface:
            self.network_interface.create_game(game)
        
        return game

    def join_game(self, game_id: str) -> bool:
        """Join a game with the given ID."""
        if not self.player_id:
            print("Error: Player not created yet.")
            return False
        
        # If network interface is available, send join game message
        if self.network_interface:
            game = self.network_interface.join_game(game_id, self.player_id, self.player_name)
            if game:
                self.current_game = game
                return True
        
        return False

    def create_team(self, team_name: str) -> bool:
        """Create a new team in the current game. Player automatically joins the team."""
        if not self.current_game or self.current_game.started:
            # print("Cannot create team: No current game or game already started.") # Optional: for debugging
            return False
        
        # 1. Attempt to create the team locally
        if not self.current_game.create_team(team_name):
            # print(f"Failed to create team '{team_name}' locally.") # Optional: for debugging
            return False
        
        # If a network interface is present, try to create and join over the network
        if self.network_interface:
            # 2. Attempt to create the team on the network
            if self.network_interface.create_team(self.current_game.game_id, team_name):
                # 3. If network creation successful, attempt to join the team via network
                if self.join_team(team_name): # join_team handles network call
                    # print(f"Team '{team_name}' created and joined successfully (networked).") # Optional
                    return True
                else:
                    # print(f"Team '{team_name}' created on network, but failed to join.") # Optional
                    # TODO: Consider reverting network team creation if join fails.
                    # For now, consider it a failure of the "create and join" operation.
                    # Also, the local game state has the team, but the player isn't in it.
                    # And the network state has the team, but player isn't in it.
                    self.current_game.remove_team_if_empty(team_name) # Attempt to clean up local team
                    return False 
            else:
                # print(f"Failed to create team '{team_name}' on the network.") # Optional
                # The team was created locally but not on the network.
                # Revert the local creation.
                self.current_game.remove_team_if_empty(team_name)
                return False
        else:
            # No network interface: local operations only
            # Team is already created locally (step 1). Now, join it locally.
            if self.join_team(team_name): # This will call local join
                # print(f"Team '{team_name}' created and joined successfully (local mode).") # Optional
                return True
            else:
                # print(f"Team '{team_name}' created locally, but failed to join locally.") # Optional
                self.current_game.remove_team_if_empty(team_name) # Attempt to clean up local team
                return False

    def join_team(self, team_name: str) -> bool:
        """Join a team in the current game."""
        if not self.current_game:
            return False
        
        result = self.current_game.player_join_team(self.player_id, team_name)
        
        # If network interface is available, send join team message
        if result and self.network_interface:
            self.network_interface.join_team(self.current_game.game_id, team_name, self.player_id)
        
        return result

    def vote_for_join(self, player_id: str, team_name: str, vote: bool) -> bool:
        """Vote for a player join request."""
        if not self.current_game:
            return False
        
        result = self.current_game.vote_for_team_join(self.player_id, player_id, team_name, vote)
        
        # If network interface is available, send vote message
        if self.network_interface:
            self.network_interface.vote_for_join(
                self.current_game.game_id, self.player_id, player_id, team_name, vote
            )
        
        return result

    def start_game(self) -> bool:
        """Request to start the game."""
        if not self.current_game or self.current_game.started:
            return False
        
        # Only creator can start the game
        if self.current_game.creator_id != self.player_id:
            return False
        
        result = self.current_game.start_game()
        
        # If network interface is available, send start game message
        if result and self.network_interface:
            self.network_interface.start_game(self.current_game.game_id)
        
        return result

    def roll_dice(self) -> Tuple[str, int, int]:
        """Roll dice for the current team if it's their turn."""
        if not self.current_game or not self.current_game.started:
            return None, 0, 0
        
        # Check if it's the player's team's turn
        current_team = self.current_game.get_current_team()
        if not current_team:
            return None, 0, 0
        
        player_in_team = False
        for player in current_team.players:
            if player.id == self.player_id:
                player_in_team = True
                break
        
        if not player_in_team:
            return None, 0, 0
        
        result = self.current_game.next_turn()
        
        # If network interface is available, send roll dice message
        if self.network_interface:
            self.network_interface.roll_dice(self.current_game.game_id, result[0], result[1], result[2])
        
        return result

    def get_available_games(self) -> List[str]:
        """Get a list of available games."""
        if not self.network_interface:
            return []
        
        return self.network_interface.get_available_games()

    def get_game_state(self) -> Dict:
        """Get the current state of the game."""
        if not self.current_game:
            return {}
        
        return self.current_game.get_game_state()

    def leave_game(self) -> bool:
        """Leave the current game."""
        if not self.current_game:
            return False
        
        game_id = self.current_game.game_id
        
        # Find player's team
        player_team = None
        for team in self.current_game.teams.values():
            for player in team.players:
                if player.id == self.player_id:
                    player_team = team
                    break
            if player_team:
                break
        
        # Remove player from team
        if player_team:
            player_team.remove_player(self.player_id)
        
        # If player is creator and game hasn't started, delete the game
        is_creator = self.current_game.creator_id == self.player_id
        if is_creator and not self.current_game.started:
            # If network interface is available, send delete game message
            if self.network_interface:
                self.network_interface.delete_game(game_id)
        else:
            # If network interface is available, send leave game message
            if self.network_interface:
                self.network_interface.leave_game(game_id, self.player_id)
        
        self.current_game = None
        return True


def parse_command(command: str) -> Tuple[str, List[str]]:
    """Parse a command and its arguments."""
    parts = command.strip().split()
    if not parts:
        return "", []
    
    return parts[0].lower(), parts[1:]


def main(client=None):
    """Main function to run the game client."""
    if client is None:
        client = GameClient()
    print("¡Bienvenido al juego de equipos y dados!")
    
    # Get player name
    while True:
        name = input("Por favor ingresa tu nombre: ")
        if name.strip():
            client.create_player(name.strip())
            print(f"Bienvenido, {name}! Tu ID único es: {client.player_id}")
            break
        else:
            print("El nombre no puede estar vacío.")
    
    # Main menu loop
    while True:
        print("\n--- Menú Principal ---")
        print("1. Crear juego")
        print("2. Unirse a un juego")
        print("3. Salir del juego")
        choice = input("Elige una opción (1-3): ")
        
        if choice == "1":
            # Create game menu
            try:
                max_teams = int(input("Introduce la cantidad máxima de equipos (2-50): "))
                max_players = int(input("Introduce la cantidad máxima de jugadores por equipo (1-50): "))
                board_size = int(input("Introduce el tamaño del tablero (10-1000000): "))
                dice_min = int(input("Introduce el valor mínimo del dado (1): ") or "1")
                dice_max = int(input("Introduce el valor máximo del dado (1-{}): ".format(min(board_size, 1000000))))
                
                game = client.create_game(max_teams, max_players, board_size, dice_min, dice_max)
                if game:
                    print(f"¡Juego creado! ID: {game.game_id}")
                    handle_game_lobby(client)
                else:
                    print("Error al crear el juego.")
            except ValueError:
                print("Error: Debes introducir valores numéricos válidos.")
        
        elif choice == "2":
            # Join game menu
            games = client.get_available_games()
            
            if not games:
                print("No hay juegos disponibles actualmente.")
                continue
            
            print("\n--- Juegos Disponibles ---")
            for i, game_info in enumerate(games, 1):
                print(f"{i}. {game_info}")
            
            print("\nComandos disponibles:")
            print("  listar - Muestra nuevamente los juegos disponibles")
            print("  unirse [ID_juego] - Unirse a un juego específico")
            print("  volver - Regresar al menú principal")
            
            while True:
                action = input("Ingresa un comando: ")
                cmd, args = parse_command(action)
                
                if cmd == "listar":
                    games = client.get_available_games()
                    print("\n--- Juegos Disponibles ---")
                    for i, game_info in enumerate(games, 1):
                        print(f"{i}. {game_info}")
                
                elif cmd == "unirse" and args:
                    game_id = args[0]
                    if client.join_game(game_id):
                        print(f"Te has unido al juego {game_id}")
                        handle_game_lobby(client)
                        break
                    else:
                        print("Error al unirse al juego.")
                
                elif cmd == "volver":
                    break
                
                else:
                    print("Comando no reconocido.")
        
        elif choice == "3":
            print("¡Gracias por jugar! Hasta pronto.")
            break
        
        else:
            print("Opción no válida. Por favor elige una opción del 1 al 3.")


def handle_game_lobby(client: GameClient):
    """Handle the game lobby interface."""
    if not client.current_game:
        print("Error: No estás en ningún juego.")
        return
    
    print("\n--- Sala de Juego ---")
    print(f"ID de la Sala: {client.current_game.game_id}")
    print(f"Estado: {client.current_game.state}")
    
    is_creator = client.current_game.creator_id == client.player_id
    
    while True:
        print("\nComandos disponibles:")
        print("  estado - Muestra el estado actual del juego")
        print("  equipos - Muestra los equipos disponibles")
        print("  crear_equipo [nombre] - Crea un nuevo equipo")
        print("  unirse_equipo [nombre] - Envía solicitud para unirse a un equipo")
        if is_creator and not client.current_game.started:
            print("  iniciar - Inicia el juego (solo creador)")
        if client.current_game.started:
            print("  tirar - Tira el dado si es el turno de tu equipo")
            print("  logs - Muestra los logs del juego") # New command
        print("  salir - Volver al menú principal")
        
        action = input("Ingresa un comando: ")
        cmd, args = parse_command(action)
        
        if cmd == "estado":
            game_state = client.get_game_state()
            print("\n--- Estado del Juego ---")
            print(f"ID: {game_state['game_id']}")
            print(f"Estado: {game_state['state']}")
            if game_state['started']:
                print(f"Equipo actual: {game_state['current_team']}")
            print(f"Tamaño del tablero: {game_state['board_size']}")
            print("\nEquipos:")
            for team_name, team_data in game_state['teams'].items():
                print(f"  {team_name} - Posición: {team_data['position']} - Jugadores: {team_data['total_players']}")
            if game_state['winner']:
                print(f"\n¡El equipo {game_state['winner']} ha ganado!")
        
        elif cmd == "equipos":
            game_state = client.get_game_state()
            print("\n--- Equipos ---")
            for team_name, team_data in game_state['teams'].items():
                print(f"Equipo: {team_name} - Posición: {team_data['position']}")
                print("  Jugadores:")
                for player in team_data['players']:
                    print(f"    {player['name']} (ID: {player['id']})")
                if team_data['total_players'] > 5:
                    print(f"    ... y {team_data['total_players'] - 5} más")
                if team_data['join_requests']:
                    print("  Solicitudes de unión pendientes:")
                    for req_id in team_data['join_requests']:
                        for p_id, player in client.current_game.players.items():
                            if p_id == req_id:
                                print(f"    {player.name} (ID: {p_id})")
                                break
                print()
        
        elif cmd == "crear_equipo" and args:
            team_name = args[0]
            if not client.current_game.started:
                if client.create_team(team_name):
                    print(f"Equipo '{team_name}' creado exitosamente.")
                else:
                    print("Error al crear el equipo.")
            else:
                print("No se pueden crear equipos una vez iniciado el juego.")
        
        elif cmd == "unirse_equipo" and args:
            team_name = args[0]
            if team_name in client.current_game.teams:
                if client.join_team(team_name):
                    team = client.current_game.teams[team_name]
                    if team.players and len(team.players) == 1 and team.players[0].id == client.player_id:
                        print(f"Te has unido al equipo '{team_name}'.")
                    else:
                        print(f"Solicitud para unirse al equipo '{team_name}' enviada.")
                else:
                    print("Error al unirse al equipo.")
            else:
                print(f"El equipo '{team_name}' no existe.")
        
        elif cmd == "iniciar" and is_creator:
            if client.start_game():
                print("¡El juego ha comenzado!")
            else:
                print("No se puede iniciar el juego. Asegúrate de tener al menos 2 equipos con jugadores.")
        
        elif cmd == "tirar" and client.current_game.started:
            team_name, dice_roll, new_position = client.roll_dice()
            if team_name:
                print(f"El equipo {team_name} ha tirado los dados y obtenido {dice_roll}.")
                print(f"Nueva posición: {new_position}")
                if client.current_game.winner:
                    print(f"\n¡El equipo {client.current_game.winner} ha ganado!")
            else:
                print("No es el turno de tu equipo o no estás en un equipo.")
        
        elif cmd == "logs" and client.current_game.started:
            if client.network_interface:
                logs = client.network_interface.get_game_logs(client.current_game.game_id)
                if logs:
                    print("\n--- Logs del Juego ---")
                    for log_entry in logs:
                        print(log_entry)
                else:
                    print("No se pudieron obtener los logs del juego o no hay logs disponibles.")
            else:
                print("La interfaz de red no está disponible para obtener logs.")

        elif cmd == "votar" and len(args) >= 3:
            player_id = args[0]
            team_name = args[1]
            vote = args[2].lower() in ("si", "yes", "y", "1", "true")
            
            if client.vote_for_join(player_id, team_name, vote):
                print(f"Tu voto para {player_id} se ha registrado.")
            else:
                print("Error al votar.")
        
        elif cmd == "salir":
            if client.leave_game():
                print("Has salido del juego.")
                break
            else:
                print("Error al salir del juego.")
        
        else:
            print("Comando no reconocido.")


if __name__ == "__main__":
    main()
