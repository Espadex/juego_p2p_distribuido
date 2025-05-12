# Juego de Equipos y Tablero

Este es un juego P2P jerárquico y distribuido donde equipos compiten tirando dados para avanzar en un tablero. El primer equipo en llegar a la meta o superarla gana.

## Requisitos

- Python 3.6 o superior
- Sistema operativo compatible (Windows, Linux, MacOS)
- Elixir (opcional, para el componente P2P)

## Cómo iniciar el juego

1. **Sin el componente Elixir**:
   ```
   juego.bat
   ```

2. **Con el componente Elixir** (recomendado para multijugador):
   ```
   juego.bat "d:\pasca\Downloads\Practica_elixir\p2p_game"
   ```

> **Importante**: Para jugar en modo multijugador, todos los jugadores deben iniciar el juego con la misma ruta al proyecto Elixir.

## Arquitectura

El juego está diseñado con las siguientes partes:

1. **Interfaz del Juego** (`game.py`): Gestiona la lógica del juego, incluyendo:
   - Jugadores (clase `Player`)
   - Equipos (clase `Team`)
   - Juego (clase `Game`)
   - Cliente del Juego (clase `GameClient`)

2. **Interfaz de Red** (`network_interface.py`): Conecta el juego con la aplicación P2P de Elixir:
   - Gestiona la comunicación con el servicio de descubrimiento (puerto 80)
   - Maneja la comunicación con los nodos maestro (puertos 4000-5000)
   - Implementa las funciones necesarias para crear, unirse y jugar partidas
   - Inicia y gestiona el componente Elixir para P2P

3. **Conector** (`connector.py`): Conecta el cliente del juego con la interfaz de red y maneja la comunicación bidireccional con Elixir.

## Variables Importantes

El juego utiliza las siguientes variables de configuración:

- **DISCOVERY_HOST**: Host del servicio de descubrimiento (por defecto: 'localhost')
- **DISCOVERY_PORT**: Puerto del servicio de descubrimiento (por defecto: 80)
- **GAME_PORTS_RANGE**: Rango de puertos para las partidas (por defecto: 4000-5000)
- **ELIXIR_PATH**: Ruta al proyecto Elixir (opcional)

## Flujo del Juego

1. Al iniciar, se solicita al jugador ingresar un nombre.
2. El jugador puede:
   - Crear un juego (configurando equipos, jugadores por equipo, tamaño del tablero y valores del dado)
   - Unirse a un juego existente
   - Salir del juego

3. Dentro de un juego, el jugador puede:
   - Crear equipos
   - Unirse a equipos (con votación)
   - Iniciar el juego (si es el creador)
   - Tirar los dados (cuando sea su turno)
   - Ver el estado del juego

4. El juego continúa hasta que un equipo alcance o supere la posición final del tablero.

## Comunicación con Elixir

El juego se comunica con un componente Elixir que maneja la lógica P2P:

1. **Protocolo de Comunicación**:
   - Mensajes JSON con delimitador de nueva línea
   - Cada mensaje contiene un campo 'action' que indica la acción a realizar
   - Respuestas incluyen un campo 'status' que indica éxito o fallo

2. **Flujo de Comunicación**:
   - Python inicia el nodo Elixir si se proporciona la ruta
   - Python se conecta al servicio de descubrimiento (puerto 80)
   - Elixir maneja la creación de nodos maestros y esclavos
   - Python recibe actualizaciones de estado a través de callbacks

3. **Tipos de Mensajes**:
   - Descubrimiento: listar juegos, unirse a juegos
   - Gestión de equipos: crear, unirse, votar
   - Juego: iniciar, tirar dados, actualizar estado
   - Sistema: registrar callbacks, manejar caídas de nodos

## Modelo de Comunicación

- **Nodos Comunes**: Jugadores en el menú inicial, escuchan en el puerto 80.
- **Nodo Maestro/Admin**: Creador de la partida, atiende en un puerto asignado (4000-5000).
- **Nodos Esclavos/Jugadores**: Se conectan directamente al nodo maestro de la partida.

## Estructura del Componente Elixir

El componente Elixir debe proporcionar las siguientes funcionalidades:

1. **Servicio de Descubrimiento**: En el puerto 80, gestiona el registro y descubrimiento de partidas.
2. **Gestión de Nodos**: Crea nodos maestros y esclavos, gestiona la comunicación entre ellos.
3. **Tolerancia a Fallos**: Maneja fallos en nodos maestros, reasignando el rol a otro nodo.
4. **Broadcast**: Distribuye actualizaciones de estado a todos los nodos participantes.

Para iniciar el juego con el componente Elixir, proporcione la ruta al proyecto Elixir como argumento al ejecutar `juego.bat`.
