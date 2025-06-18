"""
Cliente RMI simplificado para logging
Utiliza un servidor proxy en Java que expone RMI a través de sockets TCP
"""
import socket
import json
import time
import threading
from datetime import datetime

class SimpleRMILogger:
    def __init__(self, proxy_host='localhost', proxy_port=25334):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.connected = False
        self.socket = None
        self.log_queue = []
        self.queue_lock = threading.Lock()
        
    def connect(self):
        """Conecta al proxy del servidor RMI"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.proxy_host, self.proxy_port))
            self.connected = True
            
            print(f"✅ Conectado al proxy RMI en {self.proxy_host}:{self.proxy_port}")
            
            # Procesar logs pendientes
            self._process_queued_logs()
            
            return True
            
        except Exception as e:
            print(f"❌ Error conectando al proxy RMI: {e}")
            print("⚠️  Los logs se almacenarán localmente hasta que se restablezca la conexión")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta del proxy RMI"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def log_start(self, game_id, operation, *details):
        """Registra el inicio de una operación"""
        timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
        self._send_log('logStart', timestamp, game_id, operation, details)
    
    def log_end(self, game_id, operation, *details):
        """Registra el fin de una operación"""
        timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
        self._send_log('logEnd', timestamp, game_id, operation, details)
    
    def _send_log(self, method, timestamp, game_id, operation, details):
        """Envía un log al proxy RMI"""
        log_request = {
            'method': method,
            'timestamp': timestamp,
            'gameId': game_id,
            'operation': operation,
            'details': list(details) if details else []
        }
        
        if self.connected and self.socket:
            try:
                message = json.dumps(log_request) + '\n'
                self.socket.send(message.encode('utf-8'))
                
                # Leer respuesta
                response = self.socket.recv(1024).decode('utf-8').strip()
                if response == 'OK':
                    print(f"📝 Log enviado: {method} - {game_id} - {operation}")
                else:
                    print(f"⚠️  Respuesta inesperada del servidor: {response}")
                    
            except Exception as e:
                print(f"❌ Error enviando log: {e}")
                self.connected = False
                self._queue_log(log_request)
        else:
            self._queue_log(log_request)
    
    def _queue_log(self, log_request):
        """Almacena un log en la cola local"""
        with self.queue_lock:
            self.log_queue.append(log_request)
            print(f"📋 Log almacenado localmente: {log_request['operation']}")
    
    def _process_queued_logs(self):
        """Procesa los logs almacenados en cola"""
        with self.queue_lock:
            if not self.log_queue:
                return
            
            print(f"📤 Procesando {len(self.log_queue)} logs pendientes...")
            
            for log_request in self.log_queue.copy():
                try:
                    message = json.dumps(log_request) + '\n'
                    self.socket.send(message.encode('utf-8'))
                    
                    response = self.socket.recv(1024).decode('utf-8').strip()
                    if response == 'OK':
                        self.log_queue.remove(log_request)
                    else:
                        print(f"⚠️  Error procesando log pendiente: {response}")
                        break
                        
                except Exception as e:
                    print(f"❌ Error procesando log pendiente: {e}")
                    self.connected = False
                    break
            
            if not self.log_queue:
                print("✅ Todos los logs pendientes han sido enviados")
    
    def save_logs_to_file(self, filename="local_logs.json"):
        """Guarda los logs pendientes en un archivo"""
        with self.queue_lock:
            if self.log_queue:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.log_queue, f, indent=2, ensure_ascii=False)
                    print(f"💾 Logs guardados en {filename}")
                except Exception as e:
                    print(f"❌ Error guardando logs: {e}")

# Instancia global del logger RMI simplificado
simple_rmi_logger = SimpleRMILogger()

# Funciones de conveniencia para usar en el juego
def log_game_start(game_id):
    """Log del inicio de un juego"""
    simple_rmi_logger.log_start(game_id, "inicio-juego")

def log_game_end(game_id):
    """Log del fin de un juego"""
    simple_rmi_logger.log_end(game_id, "fin-juego")

def log_player_create_start(game_id, team_name, player_name):
    """Log del inicio de creación de jugador"""
    simple_rmi_logger.log_start(game_id, "crea-jugador", team_name, player_name)

def log_player_create_end(game_id, team_name, player_name):
    """Log del fin de creación de jugador"""
    simple_rmi_logger.log_end(game_id, "crea-jugador", team_name, player_name)

def log_dice_roll_start(game_id, team_name, player_name, dice_value):
    """Log del inicio de lanzamiento de dado"""
    simple_rmi_logger.log_start(game_id, "lanza-dado", team_name, player_name, str(dice_value))

def log_dice_roll_end(game_id, team_name, player_name, dice_value):
    """Log del fin de lanzamiento de dado"""
    simple_rmi_logger.log_end(game_id, "lanza-dado", team_name, player_name, str(dice_value))

def log_team_create_start(game_id, team_name, creator):
    """Log del inicio de creación de equipo"""
    simple_rmi_logger.log_start(game_id, "crea-equipo", team_name, creator)

def log_team_create_end(game_id, team_name, creator):
    """Log del fin de creación de equipo"""
    simple_rmi_logger.log_end(game_id, "crea-equipo", team_name, creator)

def log_team_join_start(game_id, team_name, player_name):
    """Log del inicio de unión a equipo"""
    simple_rmi_logger.log_start(game_id, "une-equipo", team_name, player_name)

def log_team_join_end(game_id, team_name, player_name):
    """Log del fin de unión a equipo"""
    simple_rmi_logger.log_end(game_id, "une-equipo", team_name, player_name)

def log_game_win(game_id, team_name):
    """Log de victoria de equipo"""
    simple_rmi_logger.log_start(game_id, "equipo-gana", team_name)
    simple_rmi_logger.log_end(game_id, "equipo-gana", team_name)

def init_rmi_logging():
    """Inicializa el cliente RMI de logging"""
    print("🔌 Inicializando cliente RMI para logging...")
    if not simple_rmi_logger.connect():
        print("⚠️  Continuando sin logging RMI (se almacenará localmente)")

def cleanup_rmi_logging():
    """Limpia la conexión RMI y guarda logs pendientes"""
    simple_rmi_logger.save_logs_to_file()
    simple_rmi_logger.disconnect()

if __name__ == "__main__":
    # Prueba del cliente RMI simple
    print("🧪 Probando cliente RMI simple de logging...")
    
    init_rmi_logging()
    
    # Simular algunos logs
    log_game_start("juego_test")
    log_team_create_start("juego_test", "equipo1", "jugador1")
    log_team_create_end("juego_test", "equipo1", "jugador1")
    log_dice_roll_start("juego_test", "equipo1", "jugador1", 6)
    log_dice_roll_end("juego_test", "equipo1", "jugador1", 6)
    log_game_end("juego_test")
    
    cleanup_rmi_logging()
    print("✅ Prueba completada")
