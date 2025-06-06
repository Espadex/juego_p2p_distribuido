"""
Servidor del juego de carreras por equipos con logging RMI integrado
Maneja múltiples partidas y jugadores concurrentes
"""
import socket
import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import random
from simple_rmi_logger import (
    init_rmi_logging, cleanup_rmi_logging,
    log_game_start, log_game_end, log_player_create_start, log_player_create_end,
    log_dice_roll_start, log_dice_roll_end, log_team_create_start, log_team_create_end,
    log_team_join_start, log_team_join_end, log_game_win
)

class Team:
    def __init__(self, name: str, creator: str):
        self.name = name
        self.players = [creator]
        self.position = 0
        self.votes_to_start = set()
        
    def add_player(self, player: str):
        if player not in self.players:
            self.players.append(player)
    
    def remove_player(self, player: str):
        if player in self.players:
            self.players.remove(player)
            self.votes_to_start.discard(player)

class Game:
    def __init__(self, name: str, creator: str, max_teams: int, max_players_per_team: int, 
                 board_length: int, min_dice: int, max_dice: int):
        self.name = name
        self.creator = creator
        self.max_teams = max_teams
        self.max_players_per_team = max_players_per_team
        self.board_length = board_length
        self.min_dice = min_dice
        self.max_dice = max_dice
        self.teams: Dict[str, Team] = {}
        self.players = {creator}
        self.started = False
        self.finished = False
        self.winner = None
        self.current_turn = 0
        self.team_names = []
        self.pending_votes = {}  # Para votaciones de unión a equipos
        
    def add_player(self, player: str):
        self.players.add(player)
    
    def remove_player(self, player: str):
        self.players.discard(player)
        # Remover de equipos
        for team in self.teams.values():
            team.remove_player(player)
        # Limpiar equipos vacíos
        empty_teams = [name for name, team in self.teams.items() if not team.players]
        for team_name in empty_teams:
            del self.teams[team_name]
            if team_name in self.team_names:
                self.team_names.remove(team_name)
    
    def create_team(self, team_name: str, creator: str) -> bool:
        if len(self.teams) >= self.max_teams:
            return False
        if team_name in self.teams:
            return False
        if self.get_player_team(creator):
            return False
            
        team = Team(team_name, creator)
        self.teams[team_name] = team
        self.team_names.append(team_name)
        return True
    
    def get_player_team(self, player: str) -> Optional[str]:
        for team_name, team in self.teams.items():
            if player in team.players:
                return team_name
        return None
    
    def can_start(self) -> bool:
        if self.started or len(self.teams) == 0:
            return False
        
        # Todos los jugadores deben estar en equipos
        for player in self.players:
            if not self.get_player_team(player):
                return False
        
        # Todos los jugadores deben haber votado para empezar
        total_votes_needed = len(self.players)
        total_votes = sum(len(team.votes_to_start) for team in self.teams.values())
        
        return total_votes >= total_votes_needed
    
    def vote_to_start(self, player: str) -> bool:
        team_name = self.get_player_team(player)
        if team_name and team_name in self.teams:
            self.teams[team_name].votes_to_start.add(player)
            return True
        return False
    
    def start_game(self):
        if self.can_start():
            self.started = True
            return True
        return False

class GameServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.games: Dict[str, Game] = {}
        self.client_sockets = {}
        self.running = False
        
    def start(self):
        # Inicializar logging RMI
        init_rmi_logging()
        
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)
        
        print(f"🎮 Servidor del juego iniciado en {self.host}:{self.port}")
        print("📡 Sistema de logging RMI activado")
        
        try:
            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    print(f"🔌 Cliente conectado desde {address}")
                    thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    if self.running:
                        print(f"❌ Error aceptando conexión: {e}")
        except KeyboardInterrupt:
            print("\n🛑 Cerrando servidor...")
        finally:
            server_socket.close()
            cleanup_rmi_logging()
    
    def handle_client(self, client_socket):
        player_name = None
        current_game = None
        
        try:
            while True:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                try:
                    request = json.loads(data)
                    response = self.process_request(request, player_name, current_game)
                    
                    # Actualizar estado local
                    if 'player_name' in response:
                        player_name = response['player_name']
                        self.client_sockets[player_name] = client_socket
                    
                    if 'current_game' in response:
                        current_game = response['current_game']
                    
                    client_socket.send((json.dumps(response) + '\n').encode('utf-8'))
                    
                except json.JSONDecodeError:
                    error_response = {"status": "error", "message": "Formato JSON inválido"}
                    client_socket.send((json.dumps(error_response) + '\n').encode('utf-8'))
                    
        except Exception as e:
            print(f"❌ Error manejando cliente: {e}")
        finally:
            if player_name:
                # Limpiar jugador de partidas
                for game in self.games.values():
                    if player_name in game.players:
                        game.remove_player(player_name)
                
                if player_name in self.client_sockets:
                    del self.client_sockets[player_name]
            
            client_socket.close()
    
    def process_request(self, request, player_name, current_game):
        command = request.get('command')
        
        if command == 'set_player_name':
            name = request.get('name')
            return {"status": "ok", "player_name": name}
        
        elif command == 'create_game':
            return self.create_game(request, player_name)
        
        elif command == 'join_game':
            return self.join_game(request, player_name)
        
        elif command == 'list_games':
            return self.list_games()
        
        elif command == 'create_team':
            return self.create_team(request, player_name, current_game)
        
        elif command == 'join_team':
            return self.join_team(request, player_name, current_game)
        
        elif command == 'list_teams':
            return self.list_teams(current_game)
        
        elif command == 'game_status':
            return self.game_status(current_game)
        
        elif command == 'vote_start':
            return self.vote_start(player_name, current_game)
        
        elif command == 'roll_dice':
            return self.roll_dice(player_name, current_game)
        
        elif command == 'leave_game':
            return self.leave_game(player_name, current_game)
        
        elif command == 'vote_team_join':
            return self.vote_team_join(request, player_name, current_game)
        
        else:
            return {"status": "error", "message": "Comando no reconocido"}
    
    def create_game(self, request, player_name):
        game_name = request.get('game_name')
        max_teams = request.get('max_teams')
        max_players_per_team = request.get('max_players_per_team')
        board_length = request.get('board_length')
        min_dice = request.get('min_dice')
        max_dice = request.get('max_dice')
        
        # Log inicio de creación de juego
        log_game_start(game_name)
        
        if game_name in self.games:
            return {"status": "error", "message": "Ya existe una partida con ese nombre"}
        
        game = Game(game_name, player_name, max_teams, max_players_per_team, 
                   board_length, min_dice, max_dice)
        self.games[game_name] = game
        
        return {
            "status": "ok", 
            "message": f"Partida '{game_name}' creada exitosamente",
            "current_game": game_name
        }
    
    def join_game(self, request, player_name):
        game_name = request.get('game_name')
        
        if game_name not in self.games:
            return {"status": "error", "message": "La partida no existe"}
        
        game = self.games[game_name]
        if game.started:
            return {"status": "error", "message": "La partida ya ha comenzado"}
        
        # Log creación de jugador en la partida
        log_player_create_start(game_name, "sin_equipo", player_name)
        game.add_player(player_name)
        log_player_create_end(game_name, "sin_equipo", player_name)
        
        return {
            "status": "ok",
            "message": f"Te has unido a la partida '{game_name}'",
            "current_game": game_name
        }
    
    def list_games(self):
        games_info = []
        for name, game in self.games.items():
            games_info.append({
                "name": name,
                "creator": game.creator,
                "players": len(game.players),
                "teams": len(game.teams),
                "started": game.started,
                "finished": game.finished
            })
        
        return {"status": "ok", "games": games_info}
    
    def create_team(self, request, player_name, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        team_name = request.get('team_name')
        game = self.games[current_game]
        
        # Log inicio de creación de equipo
        log_team_create_start(current_game, team_name, player_name)
        
        if game.create_team(team_name, player_name):
            # Log fin de creación de equipo
            log_team_create_end(current_game, team_name, player_name)
            
            self.broadcast_to_game(current_game, {
                "type": "team_created",
                "team_name": team_name,
                "creator": player_name
            })
            return {"status": "ok", "message": f"Equipo '{team_name}' creado exitosamente"}
        else:
            return {"status": "error", "message": "No se pudo crear el equipo"}
    
    def join_team(self, request, player_name, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        team_name = request.get('team_name')
        game = self.games[current_game]
        
        if team_name not in game.teams:
            return {"status": "error", "message": "El equipo no existe"}
        
        team = game.teams[team_name]
        
        if len(team.players) >= game.max_players_per_team:
            return {"status": "error", "message": "El equipo está lleno"}
        
        if game.get_player_team(player_name):
            return {"status": "error", "message": "Ya estás en un equipo"}
        
        # Iniciar votación para unirse al equipo
        vote_id = player_name
        game.pending_votes[vote_id] = {
            "type": "join_team",
            "team_name": team_name,
            "player": player_name,
            "votes": {},
            "total_needed": len(team.players)
        }
        
        # Notificar a los miembros del equipo
        self.broadcast_to_team(current_game, team_name, {
            "type": "vote_request",
            "vote_id": vote_id,
            "message": f"{player_name} quiere unirse al equipo {team_name}. Vota 'si' o 'no'",
            "player_requesting": player_name
        })
        
        return {"status": "ok", "message": f"Solicitud enviada al equipo '{team_name}'. Esperando votación..."}
    
    def vote_team_join(self, request, player_name, current_game):
        vote_id = player_name
        vote = request.get('vote')  # 'si' o 'no'
        
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        game = self.games[current_game]
        
        if vote_id not in game.pending_votes:
            return {"status": "error", "message": "Votación no encontrada"}
        
        vote_data = game.pending_votes[vote_id]
        team_name = vote_data["team_name"]
        
        if team_name not in game.teams:
            return {"status": "error", "message": "El equipo ya no existe"}
        
        team = game.teams[team_name]
        
        if player_name not in team.players:
            return {"status": "error", "message": "No puedes votar en este equipo"}
        
        # Registrar voto
        vote_data["votes"][player_name] = vote
        
        # Verificar si todos han votado
        if len(vote_data["votes"]) >= vote_data["total_needed"]:
            # Contar votos
            yes_votes = sum(1 for v in vote_data["votes"].values() if v == 'si')
            no_votes = len(vote_data["votes"]) - yes_votes
            
            requesting_player = vote_data["player"]
            
            if yes_votes > no_votes:  # Mayoría gana
                # Log inicio de unión a equipo
                log_team_join_start(current_game, team_name, requesting_player)
                
                # Agregar al equipo
                team.add_player(requesting_player)
                
                # Log fin de unión a equipo
                log_team_join_end(current_game, team_name, requesting_player)
                
                # Notificar al solicitante
                if requesting_player in self.client_sockets:
                    self.send_to_player(requesting_player, {
                        "type": "team_join_result",
                        "status": "accepted",
                        "message": f"¡Has sido aceptado en el equipo '{team_name}'!"
                    })
                
                # Notificar al equipo
                self.broadcast_to_team(current_game, team_name, {
                    "type": "team_member_added",
                    "player": requesting_player,
                    "team_name": team_name
                })
            else:
                # Rechazado
                if requesting_player in self.client_sockets:
                    self.send_to_player(requesting_player, {
                        "type": "team_join_result",
                        "status": "rejected",
                        "message": f"Solicitud de unión al equipo '{team_name}' ¡RECHAZADA!"
                    })
            
            # Limpiar votación
            del game.pending_votes[vote_id]
            
            return {"status": "ok", "message": "Voto registrado. Votación completada."}
        else:
            return {"status": "ok", "message": "Voto registrado. Esperando más votos..."}
    
    def list_teams(self, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        game = self.games[current_game]
        teams_info = []
        
        for name, team in game.teams.items():
            teams_info.append({
                "name": name,
                "players": team.players,
                "position": team.position
            })
        
        return {"status": "ok", "teams": teams_info}
    
    def game_status(self, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        game = self.games[current_game]
        
        if not game.started:
            # Mostrar estado de votación para empezar
            total_players = len(game.players)
            votes_cast = sum(len(team.votes_to_start) for team in game.teams.values())
            
            return {
                "status": "ok",
                "game_status": "waiting",
                "message": f"Esperando inicio de partida",
                "votes_to_start": f"{votes_cast}/{total_players}",
                "can_start": game.can_start()
            }
        else:
            # Mostrar estado del tablero
            positions = []
            for name, team in game.teams.items():
                positions.append({
                    "team": name,
                    "position": team.position,
                    "players": team.players
                })
            
            current_team = game.team_names[game.current_turn] if game.team_names else None
            
            return {
                "status": "ok",
                "game_status": "playing" if not game.finished else "finished",
                "positions": positions,
                "current_turn": current_team,
                "board_length": game.board_length,
                "winner": game.winner
            }
    
    def vote_start(self, player_name, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        game = self.games[current_game]
        
        if game.started:
            return {"status": "error", "message": "La partida ya ha comenzado"}
        
        if game.vote_to_start(player_name):
            if game.can_start():
                game.start_game()
                self.broadcast_to_game(current_game, {
                    "type": "game_started",
                    "message": "¡La partida ha comenzado!"
                })
                return {"status": "ok", "message": "¡La partida ha comenzado!"}
            else:
                return {"status": "ok", "message": "Voto registrado. Esperando más votos..."}
        else:
            return {"status": "error", "message": "No se pudo registrar el voto"}
    
    def roll_dice(self, player_name, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        game = self.games[current_game]
        
        if not game.started or game.finished:
            return {"status": "error", "message": "La partida no está en curso"}
        
        player_team = game.get_player_team(player_name)
        if not player_team:
            return {"status": "error", "message": "No estás en ningún equipo"}
        
        current_team_name = game.team_names[game.current_turn]
        if player_team != current_team_name:
            return {"status": "error", "message": f"No es el turno de tu equipo. Turno actual: {current_team_name}"}
        
        team = game.teams[player_team]
        
        # Verificar si todos los miembros del equipo han jugado
        # (Simplificado: cualquier miembro puede tirar por todo el equipo)
        total_roll = 0
        for team_player in team.players:
            roll = random.randint(game.min_dice, game.max_dice)
            total_roll += roll
            
            # Log de cada lanzamiento de dado
            log_dice_roll_start(current_game, player_team, team_player, roll)
            log_dice_roll_end(current_game, player_team, team_player, roll)
        
        # Mover equipo
        team.position += total_roll
        
        # Verificar victoria
        if team.position >= game.board_length:
            game.finished = True
            game.winner = player_team
            
            # Log de victoria
            log_game_win(current_game, player_team)
            log_game_end(current_game)
            
            self.broadcast_to_game(current_game, {
                "type": "game_finished",
                "winner": player_team,
                "message": f"¡El equipo {player_team} ha ganado!"
            })
            
            return {
                "status": "ok",
                "message": f"¡El equipo {player_team} ha ganado!",
                "roll": total_roll,
                "new_position": team.position,
                "game_finished": True
            }
        
        # Siguiente turno
        game.current_turn = (game.current_turn + 1) % len(game.team_names)
        
        self.broadcast_to_game(current_game, {
            "type": "turn_played",
            "team": player_team,
            "player": player_name,
            "roll": total_roll,
            "new_position": team.position,
            "next_turn": game.team_names[game.current_turn]
        })
        
        return {
            "status": "ok",
            "message": f"Equipo avanzó {total_roll} posiciones",
            "roll": total_roll,
            "new_position": team.position,
            "next_turn": game.team_names[game.current_turn]
        }
    
    def leave_game(self, player_name, current_game):
        if not current_game or current_game not in self.games:
            return {"status": "error", "message": "No estás en ninguna partida"}
        
        game = self.games[current_game]
        game.remove_player(player_name)
        
        # Si era el creador, eliminar la partida
        if player_name == game.creator:
            # Log fin de juego
            log_game_end(current_game)
            
            self.broadcast_to_game(current_game, {
                "type": "game_closed",
                "message": "La partida ha sido cerrada por el creador"
            })
            del self.games[current_game]
            
            return {"status": "ok", "message": "Partida cerrada", "current_game": None}
        
        return {"status": "ok", "message": "Has abandonado la partida", "current_game": None}
    
    def broadcast_to_game(self, game_name, message):
        if game_name not in self.games:
            return
        
        game = self.games[game_name]
        for player in game.players:
            self.send_to_player(player, message)
    
    def broadcast_to_team(self, game_name, team_name, message):
        if game_name not in self.games:
            return
        
        game = self.games[game_name]
        if team_name not in game.teams:
            return
        
        team = game.teams[team_name]
        for player in team.players:
            self.send_to_player(player, message)
    
    def send_to_player(self, player_name, message):
        if player_name in self.client_sockets:
            try:
                notification = {
                    "type": "notification",
                    "data": message
                }
                self.client_sockets[player_name].send((json.dumps(notification)+'\n').encode('utf-8'))
            except:
                # Cliente desconectado
                if player_name in self.client_sockets:
                    del self.client_sockets[player_name]

if __name__ == "__main__":
    server = GameServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor...")
        server.running = False
