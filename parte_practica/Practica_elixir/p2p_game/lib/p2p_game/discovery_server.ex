defmodule P2pGame.DiscoveryServer do
  @moduledoc """
  Discovery server that listens on port 80 for new game announcements and player requests.
  """
  use GenServer
  require Logger

  @port 80

  # Client API

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def list_games do
    GenServer.call(__MODULE__, :list_games)
  end

  def register_game(game_id, creator_name, game_data, port) do
    GenServer.cast(__MODULE__, {:register_game, game_id, creator_name, game_data, port})
  end

  def update_game_state(game_id, state) do
    GenServer.cast(__MODULE__, {:update_game_state, game_id, state})
  end

  def delete_game(game_id) do
    GenServer.cast(__MODULE__, {:delete_game, game_id})
  end

  def get_game_port(game_id) do
    GenServer.call(__MODULE__, {:get_game_port, game_id})
  end

  def get_next_port do
    GenServer.call(__MODULE__, :get_next_port)
  end

  # Server callbacks

  @impl true
  def init(_opts) do
    Logger.info("Starting Discovery Server on port #{@port}")

    # Start the TCP server
    {:ok, socket} = :gen_tcp.listen(@port, [:binary, packet: :line, active: false, reuseaddr: true])

    # Start accepting connections
    start_accepting(socket)

    # Initial state with empty games list
    initial_state = %{
      socket: socket,
      games: %{}, # game_id => %{creator_name, state, port, game_data}
      next_port: 4000 # Next available port for game servers
    }
    {:ok, initial_state}
  end # Corrected end for init/1

  @impl true
  def handle_call(:list_games, _from, state) do
    games_list = Enum.map(state.games, fn {game_id, game_data} ->
      %{
        game_id: game_id,
        creator_name: game_data.creator_name,
        state: game_data.state,
        port: game_data.port
      }
    end)

    {:reply, games_list, state}
  end

  @impl true
  def handle_call({:get_game_port, game_id}, _from, state) do
    case Map.get(state.games, game_id) do
      nil ->
        {:reply, nil, state}
      game_data ->
        {:reply, game_data.port, state}
    end
  end

  @impl true
  def handle_call(:get_next_port, _from, state) do
    port = state.next_port
    new_state = %{state | next_port: port + 1}
    {:reply, port, new_state}
  end

  @impl true
  def handle_cast({:register_game, game_id, creator_name, game_data, port}, state) do
    Logger.info("Registered new game: #{game_id} by #{creator_name} on port #{port}")

    new_state = state
    |> put_in([:games, game_id], %{
      creator_name: creator_name,
      state: "en espera",
      port: port,
      game_data: game_data
    })

    {:noreply, new_state}
  end

  @impl true
  def handle_cast({:update_game_state, game_id, new_state}, state) do
    new_games =
      case Map.get(state.games, game_id) do
        nil ->
          state.games
        game_data ->
          Map.put(state.games, game_id, %{game_data | state: new_state})
      end

    {:noreply, %{state | games: new_games}}
  end

  @impl true
  def handle_cast({:delete_game, game_id}, state) do
    Logger.info("Deleting game: #{game_id}")

    new_games = Map.delete(state.games, game_id)
    {:noreply, %{state | games: new_games}}
  end

  @impl true
  def handle_info({:tcp, client, data}, state) do
    handle_tcp_data(client, data, state)
    {:noreply, state}
  end

  # Private functions

  defp start_accepting(socket) do
    Task.async(fn ->
      acceptor_loop(socket)
    end)
  end

  defp acceptor_loop(socket) do
    {:ok, client} = :gen_tcp.accept(socket)
    # Spawn a new process to handle this client
    Task.start(fn -> serve_client(client) end)
    # Continue accepting connections
    acceptor_loop(socket)
  end

  defp serve_client(client) do
    case :gen_tcp.recv(client, 0) do
      {:ok, data} ->
        try do
          decoded = Jason.decode!(data)
          handle_client_message(client, decoded)
        rescue
          e ->
            Logger.error("Error handling client message: #{inspect(e)}")
            send_response(client, %{status: "error", message: "Invalid message format"})
        end
      {:error, :closed} ->
        Logger.debug("Client closed connection")
      {:error, reason} ->
        Logger.error("Error receiving from client: #{inspect(reason)}")
    end
    :gen_tcp.close(client)
  end

  defp handle_client_message(client, %{"action" => "list_games"} = _message) do
    games = list_games()
    send_response(client, %{status: "success", games: games})
  end

  defp handle_client_message(client, %{"action" => "get_game_port", "game_id" => game_id}) do
    case get_game_port(game_id) do
      nil ->
        send_response(client, %{status: "error", message: "Game not found"})
      port ->
        send_response(client, %{status: "success", port: port})
    end
  end

  defp handle_client_message(client, %{"action" => "create_game", "game_data" => game_data, "creator_id" => creator_id}) do
    # Assign a port for the new game server
    port = get_next_available_port()
    game_id = game_data["game_id"]

    # Extract creator name from game data
    creator_name = get_creator_name(game_data, creator_id)

    # Register the game
    register_game(game_id, creator_name, game_data, port)

    # Start a game server for this game
    P2pGame.GameSupervisor.start_game_server(game_id, game_data, port)

    send_response(client, %{status: "success", port: port})
  end

  defp handle_client_message(client, message) do
    Logger.warn("Unknown message: #{inspect(message)}")
    send_response(client, %{status: "error", message: "Unknown action"})
  end

  defp send_response(client, response) do
    json = Jason.encode!(response) <> "\n"
    :gen_tcp.send(client, json)
  end

  defp get_next_available_port do
    # For now, just increment the port number
    # In a real system, you would check if the port is available
    GenServer.call(__MODULE__, :get_next_port)
  end

  defp get_creator_name(game_data, creator_id) do
    case game_data["players"] do
      nil -> "Unknown"
      players ->
        case Enum.find(players, fn p -> p["id"] == creator_id end) do
          nil -> "Unknown"
          player -> player["name"]
        end
    end
  end
end
