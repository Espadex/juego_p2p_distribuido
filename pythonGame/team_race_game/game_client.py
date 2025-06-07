"""
Cliente del juego de carreras por equipos
Interfaz de consola para interactuar con el servidor
"""
import socket
import json
import threading
import time

class GameClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.player_name = None
        self.current_game = None
        self.current_team = None
        self.running = False
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.running = True


            
            # Iniciar hilo para recibir notificaciones
            notification_thread = threading.Thread(target=self.receive_notifications)
            notification_thread.daemon = True
            notification_thread.start()
            
            return True
        except Exception as e:
            print(f"Error conectando al servidor: {e}")
            return False
    
    def disconnect(self):
        self.running = False
        if self.socket:
            self.socket.close()
    
    def send_request(self, request):
        try:
            # AGREGAR \n al final del mensaje
            print(f"📤 Enviando solicitud: {request}")
            message = json.dumps(request) + '\n'
            self.socket.send(message.encode('utf-8'))
            
            self.socket.settimeout(10)  # Establecer timeout para la respuesta
            response_data = self.socket.recv(4096).decode('utf-8')
            if not response_data:
                return {"status": "error", "message": "No response received"}
            
            try:
                parsed_response = json.loads(response_data)
                print(f"🔍 JSON parseado: {parsed_response}")  # ← AGREGAR DEBUG
                return parsed_response
            except json.JSONDecodeError:
                print(f"⚠️ No es JSON válido, tratando como texto: '{response_data}'")
                # Si no es JSON válido, crear respuesta estructurada
                return {"status": "ok", "message": response_data}
        except socket.timeout:
            print("⏰ Timeout esperando respuesta del servidor")  # ← AGREGAR DEBUG
            return {"status": "error", "message": "Request timed out"}
        except Exception as e:
            print(f"❌ Error en comunicación: {e}")  # ← AGREGAR DEBUG
            return {"status": "error", "message": str(e)}
    
    def receive_notifications(self):
        while self.running:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if data:
                    notification = json.loads(data)
                    if notification.get('type') == 'notification':
                        self.handle_notification(notification['data'])
                if not data: print("Servidor cerró la conexión.");
            except:
                break
    
    def handle_notification(self, data):
        msg_type = data.get('type')
        
        if msg_type == 'team_created':
            print(f"\n🎉 Nuevo equipo creado: '{data['team_name']}' por {data['creator']}")
        
        elif msg_type == 'team_member_added':
            print(f"\n👥 {data['player']} se ha unido al equipo '{data['team_name']}'")
        
        elif msg_type == 'vote_request':
            print(f"\n🗳️  VOTACIÓN: {data['message']}")
            print(f"   Usa el comando: votar_equipo {data['vote_id']} si|no")
        
        elif msg_type == 'team_join_result':
            if data['status'] == 'accepted':
                print(f"\n✅ {data['message']}")
                self.current_team = data.get('team_name')
            else:
                print(f"\n❌ {data['message']}")
        
        elif msg_type == 'game_started':
            print(f"\n🎮 {data['message']}")
        
        elif msg_type == 'turn_played':
            print(f"\n🎲 {data['player']} del equipo {data['team']} tiró {data['roll']}")
            print(f"   Equipo {data['team']} ahora en posición {data['new_position']}")
            print(f"   Siguiente turno: {data['next_turn']}")
        
        elif msg_type == 'game_finished':
            print(f"\n🏆 {data['message']}")
        
        elif msg_type == 'game_closed':
            print(f"\n⚠️  {data['message']}")
            self.current_game = None
            self.current_team = None
        
        print("\n> ", end="", flush=True)
    
    def set_player_name(self, name):
        request = {
            "command": "set_player_name",
            "name": name
        }
        response = self.send_request(request)
        if response.get("status") in ["success", "ok"]:
            self.player_name = name
            return True
        else:
            print(f"Error estableciendo nombre: {response.get('message', 'Error desconocido')}")
            return False
    
    def create_game(self, game_name, max_teams, max_players_per_team, board_length, min_dice, max_dice):
        request = {
            "command": "create_game",
            "game_name": game_name,
            "max_teams": max_teams,
            "max_players_per_team": max_players_per_team,
            "board_length": board_length,
            "min_dice": min_dice,
            "max_dice": max_dice
        }
        response = self.send_request(request)
        if response['status'] in ['success', 'ok'] and 'current_game' in response:
            self.current_game = response['current_game']
        return response
    
    
    def list_games(self):
        request = {"command": "list_games"}
        return self.send_request(request)
    
    def create_team(self, team_name):
        request = {
            "command": "create_team",
            "team_name": team_name
        }
        response = self.send_request(request)

        if response.get('type') == 'notification':
            # Es una notificación, crear respuesta basada en los datos
            data = response.get('data', {})
            if data.get('type') == 'team_created' and data.get('creator') == self.player_name:
                self.current_team = team_name
                return {"status": "ok", "message": f"Equipo '{team_name}' creado exitosamente"}
            else:
                return {"status": "error", "message": "Respuesta inesperada del servidor"}
    
        
        # MEJORAR: Verificación más robusta
        status = response.get('status', '')
        if status in ['ok', 'success']:
            # Verificar si hay equipos en la respuesta y el nuestro está ahí
            teams = response.get('teams', [])
            team_exists = any(team.get('name') == team_name for team in teams)
            
            if team_exists:
                self.current_team = team_name
                return {"status": "ok", "message": f"Equipo '{team_name}' creado exitosamente"}
            else:
                message = response.get('message', f"Equipo '{team_name}' creado")
                self.current_team = team_name
                return {"status": "ok", "message": message}
        else:
            return response
    
    def join_game(self, game_name):
        request = {
            "command": "join_game",
            "game_name": game_name
        }
        response = self.send_request(request)
        
        # MEJORAR: Verificación más robusta
        status = response.get('status', '')
        if status in ['ok', 'success'] or 'unido' in response.get('message', '').lower():
            self.current_game = response.get('current_game', game_name)
            return response
        else:
            print(f"🔍 Debug - Respuesta completa: {response}")  # ← AGREGAR DEBUG
            return response
    
    def list_teams(self):
        request = {"command": "list_teams"}
        return self.send_request(request)
    
    def game_status(self):
        request = {"command": "game_status"}
        return self.send_request(request)
    
    def vote_start(self):
        request = {"command": "vote_start"}
        return self.send_request(request)
    
    def roll_dice(self):
        request = {"command": "roll_dice"}
        return self.send_request(request)
    
    def leave_game(self):
        request = {"command": "leave_game"}
        response = self.send_request(request)
        if response['status'] == 'ok':
            self.current_game = None
            self.current_team = None
        return response
    
    def vote_team_join(self, vote_id, vote):
        request = {
            "command": "vote_team_join",
            "vote_id": vote_id,
            "vote": vote
        }
        return self.send_request(request)
    
    def show_main_menu(self):
        print("\n" + "="*50)
        print("🏁 JUEGO DE CARRERAS POR EQUIPOS 🏁")
        print("="*50)
        print("1. Crear partida")
        print("2. Unirse a partida")
        print("3. Listar partidas")
        print("4. Salir")
        print("-"*50)
    
    def show_game_menu(self):
        print(f"\n{'='*50}")
        print(f"🎮 PARTIDA: {self.current_game}")
        if self.current_team:
            print(f"👥 EQUIPO: {self.current_team}")
        print("="*50)
        
        # Menú dinámico basado en el estado
        options = []
        if not self.current_team:
            options.extend([
                "1. Crear equipo",
                "2. Unirse a equipo"
            ])
        
        options.extend([
            "3. Consultar equipos",
            "4. Ver estado del juego",
            "5. Votar para empezar partida",
            "6. Tirar dados",
            "7. Abandonar partida"
        ])
        
        for option in options:
            print(option)
        print("-"*50)
    
    def run(self):
        if not self.connect():
            return
        
        # Solicitar nombre del jugador
        while not self.player_name:
            name = input("🎮 Ingresa tu nombre: ").strip()
            if name:
                success = self.set_player_name(name)  # ← CAMBIAR ESTO
                if success:
                    print(f"✅ Bienvenido, {name}!")
                else:
                    print("❌ Error estableciendo nombre. Intenta de nuevo.")
        
        # Bucle principal
        try:
            while self.running:
                if not self.current_game:
                    self.main_menu_loop()
                else:
                    self.game_menu_loop()
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
        finally:
            self.disconnect()
    
    def main_menu_loop(self):
        while self.running and not self.current_game:
            self.show_main_menu()
            choice = input("Elige una opción: ").strip()
            
            if choice == '1':
                self.create_game_flow()
            elif choice == '2':
                self.join_game_flow()
            elif choice == '3':
                self.list_games_flow()
            elif choice == '4':
                self.running = False
            else:
                print("❌ Opción inválida")
    
    def game_menu_loop(self):
        while self.running and self.current_game:
            self.show_game_menu()
            choice = input("Elige una opción: ").strip().lower()
            
            if choice == '1' and not self.current_team:
                self.create_team_flow()
            elif choice == '2' and not self.current_team:
                self.join_team_flow()
            elif choice == '3':
                self.list_teams_flow()
            elif choice == '4':
                self.game_status_flow()
            elif choice == '5':
                self.vote_start_flow()
            elif choice == '6':
                self.roll_dice_flow()
            elif choice == '7':
                self.leave_game_flow()
            elif choice.startswith('votar_equipo'):
                # Comando especial para votaciones
                parts = choice.split()
                if len(parts) == 3:
                    vote_id = parts[1]
                    vote = parts[2]
                    if vote in ['si', 'no']:
                        response = self.vote_team_join(vote_id, vote)
                        print(f"📝 {response.get('message', 'Voto procesado')}")
                    else:
                        print("❌ Voto debe ser 'si' o 'no'")
                else:
                    print("❌ Formato: votar_equipo <vote_id> si|no")
            else:
                print("❌ Opción inválida")
    
    def create_game_flow(self):
        try:
            print("\n🎮 Crear nueva partida:")
            game_name = input("Nombre de la partida: ").strip()
            max_teams = int(input("Cantidad máxima de equipos: "))
            max_players_per_team = int(input("Jugadores máximos por equipo: "))
            board_length = int(input("Largo del tablero: "))
            min_dice = int(input("Valor mínimo del dado (mín 1): "))
            max_dice = int(input(f"Valor máximo del dado (máx {board_length-1}): "))
            
            if min_dice < 1 or max_dice >= board_length or min_dice > max_dice:
                print("❌ Valores de dados inválidos")
                return
            
            response = self.create_game(game_name, max_teams, max_players_per_team, board_length, min_dice, max_dice)
            
            if response['status'] in ['ok', 'success']:
                print(f"✅ {response['message']}")
            else:
                print(f"❌ {response['message']}")
        except ValueError:
            print("❌ Por favor ingresa números válidos")
    
    def join_game_flow(self):
        self.list_games_flow()
        game_name = input("Nombre de la partida a unirse: ").strip()
        if game_name:
            response = self.join_game(game_name)
            if response['status'] in ['ok', 'success']:
                print("\n '✅' Unido a la partida exitosamente")
            
            else: 
                print(f"❌ Error al unirse a la partida: {response['message']}")
    
    def list_games_flow(self):
        response = self.list_games()
        if response['status'] == 'ok':
            games = response['games']
            if games:
                print("\n📋 Partidas disponibles:")
                for game in games:
                    status = "🔴 En curso" if game['started'] else ("🏁 Terminada" if game['finished'] else "🟢 Esperando")
                    print(f"  • {game['name']} - {status} - {game['players']} jugadores - {game['teams']} equipos")
            else:
                print("📋 No hay partidas disponibles")
        else:
            print(f"❌ {response['message']}")
    
    def create_team_flow(self):
        team_name = input("Nombre del equipo: ").strip()
        if team_name:
            response = self.create_team(team_name)
            
            # MEJORAR: Verificación más robusta
            status = response.get('status', '')
            message = response.get('message', '')
            
            if status in ['ok', 'success']:
                print(f"✅ {message}")
                self.current_team = team_name
            elif status == 'error':
                print(f"❌ {message}")
            else:
                # Si no hay campo status, verificar por mensaje
                print(f"📝 {message}")
                if message:
                    print(f"📝 {message}")
                else:
                    print("📝 Comando procesado")
                #if 'creado' in message.lower() or 'exitoso' in message.lower():
                #   self.current_team = team_name
    
    def join_team_flow(self):
        self.list_teams_flow()
        team_name = input("Nombre del equipo a unirse: ").strip()
        if team_name:
            response = self.join_team(team_name)
            
            status = response.get('status', '')
            message = response.get('message', 'Comando procesado')
            
            if status == 'ok':
                print(f"✅ {message}")
                self.current_team = team_name
            elif status == 'error':
                print(f"❌ {message}")
            else:
                print(f"📝 {message}")
    
    def join_team(self, team_name):
        request = {
            "command": "join_team",
            "team_name": team_name
        }
        response = self.send_request(request)
        
        # Verificar si es una notificación en lugar de respuesta
        if response.get('type') == 'notification':
            data = response.get('data', {})
            if data.get('type') == 'team_join_result':
                if data.get('status') == 'accepted':
                    self.current_team = team_name
                    return {"status": "ok", "message": data.get('message', f"Te has unido al equipo '{team_name}'")}
                else:
                    return {"status": "error", "message": data.get('message', 'Solicitud rechazada')}
        
        # Respuesta normal
        status = response.get('status', '')
        if status in ['ok', 'success']:
            message = response.get('message', f"Solicitud enviada para unirse a '{team_name}'")
            # Solo actualizar current_team si la unión fue inmediata
            if 'unido' in message.lower() or 'aceptado' in message.lower():
                self.current_team = team_name
            return {"status": "ok", "message": message}
        else:
            return response


    def list_teams_flow(self):
        response = self.list_teams()
        
        # MEJORAR: Verificación más robusta
        status = response.get('status', '')
        
        if status in ['ok', 'success']:
            teams = response.get('teams', [])
            if teams:
                print("\n👥 Equipos en la partida:")
                for team in teams:
                    players_str = ", ".join(team.get('players', []))
                    position = team.get('position', 'N/A')
                    print(f"  • {team.get('name', 'Sin nombre')} (Posición: {position}) - Jugadores: {players_str}")
            else:
                print("👥 No hay equipos creados")
        elif status == 'error':
            print(f"❌ {response.get('message', 'Error desconocido')}")
        else:
            # Si no hay campo status, mostrar el mensaje directamente
            message = response.get('message', str(response))
            print(f"📝 {message}")
            
            # Si parece que hay equipos en el mensaje, intentar procesarlo
            if 'equipos' in message.lower() or 'teams' in str(response).lower():
                print("👥 Información de equipos recibida")

    def game_status_flow(self):
        response = self.game_status()
        status = response.get('status', '')
        if status in ['ok', 'success']:
            game_status = response.get('game_status', 'unknown')
        
            if game_status == 'waiting':
                message = response.get('message', 'Esperando inicio de partida')
                print(f"\n⏳ {message}")
                
                votes = response.get('votes_to_start', 'N/A')
                print(f"🗳️  Votos para empezar: {votes}")
                
                if response.get('can_start'):
                    print("✅ ¡Todos listos para empezar!")
                    
            elif game_status == 'playing':
                print(f"\n🏁 Partida en curso:")
                # Mostrar posiciones si están disponibles
                positions = response.get('positions', [])
                board_length = response.get('board_length', 'N/A')
                
                if positions:
                    print(f"📊 Tablero (1-{board_length}):")
                    for pos in positions:
                        players_str = ", ".join(pos.get('players', []))
                        team_name = pos.get('team', 'Equipo')
                        position = pos.get('position', 0)
                        print(f"  🏃 {team_name}: Posición {position} - {players_str}")
                
                current_turn = response.get('current_turn', 'N/A')
                print(f"\n🎯 Turno actual: {current_turn}")
            elif game_status == 'finished':
                print(f"\n🏆 ¡Partida terminada!")
                winner = response.get('winner', 'Desconocido')
                print(f"🥇 Ganador: {winner}")
            else:
                message = response.get('message', f'Estado: {game_status}')
                print(f"\n📊 {message}")
        else:
            message = response.get('message', 'Error consultando estado')
            print(f"❌ {message}")  

          
    def vote_start_flow(self):
        response = self.vote_start()
        status = response.get('status', '')
        message = response.get('message', '')
        
        if status == 'ok':
            # Si no hay mensaje, crear uno basado en el contenido
            if not message:
                if 'teams' in response:
                    message = "Voto registrado exitosamente"
                else:
                    message = "Comando procesado"
            print(f"✅ {message}")
        elif status == 'error':
            print(f"❌ {message}")
        else:
            # Si no hay status claro, intentar interpretar
            if 'teams' in response:
                print("✅ Voto procesado")
            else:
                print(f"📝 Respuesta: {response}")
    
    def roll_dice_flow(self):
        response = self.roll_dice()
        status = response.get('status', '')
        message = response.get('message', '')
    
        if status == 'ok':
            print(f"🎲 {message}")
            
            # Mostrar detalles adicionales si están disponibles
            if 'roll' in response:
                print(f"   Dados totales: {response['roll']}")
            if 'new_position' in response:
                print(f"   Nueva posición: {response['new_position']}")
            if 'next_turn' in response:
                print(f"   Siguiente turno: {response['next_turn']}")
        else:
            if not message:
                message = "No se pudo procesar el lanzamiento"
            print(f"❌ {message}")
    
    def leave_game_flow(self):
        response = self.leave_game()
        print(f"{'✅' if response['status'] == 'ok' else '❌'} {response['message']}")

if __name__ == "__main__":
    import sys
    
    # Permitir especificar host como argumento de línea de comandos
    host = 'localhost'
    if len(sys.argv) > 1:
        host = sys.argv[1]
    
    client = GameClient(host=host)
    client.run()
