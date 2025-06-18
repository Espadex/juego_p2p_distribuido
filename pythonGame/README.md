# Juego de Carreras por Equipos con Logging RMI

Este proyecto implementa un juego de carreras por equipos en Python con un sistema de logging centralizado usando RMI en Java.

## Estructura del Proyecto

```
team_race_game/           # Juego principal en Python
├── game_server_with_logging.py      # Servidor del juego con logging integrado
├── game_client.py                   # Cliente del juego (interfaz de usuario)
├── simple_rmi_logger.py            # Cliente RMI simplificado para logging

rmi_logging/             # Sistema RMI en Java
├── LoggingService.java              # Interfaz RMI
├── LoggingServiceImpl.java          # Implementación del servicio
├── LoggingServer.java               # Servidor RMI principal
└── RMIProxy.java                    # Proxy TCP-RMI para Python
```

## Características del Juego

### Mecánicas Principales

- **Tablero unidimensional**: Casillas del 1 al N (configurable)
- **Equipos**: Múltiples jugadores por equipo
- **Turnos**: Cada equipo juega por turnos
- **Dados**: Todos los miembros del equipo tiran dados, se suma el total
- **Victoria**: Primer equipo en llegar a la meta gana

### Funcionalidades

1. **Gestión de Partidas**

   - Crear partida con parámetros personalizables
   - Unirse a partidas existentes
   - Listar partidas disponibles
2. **Gestión de Equipos**

   - Crear equipos dentro de partidas
   - Unirse a equipos (con votación de miembros existentes)
   - Consultar equipos y sus miembros
3. **Sistema de Votación**

   - Votación para iniciar partida (todos los jugadores deben votar)
   - Votación para admitir nuevos miembros a equipos (mayoría 50+1)
4. **Gameplay**

   - Lanzamiento de dados por turnos
   - Avance automático en el tablero
   - Notificaciones en tiempo real
   - Detección automática de victoria

### Logging Centralizado RMI

- **Registro detallado**: Inicio y fin de cada operación
- **Timestamps**: Marcas de tiempo precisas
- **Centralización**: Todos los logs van a un servidor central
- **Persistencia**: Logs guardados en archivo
- **Formato estructurado**: timestamp, tipo, juego, operación, detalles

## Instalación y Configuración

### Requisitos

- **Python 3.7+**
- **Java 8+**
- **Gson library** (para JSON en Java)

### Opción A: Inicio Automático (Recomendado)

#### Windows - Scripts de Lote

El proyecto incluye scripts .bat para facilitar el inicio:

```cmd
# Compilar e iniciar todo automáticamente
start_all.bat

# O iniciar componentes individualmente:
compile.bat                 # Compilar Java
run_rmi_server.bat         # Servidor RMI + Registry
run_rmi_proxy.bat          # Proxy TCP-RMI
run_game_server.bat        # Servidor del juego
run_game_client.bat        # Cliente del juego
test_system.bat            # Probar conectividad
```

#### Paso a paso automático:

1. **Ejecutar `start_all.bat`** - Inicia todos los componentes
2. **Ejecutar `run_game_client.bat`** - Para cada jugador
3. **Ejecutar `test_system.bat`** - Verificar funcionamiento

### Opción B: Inicio Manual

#### Paso 1: Compilar el Sistema RMI (Java)

```cmd
# Ejecutar script de compilación
compile.bat

# O manualmente:
cd rmi_logging
javac *.java
```

#### Paso 2: Iniciar el Servidor RMI

```cmd
# Terminal 1: Iniciar servidor de logging
cd rmi_logging
start rmiregistry 1099
java LoggingServer

# Terminal 2: Iniciar proxy TCP-RMI
java RMIProxy
```

#### Paso 3: Iniciar el Juego (Python)

```cmd
# Terminal 3: Iniciar servidor del juego
cd team_race_game
python game_server_with_logging.py

# Terminal 4+: Clientes del juego (uno por jugador)
python game_client.py [servidor_ip]
```

## Uso del Juego

### Flujo Básico

1. **Configurar nombre**: Al iniciar, ingresa tu nombre de jugador
2. **Crear o unirse a partida**:

   - Crear: Define parámetros (equipos, jugadores, tablero, dados)
   - Unirse: Selecciona una partida existente
3. **Formar equipos**:

   - Crear equipo nuevo
   - Unirse a equipo existente (requiere votación)
4. **Iniciar partida**:

   - Todos los jugadores deben votar para empezar
   - Solo inicia cuando todos están de acuerdo
5. **Jugar**:

   - Esperar tu turno de equipo
   - Tirar dados (suma de todos los miembros)
   - Ver avance en el tablero
6. **Victoria**:

   - Primer equipo en llegar a la meta gana
   - Notificación automática a todos los jugadores

### Comandos Especiales

Durante el juego, también puedes usar comandos directos:

```
votar_equipo <vote_id> si|no    # Votar en solicitudes de unión
```

## Ejemplos de Logs RMI

El sistema genera logs estructurados como:

```
timestamp(1640995200000), ini, partida1, inicio-juego
timestamp(1640995201000), ini, partida1, crea-equipo, equipo1, jugador1
timestamp(1640995201100), fin, partida1, crea-equipo, equipo1, jugador1
timestamp(1640995202000), ini, partida1, lanza-dado, equipo1, jugador1, 6
timestamp(1640995202050), fin, partida1, lanza-dado, equipo1, jugador1, 6
```

## Arquitectura Técnica

### Comunicación

- **Cliente-Servidor Juego**: TCP Sockets + JSON
- **Python-Java**: TCP Proxy + RMI
- **Multithreading**: Manejo concurrente de múltiples clientes

### Tolerancia a Fallos

- **Logs locales**: Si RMI falla, logs se almacenan localmente
- **Reconexión automática**: Intento de reconectar al servidor RMI
- **Backup de datos**: Logs guardados en archivos JSON

### Escalabilidad

- **Pool de hilos**: Manejo eficiente de conexiones
- **Estado distribuido**: Cada partida es independiente
- **Logging asíncrono**: No bloquea el gameplay

## Verificación del Sistema

### Verificar que Todo Funciona

Después de iniciar los componentes, puedes verificar que el sistema funciona correctamente:

```cmd
# Ejecutar script de verificación
test_system.bat

# O manualmente probar cada componente:
cd team_race_game
python test_system.py [servidor_ip]
```

### Puertos y Servicios

El sistema utiliza los siguientes puertos:

- **1099**: RMI Registry (Java)
- **8888**: RMI TCP Proxy (Java → Python)
- **12345**: Servidor del Juego (Python)

### Verificación Manual

1. **RMI Server**: Debe mostrar "LoggingServer ready and waiting..."
2. **RMI Proxy**: Debe mostrar "RMI Proxy listening on port 8888"
3. **Game Server**: Debe mostrar "Servidor iniciado en puerto 12345"
4. **Test Script**: Debe mostrar "✅ PASS" para todos los componentes

## Troubleshooting

### Problemas Comunes

1. **Error "RMI registry not found"**:

   ```bash
   # Asegúrate de que el servidor RMI esté corriendo
   java LoggingServer
   ```
2. **Error "Connection refused" en proxy**:

   ```bash
   # Verifica que el proxy esté iniciado
   java RMIProxy
   ```
3. **Logs no aparecen**:

   - Verifica que el proxy RMI esté corriendo
   - Los logs se guardan localmente si RMI falla
   - Revisa `local_logs.json`
4. **Puerto en uso**:

   - Cambia los puertos en las configuraciones
   - GameServer: puerto 12345
   - RMI Registry: puerto 1099
   - RMI Proxy: puerto 25334

## Contribución

Para extender el juego:

1. **Nuevas mecánicas**: Modifica `game_server_with_logging.py`
2. **UI mejorada**: Actualiza `game_client.py`
3. **Más logs**: Añade llamadas en `simple_rmi_logger.py`
4. **Análisis**: Procesa logs desde `LoggingServiceImpl.java`

## Inicio Rápido

### Para Probar el Sistema Inmediatamente

1. **Ejecutar compilación y inicio automático**:

   ```cmd
   start_all.bat
   ```
2. **Abrir múltiples clientes** (uno para cada jugador):

   ```cmd
   run_game_client.bat
   ```
3. **Crear y jugar una partida de ejemplo**:

   - Jugador 1: Crear partida "test" (2 equipos, 2 jugadores, tablero 50, dados 1-6)
   - Jugador 2: Unirse a partida "test"
   - Jugador 1: Crear equipo "Rojos"
   - Jugador 2: Crear equipo "Azules"
   - Ambos: Votar para iniciar partida
   - Turnos: Cada jugador tira dados en su turno hasta que un equipo gane
4. **Verificar logs RMI**:

   - Los logs aparecen en la consola del servidor RMI
   - También se guardan en `game_logs.txt`

### Estructura de Comandos del Cliente

```
Menú principal:
1. Crear partida
2. Unirse a partida  
3. Listar partidas
4. Salir

Dentro de partida:
1. Crear equipo
2. Unirse a equipo
3. Ver equipos
4. Votar para iniciar
5. Lanzar dados (en turno)
6. Salir de partida
```

¡Disfruta el juego! 🎮🏁
