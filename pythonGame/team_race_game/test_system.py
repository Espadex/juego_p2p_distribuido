"""
Script de prueba para verificar la conectividad del sistema
Verifica que todos los componentes estén funcionando correctamente
"""
import socket
import json
import time
import sys

def test_game_server(host='localhost', port=12345):
    """Prueba la conectividad con el servidor del juego"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        # Enviar una solicitud simple
        request = {"action": "list_games"}
        sock.send(json.dumps(request).encode('utf-8'))
        
        # Recibir respuesta
        response = sock.recv(1024).decode('utf-8')
        data = json.loads(response)
        
        sock.close()
        return True, "Game server is responding"
    except Exception as e:
        return False, f"Game server error: {e}"

def test_rmi_proxy(host='localhost', port=25334):
    """Prueba la conectividad con el proxy RMI"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        # Enviar un mensaje de prueba
        test_message = {
            "method": "logStart",                    # Método RMI a llamar
            "timestamp": int(time.time() * 1000),   # Timestamp en milisegundos
            "gameId": "TEST",                       # ID del juego
            "operation": "system_test",             # Operación realizada
            "details": ["System startup verification", "connectivity_test"]  # Array de detalles
        }

        message_json = json.dumps(test_message) + '\n'
        sock.send(message_json.encode('utf-8'))  # ← CAMBIAR ESTA LÍNEA
        print(f"📤 Mensaje enviado: {test_message}")
        
        # Esperar respuesta
        sock.settimeout(5)
        response = sock.recv(1024).decode('utf-8').strip()
        print(f"📥 Respuesta recibida: '{response}'")

        sock.close()
        if "OK" in response:
            return True, "RMI proxy is responding"
        else:
            return False, f"RMI proxy returned: {response}"
    except socket.timeout:
        return False, "RMI proxy error: timed out (no response received)"
    except Exception as e:
        return False, f"RMI proxy error: {e}"

def main():
    print("================================")
    print("Team Race Game - System Test")
    print("================================")
    print()
    
    host = 'localhost'
    if len(sys.argv) > 1:
        host = sys.argv[1]
    
    print(f"Testing system components on {host}...")
    print()
    
    # Test Game Server
    print("1. Testing Game Server (port 12345)...")
    success, message = test_game_server(host)
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: {message}")
    
    # Test RMI Proxy
    print("2. Testing RMI TCP Proxy (port 25334)...")
    success, message = test_rmi_proxy(host)
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: {message}")
    
    print()
    print("Test completed.")
    print()
    print("If all tests pass, the system is ready for use!")
    print("If any test fails, make sure all components are running:")
    print("- RMI Server (run_rmi_server.bat)")
    print("- RMI Proxy (run_rmi_proxy.bat)")  
    print("- Game Server (run_game_server.bat)")

if __name__ == "__main__":
    main()
