"""
Demo automatizada del sistema de juego de carreras por equipos
Ejecuta una simulación completa para demostrar todas las funcionalidades
"""
import socket
import json
import time
import threading
import random

class AutomatedGameDemo:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        
    def connect_client(self, name):
        """Conecta un cliente automático al servidor"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            return sock
        except Exception as e:
            print(f"Error conectando cliente {name}: {e}")
            return None
    
    def send_request(self, sock, request):
        """Envía una solicitud y recibe respuesta"""
        try:
            # Agregar \n al final
            message = json.dumps(request) + '\n'
            sock.send(message.encode('utf-8'))
            
            # Aumentar timeout y manejar mejor las respuestas
            sock.settimeout(10)  # ← Aumentar a 10 segundos
            response_data = sock.recv(4096).decode('utf-8').strip()
            
            if not response_data:
                return {"status": "error", "message": "No response received"}
                
            # Intentar parsear JSON
            try:
                return json.loads(response_data)
            except json.JSONDecodeError:
                # Si no es JSON válido, crear respuesta estructurada
                return {"status": "ok", "message": response_data}
                
        except socket.timeout:
            return {"status": "error", "message": "Request timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def simulate_player(self, player_name, team_name, game_name="DemoGame"):
        """Simula las acciones de un jugador automático"""
        print(f"🤖 Iniciando simulación de {player_name}")
        
        sock = self.connect_client(player_name)
        if not sock:
            return
        
        # Iniciar hilo para manejar notificaciones
        notification_thread = threading.Thread(
            target=self.listen_notifications, 
            args=(sock, player_name)
        )
        notification_thread.daemon = True
        notification_thread.start()
        
        try:
            # 1. Registrar nombre
            response = self.send_request(sock, {
                "command": "set_player_name",
                "name": player_name
            })
            
            if self.is_success_response(response):
                print(f"  ✅ {player_name}: Registrado exitosamente")
            
            time.sleep(2)
            
            # 2. Unirse a partida o crearla
            response = self.send_request(sock, {
                "command": "join_game",
                "game_name": game_name
            })
            
            if (response.get('status') == 'error' and 
                'no existe' in response.get('message', '').lower()):
                
                print(f"  🎮 {player_name}: Creando partida {game_name}")
                response = self.send_request(sock, {
                    "command": "create_game",
                    "game_name": game_name,
                    "max_teams": 2,
                    "max_players_per_team": 2,
                    "board_size": 20,
                    "dice_min": 1,
                    "dice_max": 6
                })
                
                time.sleep(2)
                response = self.send_request(sock, {
                    "command": "join_game",
                    "game_name": game_name
                })
            
            if self.is_success_response(response):
                print(f"  ✅ {player_name}: Unido a partida exitosamente")
            
            time.sleep(3)
            
            # 3. Manejo inteligente de equipos
            # Primero: intentar unirse (por si el equipo ya existe)
            print(f"  👥 {player_name}: Buscando equipo {team_name}...")
            response = self.send_request(sock, {
                "command": "join_team",
                "team_name": team_name
            })
            
            if response.get('status') == 'error':
                error_msg = response.get('message', '').lower()
                
                if 'no existe' in error_msg or 'no encontrado' in error_msg:
                    # El equipo no existe, crearlo
                    print(f"  🆕 {player_name}: Creando equipo {team_name}")
                    response = self.send_request(sock, {
                        "command": "create_team",
                        "team_name": team_name
                    })
                    
                    if self.is_success_response(response):
                        print(f"  ✅ {player_name}: Equipo {team_name} creado y liderado")
                    else:
                        print(f"  ❌ {player_name}: Error creando equipo: {response.get('message', '')}")
                
                elif 'ya existe' in error_msg:
                    # El equipo existe pero está lleno o hay otro problema
                    print(f"  ⚠️ {player_name}: {response.get('message', '')}")
            
            else:
                # Unión exitosa o solicitud enviada
                message = response.get('message', '')
                if 'solicitud enviada' in message.lower():
                    print(f"  📝 {player_name}: Solicitud de unión enviada, esperando votación")
                else:
                    print(f"  ✅ {player_name}: Unido a equipo {team_name}")
            
            # 4. Esperar antes de votar (para que se procesen votaciones de equipo)
            time.sleep(8)
            
            # 5. Votar para iniciar partida
            print(f"  🗳️ {player_name}: Votando para iniciar partida")
            response = self.send_request(sock, {"command": "vote_start"})
            
            message = response.get('message', '')
            print(f"  📊 {player_name}: {message}")
            
            # 6. Esperar a que se procesen todos los votos
            time.sleep(15)  # Tiempo suficiente para que voten todos
            
            # 7. Verificar estado del juego
            response = self.send_request(sock, {"command": "game_status"})
            game_status = response.get('game_status', 'unknown')
            print(f"  📊 {player_name}: Estado del juego: {game_status}")
            
            if game_status == 'in_progress':
                print(f"  🎮 {player_name}: ¡Partida iniciada! Comenzando a jugar...")
                
                # 8. Simular juego con dados
                for round_num in range(15):  # Más rondas
                    time.sleep(random.uniform(3, 6))
                    
                    response = self.send_request(sock, {"command": "roll_dice"})
                    
                    message = response.get('message', '')
                    
                    if self.is_success_response(response):
                        if 'lanzó' in message.lower() or 'tiró' in message.lower():
                            print(f"  🎲 {player_name}: {message}")
                            
                            # Verificar si alguien ganó
                            if 'ganado' in message.lower() or 'ganador' in message.lower():
                                print(f"  🏆 {player_name}: ¡Partida terminada!")
                                break
                        else:
                            print(f"  ✅ {player_name}: {message}")
                    else:
                        if 'no es tu turno' not in message.lower():
                            print(f"  ⏰ {player_name}: {message}")
                    
                    # Verificar si la partida terminó
                    if 'terminado' in message.lower() or 'finished' in response.get('game_status', ''):
                        print(f"  🏁 {player_name}: Partida finalizada")
                        break
            
            elif game_status == 'waiting':
                print(f"  ⏳ {player_name}: Partida aún esperando más votos...")
            else:
                print(f"  ❌ {player_name}: Estado inesperado: {game_status}")
            
        except Exception as e:
            print(f"  ❌ Error en simulación de {player_name}: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
            print(f"  👋 {player_name}: Desconectado")

    def is_success_response(self, response):
        """Verifica si una respuesta indica éxito"""
        if not isinstance(response, dict):
            return False
            
        status = response.get('status', '').lower()
        return status in ['ok', 'success'] or 'exitoso' in response.get('message', '').lower()

        
    def listen_notifications(self, sock, player_name):
        """Escucha notificaciones y vota automáticamente cuando sea necesario"""
        try:
            buffer = ""
            while True:
                try:
                    sock.settimeout(0.5)
                    data = sock.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Procesar mensajes completos (separados por \n)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                notification = json.loads(line.strip())
                                
                                # Si es una notificación con datos anidados
                                if notification.get('type') == 'notification':
                                    notification = notification.get('data', {})
                                
                                # Si es una solicitud de voto, votar automáticamente 'si'
                                if (notification.get('type') == 'vote_request' and 
                                    'vote_id' in notification):
                                    
                                    vote_id = notification['vote_id']
                                    requesting_player = notification.get('player_requesting', 'jugador')
                                    print(f"  📝 {player_name}: Auto-votando 'si' para {requesting_player}")
                                    
                                    # Votar 'si' automáticamente
                                    vote_response = self.send_request(sock, {
                                        "command": "vote_team_join",
                                        "vote_id": vote_id,
                                        "vote": "si"
                                    })
                                    print(f"  ✅ {player_name}: Voto enviado")
                                    
                            except json.JSONDecodeError:
                                # Ignorar líneas que no son JSON válido
                                pass
                            
                except socket.timeout:
                    continue
                except Exception:
                    break
                    
        except Exception as e:
            print(f"  {player_name}: Error en listener: {e}")

    def run_demo(self):
        """Ejecuta la demostración completa"""
        print("=" * 50)
        print("🎮 DEMO AUTOMATIZADA - JUEGO DE CARRERAS POR EQUIPOS")
        print("=" * 50)
        print()
        
        # Verificar conectividad
        print("🔍 Verificando conectividad del servidor...")
        test_sock = self.connect_client("test")
        if not test_sock:
            print("❌ No se puede conectar al servidor del juego")
            print("   Asegúrate de que el servidor esté ejecutándose:")
            print("   run_game_server.bat")
            return
        test_sock.close()
        print("✅ Servidor del juego disponible")
        print()
        
        print("🚀 Iniciando simulación con 4 jugadores...")
        print("   - Alice y Charlie en equipo Rojos")
        print("   - Bob y Diana en equipo Azules")
        print()
        
        # CAMBIO: Ejecutar jugadores de manera secuencial para evitar race conditions
        players = [
            ("Alice", "Rojos"),   # Creará equipo Rojos
            ("Bob", "Azules"),    # Creará equipo Azules  
            ("Charlie", "Rojos"), # Se unirá a equipo Rojos
            ("Diana", "Azules")   # Se unirá a equipo Azules
        ]
        
        threads = []
        
        # Iniciar jugadores con retrasos más largos
        for i, (player_name, team_name) in enumerate(players):
            thread = threading.Thread(
                target=self.simulate_player, 
                args=(player_name, team_name)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
            # Retraso progresivo: primer jugador 0s, segundo 5s, tercero 10s, cuarto 15s
            if i < len(players) - 1:  # No esperar después del último
                wait_time = 5 + (i * 3)  # 5, 8, 11 segundos
                print(f"⏳ Esperando {wait_time}s antes del siguiente jugador...")
                time.sleep(wait_time)
        
        # Esperar a que terminen todos
        for thread in threads:
            thread.join(timeout=120)  # Timeout de 2 minutos
        
        print()
        print("=" * 50)
        print("🎯 DEMO COMPLETADA")
        print("=" * 50)

if __name__ == "__main__":
    import sys
    
    host = 'localhost'
    if len(sys.argv) > 1:
        host = sys.argv[1]
    
    demo = AutomatedGameDemo(host=host)
    demo.run_demo()
