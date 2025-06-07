"""
Cliente RMI para enviar logs al servidor centralizado de Java
Utiliza Py4J para comunicarse con RMI Java
"""
import time
import threading
from datetime import datetime
from py4j.java_gateway import JavaGateway, GatewayParameters
from py4j.protocol import Py4JNetworkError
import json

class RMILoggingClient:
    def __init__(self, rmi_host='localhost', rmi_port=1099):
        self.rmi_host = rmi_host
        self.rmi_port = rmi_port
        self.logging_service = None
        self.connected = False
        self.log_queue = []
        self.queue_lock = threading.Lock()
        
    def connect(self):
        """Conecta al servidor RMI de logging"""
        try:
            # Intentar conectar usando Py4J (requiere un gateway Java)
            gateway = JavaGateway(gateway_parameters=GatewayParameters(port=25333))
            
            # Obtener referencia al servicio RMI
            registry = gateway.jvm.java.rmi.registry.LocateRegistry.getRegistry(self.rmi_host, self.rmi_port)
            self.logging_service = registry.lookup("LoggingService")
            
            self.connected = True
            print(f"✅ Conectado al servidor de logging RMI en {self.rmi_host}:{self.rmi_port}")
            
            # Procesar logs pendientes
            self._process_queued_logs()
            
            return True
            
        except Exception as e:
            print(f"❌ Error conectando al servidor RMI: {e}")
            print("⚠️  Los logs se almacenarán localmente hasta que se restablezca la conexión")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta del servidor RMI"""
        self.connected = False
        self.logging_service = None
    
    def log_start(self, game_id, operation, *details):
        """Registra el inicio de una operación"""
        timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
        self._send_log('start', timestamp, game_id, operation, details)
    
    def log_end(self, game_id, operation, *details):
        """Registra el fin de una operación"""
        timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
        self._send_log('end', timestamp, game_id, operation, details)
    
    def _send_log(self, log_type, timestamp, game_id, operation, details):
        """Envía un log al servidor RMI o lo almacena en cola si no está conectado"""
        log_entry = {
            'type': log_type,
            'timestamp': timestamp,
            'game_id': game_id,
            'operation': operation,
            'details': list(details) if details else []
        }
        
        if self.connected and self.logging_service:
            try:
                if log_type == 'start':
                    self.logging_service.logStart(timestamp, game_id, operation, *details)
                else:
                    self.logging_service.logEnd(timestamp, game_id, operation, *details)
                
                print(f"📝 Log enviado: {log_type} - {game_id} - {operation}")
                
            except Exception as e:
                print(f"❌ Error enviando log: {e}")
                self._queue_log(log_entry)
        else:
            self._queue_log(log_entry)
    
    def _queue_log(self, log_entry):
        """Almacena un log en la cola local"""
        with self.queue_lock:
            self.log_queue.append(log_entry)
            print(f"📋 Log almacenado localmente: {log_entry['operation']}")
    
    def _process_queued_logs(self):
        """Procesa los logs almacenados en cola"""
        with self.queue_lock:
            if not self.log_queue:
                return
            
            print(f"📤 Procesando {len(self.log_queue)} logs pendientes...")
            
            for log_entry in self.log_queue.copy():
                try:
                    if log_entry['type'] == 'start':
                        self.logging_service.logStart(
                            log_entry['timestamp'],
                            log_entry['game_id'],
                            log_entry['operation'],
                            *log_entry['details']
                        )
                    else:
                        self.logging_service.logEnd(
                            log_entry['timestamp'],
                            log_entry['game_id'],
                            log_entry['operation'],
                            *log_entry['details']
                        )
                    
                    self.log_queue.remove(log_entry)
                    
                except Exception as e:
                    print(f"❌ Error procesando log pendiente: {e}")
                    break
            
            if not self.log_queue:
                print("✅ Todos los logs pendientes han sido enviados")
    
    def retry_connection(self, max_retries=3):
        """Intenta reconectar al servidor RMI"""
        for attempt in range(max_retries):
            print(f"🔄 Intento de reconexión {attempt + 1}/{max_retries}...")
            if self.connect():
                return True
            time.sleep(2 ** attempt)  # Backoff exponencial
        
        print("❌ No se pudo reconectar al servidor RMI")
        return False

# Instancia global del cliente RMI
rmi_logger = RMILoggingClient()

# Funciones de conveniencia para usar en el juego
def log_game_start(game_id):
    """Log del inicio de un juego"""
    rmi_logger.log_start(game_id, "inicio-juego")

def log_game_end(game_id):
    """Log del fin de un juego"""
    rmi_logger.log_end(game_id, "fin-juego")

def log_player_create_start(game_id, team_name, player_name):
    """Log del inicio de creación de jugador"""
    rmi_logger.log_start(game_id, "crea-jugador", team_name, player_name)

def log_player_create_end(game_id, team_name, player_name):
    """Log del fin de creación de jugador"""
    rmi_logger.log_end(game_id, "crea-jugador", team_name, player_name)

def log_dice_roll_start(game_id, team_name, player_name, dice_value):
    """Log del inicio de lanzamiento de dado"""
    rmi_logger.log_start(game_id, "lanza-dado", team_name, player_name, str(dice_value))

def log_dice_roll_end(game_id, team_name, player_name, dice_value):
    """Log del fin de lanzamiento de dado"""
    rmi_logger.log_end(game_id, "lanza-dado", team_name, player_name, str(dice_value))

def log_team_create_start(game_id, team_name, creator):
    """Log del inicio de creación de equipo"""
    rmi_logger.log_start(game_id, "crea-equipo", team_name, creator)

def log_team_create_end(game_id, team_name, creator):
    """Log del fin de creación de equipo"""
    rmi_logger.log_end(game_id, "crea-equipo", team_name, creator)

def log_team_join_start(game_id, team_name, player_name):
    """Log del inicio de unión a equipo"""
    rmi_logger.log_start(game_id, "une-equipo", team_name, player_name)

def log_team_join_end(game_id, team_name, player_name):
    """Log del fin de unión a equipo"""
    rmi_logger.log_end(game_id, "une-equipo", team_name, player_name)

def log_game_win(game_id, team_name):
    """Log de victoria de equipo"""
    rmi_logger.log_start(game_id, "equipo-gana", team_name)
    rmi_logger.log_end(game_id, "equipo-gana", team_name)

def init_rmi_logging():
    """Inicializa el cliente RMI de logging"""
    print("🔌 Inicializando cliente RMI para logging...")
    if not rmi_logger.connect():
        print("⚠️  Continuando sin logging RMI (se almacenará localmente)")

def cleanup_rmi_logging():
    """Limpia la conexión RMI"""
    rmi_logger.disconnect()

if __name__ == "__main__":
    # Prueba del cliente RMI
    print("🧪 Probando cliente RMI de logging...")
    
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
