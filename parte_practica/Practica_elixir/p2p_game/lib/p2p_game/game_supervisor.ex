defmodule P2pGame.GameSupervisor do
  @moduledoc """
  Supervisor for game servers.
  """
  use DynamicSupervisor
  require Logger

  def start_link(init_arg) do
    DynamicSupervisor.start_link(__MODULE__, init_arg, name: __MODULE__)
  end

  @impl true
  def init(_init_arg) do
    DynamicSupervisor.init(strategy: :one_for_one)
  end

  @doc """
  Starts a new game server for the given game.
  """
  def start_game_server(game_id, game_data, port) do
    child_spec = %{
      id: {P2pGame.GameServer, game_id},
      start: {P2pGame.GameServer, :start_link, [game_id, game_data, port]},
      restart: :transient
    }

    DynamicSupervisor.start_child(__MODULE__, child_spec)
  end

  @doc """
  Stops the game server for the given game.
  """
  def stop_game_server(game_id) do
    :ok = DynamicSupervisor.terminate_child(
      __MODULE__,
      pid_from_game_id(game_id)
    )
  end

  defp pid_from_game_id(game_id) do
    game_id
    |> via_tuple()
    |> GenServer.whereis()
  end

  defp via_tuple(game_id) do
    {:via, Registry, {P2pGame.GameRegistry, game_id}}
  end
end
