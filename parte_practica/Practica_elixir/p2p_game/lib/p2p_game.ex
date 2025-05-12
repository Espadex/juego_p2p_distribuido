defmodule P2pGame do
  @moduledoc """
  P2pGame is a distributed game server that manages peer-to-peer hierarchical game connections.
  """
  require Logger

  @doc """
  Lists all available games.
  """
  def list_games do
    P2pGame.DiscoveryServer.list_games()
  end

  @doc """
  Gets the port for a specific game.
  """
  def get_game_port(game_id) do
    P2pGame.DiscoveryServer.get_game_port(game_id)
  end

  @doc """
  Creates a new game with the given parameters.
  """
  def create_game(game_data, creator_id) do
    # The discovery server will assign a port and start a game server
    game_id = game_data["game_id"]
    creator_name = get_creator_name(game_data, creator_id)

    port = P2pGame.DiscoveryServer.get_next_port()
    P2pGame.DiscoveryServer.register_game(game_id, creator_name, game_data, port)
    P2pGame.GameSupervisor.start_game_server(game_id, game_data, port)

    {:ok, game_id, port}
  end

  @doc """
  Gets the state of a game.
  """
  def get_game_state(game_id) do
    P2pGame.GameServer.get_state(game_id)
  end

  @doc """
  Joins a player to a game.
  """
  def join_game(game_id, player_id, player_name) do
    P2pGame.GameServer.join_game(game_id, player_id, player_name)
  end

  @doc """
  Creates a team in a game.
  """
  def create_team(game_id, team_name) do
    P2pGame.GameServer.create_team(game_id, team_name)
  end

  @doc """
  Joins a player to a team.
  """
  def join_team(game_id, team_name, player_id) do
    P2pGame.GameServer.join_team(game_id, team_name, player_id)
  end

  @doc """
  Votes for a player to join a team.
  """
  def vote_for_join(game_id, voter_id, player_id, team_name, vote) do
    P2pGame.GameServer.vote_for_join(game_id, voter_id, player_id, team_name, vote)
  end

  @doc """
  Starts a game.
  """
  def start_game(game_id) do
    P2pGame.GameServer.start_game(game_id)
  end

  @doc """
  Rolls dice for a team.
  """
  def roll_dice(game_id, team_name, dice_roll, new_position) do
    P2pGame.GameServer.roll_dice(game_id, team_name, dice_roll, new_position)
  end

  @doc """
  Removes a player from a game.
  """
  def leave_game(game_id, player_id) do
    P2pGame.GameServer.leave_game(game_id, player_id)
  end

  @doc """
  Deletes a game.
  """
  def delete_game(game_id) do
    P2pGame.GameServer.delete_game(game_id)
  end

  # Private helper functions

  defp get_creator_name(game_data, creator_id) do
    players = game_data["players"] || []

    case Enum.find(players, fn p -> p["id"] == creator_id end) do
      nil -> "Unknown"
      player -> player["name"]
    end
  end
enddo
  @moduledoc """
  Documentation for `P2pGame`.
  """

  @doc """
  Hello world.

  ## Examples

      iex> P2pGame.hello()
      :world

  """
  def hello do
    :world
  end
end
