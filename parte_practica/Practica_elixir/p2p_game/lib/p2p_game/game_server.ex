defmodule P2pGame.GameServer do
  @moduledoc """
  Game server that handles a specific game session, running on a separate port.
  Acts as the master node for a specific game.
  """
  use GenServer
  require Logger

  # Client API

  def start_link(game_id, game_data, port) do
    GenServer.start_link(__MODULE__, {game_id, game_data, port}, name: via_tuple(game_id))
  end

  def get_state(game_id) do
    GenServer.call(via_tuple(game_id), :get_state)
  end

  def join_game(game_id, player_id, player_name) do
    GenServer.call(via_tuple(game_id), {:join_game, player_id, player_name})
  end

  def create_team(game_id, team_name) do
    GenServer.call(via_tuple(game_id), {:create_team, team_name})
  end

  def join_team(game_id, team_name, player_id) do
    GenServer.call(via_tuple(game_id), {:join_team, team_name, player_id})
  end

  def vote_for_join(game_id, voter_id, player_id, team_name, vote) do
    GenServer.call(via_tuple(game_id), {:vote_for_join, voter_id, player_id, team_name, vote})
  end

  def start_game(game_id) do
    GenServer.call(via_tuple(game_id), :start_game)
  end

  def roll_dice(game_id, team_name, dice_roll, new_position) do
    GenServer.call(via_tuple(game_id), {:roll_dice, team_name, dice_roll, new_position})
  end

  def leave_game(game_id, player_id) do
    GenServer.call(via_tuple(game_id), {:leave_game, player_id})
  end

  def delete_game(game_id) do
    # First notify the discovery server
    P2pGame.DiscoveryServer.delete_game(game_id)
    # Then stop the game server
    GenServer.stop(via_tuple(game_id))
  end

  defp via_tuple(game_id) do
    {:via, Registry, {P2pGame.GameRegistry, game_id}}
  end

  # Server callbacks

  @impl true
  def init({game_id, game_data, port}) do
    Logger.info("Starting Game Server for game: #{game_id} on port #{port}")

    # Start the TCP server for this game
    {:ok, socket} = :gen_tcp.listen(port, [:binary, packet: :line, active: false, reuseaddr: true])

    # Start accepting connections
    start_accepting(socket, game_id)

    # Initialize state from game data
    game_state = parse_game_data(game_data)

    {:ok, %{
      game_id: game_id,
      socket: socket,
      port: port,
      state: game_state,
      clients: %{}, # player_id => %{socket, callback_port}
      callback_sockets: %{} # port => socket
    }}
  end

  @impl true
  def handle_call(:get_state, _from, state) do
    {:reply, state.state, state}
  end

  @impl true
  def handle_call({:join_game, player_id, player_name}, _from, state) do
    Logger.info("Player #{player_name} (#{player_id}) joining game #{state.game_id}")

    # Add player to the game state
    new_state = add_player_to_game(state, player_id, player_name)

    # Broadcast the join to all clients
    broadcast_player_join(new_state, player_id, player_name)

    {:reply, new_state.state, new_state}
  end

  @impl true
  def handle_call({:create_team, team_name}, _from, state) do
    if state.state.started do
      {:reply, {:error, "Game already started"}, state}
    else
      Logger.info("Creating team #{team_name} in game #{state.game_id}")

      # Add team to the game state
      new_state = add_team_to_game(state, team_name)

      # Broadcast team creation
      broadcast_team_creation(new_state, team_name)

      {:reply, {:ok, "Team created"}, new_state}
    end
  end

  @impl true
  def handle_call({:join_team, team_name, player_id}, _from, state) do
    Logger.info("Player #{player_id} joining team #{team_name} in game #{state.game_id}")

    # Check if team exists
    case get_team(state, team_name) do
      nil ->
        {:reply, {:error, "Team does not exist"}, state}

      team ->
        # Check if the team is empty
        if Enum.empty?(team.players) do
          # Direct join
          new_state = add_player_to_team(state, team_name, player_id)

          # Broadcast team update
          broadcast_team_update(new_state, team_name)

          {:reply, {:ok, "Joined team"}, new_state}
        else
          # Send join request
          new_state = add_join_request(state, team_name, player_id)

          # Broadcast join request
          broadcast_join_request(new_state, team_name, player_id)

          {:reply, {:ok, "Join request sent"}, new_state}
        end
    end
  end

  @impl true
  def handle_call({:vote_for_join, voter_id, player_id, team_name, vote}, _from, state) do
    Logger.info("Player #{voter_id} voted #{vote} for player #{player_id} to join team #{team_name}")

    # Add vote
    new_state = add_vote(state, voter_id, player_id, team_name, vote)

    # Check if vote passed
    {new_state, result} = check_vote_result(new_state, player_id, team_name)

    # Broadcast vote result
    if result == :joined do
      broadcast_team_update(new_state, team_name)
    end

    {:reply, {:ok, "Vote recorded", result}, new_state}
  end

  @impl true
  def handle_call(:start_game, _from, state) do
    if state.state.started do
      {:reply, {:error, "Game already started"}, state}
    else
      # Check if there are at least 2 teams with players
      teams_with_players = Enum.filter(state.state.teams, fn {_, team} ->
        not Enum.empty?(team.players)
      end)

      if length(teams_with_players) < 2 do
        {:reply, {:error, "Need at least 2 teams with players"}, state}
      else
        Logger.info("Starting game #{state.game_id}")

        # Remove empty teams
        teams = Enum.reject(state.state.teams, fn {_, team} ->
          Enum.empty?(team.players)
        end) |> Enum.into(%{})

        # Randomize turn order
        team_names = Map.keys(teams)
        turn_order = Enum.shuffle(team_names)

        # Update game state
        new_game_state = %{
          state.state |
          started: true,
          state: "en juego",
          teams: teams,
          turn_order: turn_order,
          current_team_index: 0
        }

        new_state = %{state | state: new_game_state}

        # Update discovery server
        P2pGame.DiscoveryServer.update_game_state(state.game_id, "en juego")

        # Broadcast game start
        broadcast_game_start(new_state)

        {:reply, {:ok, "Game started"}, new_state}
      end
    end
  end

  @impl true
  def handle_call({:roll_dice, team_name, dice_roll, new_position}, _from, state) do
    if not state.state.started do
      {:reply, {:error, "Game not started"}, state}
    else
      # Check if it's this team's turn
      current_team = Enum.at(state.state.turn_order, state.state.current_team_index)

      if current_team != team_name do
        {:reply, {:error, "Not this team's turn"}, state}
      else
        Logger.info("Team #{team_name} rolled #{dice_roll}, new position: #{new_position}")

        # Update team position
        teams = Map.update!(state.state.teams, team_name, fn team ->
          %{team | position: new_position}
        end)

        # Check for winner
        {new_game_state, winner} =
          if new_position >= state.state.board_size do
            Logger.info("Team #{team_name} wins!")
            {%{state.state | teams: teams, winner: team_name}, team_name}
          else
            # Advance to next team
            next_index = rem(state.state.current_team_index + 1, length(state.state.turn_order))
            {%{state.state | teams: teams, current_team_index: next_index}, nil}
          end

        new_state = %{state | state: new_game_state}

        # Broadcast dice roll
        broadcast_dice_roll(new_state, team_name, dice_roll, new_position)

        # If we have a winner, broadcast game end
        if winner do
          broadcast_game_end(new_state, winner)
        end

        {:reply, {:ok, "Dice rolled"}, new_state}
      end
    end
  end

  @impl true
  def handle_call({:leave_game, player_id}, _from, state) do
    Logger.info("Player #{player_id} leaving game #{state.game_id}")

    # Find player's team
    {team_name, _} = Enum.find(state.state.teams, {nil, nil}, fn {_, team} ->
      Enum.any?(team.players, fn p -> p.id == player_id end)
    end)

    # Remove player from team
    new_state =
      if team_name do
        remove_player_from_team(state, team_name, player_id)
      else
        state
      end

    # Remove client connection if any
    new_clients = Map.delete(new_state.clients, player_id)
    new_state = %{new_state | clients: new_clients}

    # Broadcast player leave
    broadcast_player_leave(new_state, player_id, team_name)

    # Check if the team is now empty and the game is in progress
    if team_name && new_state.state.started do
      team = get_team(new_state, team_name)

      if team && Enum.empty?(team.players) do
        # Check if this was the last team
        teams_with_players = Enum.filter(new_state.state.teams, fn {_, team} ->
          not Enum.empty?(team.players)
        end)

        if length(teams_with_players) == 1 do
          # Only one team left, they win
          [{winner_name, _}] = teams_with_players

          new_game_state = %{new_state.state | winner: winner_name}
          new_state = %{new_state | state: new_game_state}

          # Broadcast game end
          broadcast_game_end(new_state, winner_name)
        end
      end
    end

    {:reply, {:ok, "Left game"}, new_state}
  end

  # Private functions

  defp start_accepting(socket, game_id) do
    Task.async(fn ->
      acceptor_loop(socket, game_id)
    end)
  end

  defp acceptor_loop(socket, game_id) do
    {:ok, client} = :gen_tcp.accept(socket)
    # Spawn a new process to handle this client
    Task.start(fn -> serve_game_client(client, game_id) end)
    # Continue accepting connections
    acceptor_loop(socket, game_id)
  end

  defp serve_game_client(client, game_id) do
    case :gen_tcp.recv(client, 0) do
      {:ok, data} ->
        try do
          decoded = Jason.decode!(data)
          handle_game_client_message(client, decoded, game_id)
        rescue
          e ->
            Logger.error("Error handling game client message: #{inspect(e)}")
            send_response(client, %{status: "error", message: "Invalid message format"})
        end
      {:error, :closed} ->
        Logger.debug("Game client closed connection")
      {:error, reason} ->
        Logger.error("Error receiving from game client: #{inspect(reason)}")
    end
    :gen_tcp.close(client)
  end

  defp handle_game_client_message(client, %{"action" => "join_game", "game_id" => game_id, "player_id" => player_id, "player_name" => player_name}, game_id) do
    case join_game(game_id, player_id, player_name) do
      %{} = game_state ->
        # Store the client socket for callbacks
        GenServer.cast(via_tuple(game_id), {:register_client, player_id, client})

        send_response(client, %{status: "success", game_state: game_state})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "create_team", "game_id" => game_id, "team_name" => team_name}, game_id) do
    case create_team(game_id, team_name) do
      {:ok, message} ->
        send_response(client, %{status: "success", message: message})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "join_team", "game_id" => game_id, "team_name" => team_name, "player_id" => player_id}, game_id) do
    case join_team(game_id, team_name, player_id) do
      {:ok, message} ->
        send_response(client, %{status: "success", message: message})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "vote", "game_id" => game_id, "voter_id" => voter_id, "player_id" => player_id, "team_name" => team_name, "vote" => vote}, game_id) do
    case vote_for_join(game_id, voter_id, player_id, team_name, vote) do
      {:ok, message, result} ->
        send_response(client, %{status: "success", message: message, result: result})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "start_game", "game_id" => game_id}, game_id) do
    case start_game(game_id) do
      {:ok, message} ->
        send_response(client, %{status: "success", message: message})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "roll_dice", "game_id" => game_id, "team_name" => team_name, "dice_roll" => dice_roll, "new_position" => new_position}, game_id) do
    case roll_dice(game_id, team_name, dice_roll, new_position) do
      {:ok, message} ->
        send_response(client, %{status: "success", message: message})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "leave_game", "game_id" => game_id, "player_id" => player_id}, game_id) do
    case leave_game(game_id, player_id) do
      {:ok, message} ->
        send_response(client, %{status: "success", message: message})
      {:error, reason} ->
        send_response(client, %{status: "error", message: reason})
    end
  end

  defp handle_game_client_message(client, %{"action" => "delete_game", "game_id" => game_id}, game_id) do
    # Only the creator should be able to delete the game, but we're simplifying here
    delete_game(game_id)
    send_response(client, %{status: "success", message: "Game deleted"})
  end

  defp handle_game_client_message(client, %{"action" => "register_callback_socket", "port" => port, "player_id" => player_id}, game_id) do
    GenServer.cast(via_tuple(game_id), {:register_callback_port, player_id, port})
    send_response(client, %{status: "success", message: "Callback registered"})
  end

  defp handle_game_client_message(client, message, game_id) do
    Logger.warn("Unknown game message: #{inspect(message)} for game #{game_id}")
    send_response(client, %{status: "error", message: "Unknown action"})
  end

  @impl true
  def handle_cast({:register_client, player_id, socket}, state) do
    new_clients = Map.put(state.clients, player_id, %{socket: socket, callback_port: nil})
    {:noreply, %{state | clients: new_clients}}
  end

  @impl true
  def handle_cast({:register_callback_port, player_id, port}, state) do
    new_clients =
      case Map.get(state.clients, player_id) do
        nil ->
          Map.put(state.clients, player_id, %{socket: nil, callback_port: port})
        client_data ->
          Map.put(state.clients, player_id, %{client_data | callback_port: port})
      end

    {:noreply, %{state | clients: new_clients}}
  end

  defp send_response(client, response) do
    json = Jason.encode!(response) <> "\n"
    :gen_tcp.send(client, json)
  end

  defp parse_game_data(game_data) do
    # Convert string keys to atoms
    %{
      game_id: game_data["game_id"],
      creator_id: game_data["creator_id"],
      max_teams: game_data["max_teams"],
      max_players_per_team: game_data["max_players_per_team"],
      board_size: game_data["board_size"],
      dice_min: game_data["dice_min"],
      dice_max: game_data["dice_max"],
      started: game_data["started"] || false,
      state: game_data["state"] || "en espera",
      current_team_index: game_data["current_team_index"] || 0,
      turn_order: game_data["turn_order"] || [],
      teams: parse_teams(game_data["teams"] || %{}),
      players: parse_players(game_data["players"] || []),
      winner: game_data["winner"]
    }
  end

  defp parse_teams(teams) do
    Enum.map(teams, fn {name, team_data} ->
      {name, %{
        name: name,
        position: team_data["position"] || 0,
        players: [], # We'll populate this from players data
        join_requests: Map.new(team_data["join_requests"] || [], fn req_id -> {req_id, []} end)
      }}
    end) |> Enum.into(%{})
  end

  defp parse_players(players) do
    Enum.map(players, fn player_data ->
      %{
        id: player_data["id"],
        name: player_data["name"],
        team_name: player_data["team_name"]
      }
    end)
  end

  defp add_player_to_game(state, player_id, player_name) do
    # Check if player already exists
    player_exists = Enum.any?(state.state.players, fn p -> p.id == player_id end)

    if player_exists do
      state
    else
      # Add player to state
      new_players = [%{id: player_id, name: player_name, team_name: nil} | state.state.players]
      new_game_state = %{state.state | players: new_players}

      %{state | state: new_game_state}
    end
  end

  defp add_team_to_game(state, team_name) do
    # Check if team already exists
    if Map.has_key?(state.state.teams, team_name) do
      state
    else
      # Add team to state
      new_teams = Map.put(state.state.teams, team_name, %{
        name: team_name,
        position: 0,
        players: [],
        join_requests: %{}
      })

      new_game_state = %{state.state | teams: new_teams}

      %{state | state: new_game_state}
    end
  end

  defp get_team(state, team_name) do
    Map.get(state.state.teams, team_name)
  end

  defp add_player_to_team(state, team_name, player_id) do
    # Find player
    player = Enum.find(state.state.players, fn p -> p.id == player_id end)

    if is_nil(player) do
      state
    else
      # Remove player from current team if any
      new_state =
        if player.team_name do
          remove_player_from_team(state, player.team_name, player_id)
        else
          state
        end

      # Add player to new team
      teams = Map.update!(new_state.state.teams, team_name, fn team ->
        %{team | players: [player | team.players]}
      end)

      # Update player's team
      players = Enum.map(new_state.state.players, fn p ->
        if p.id == player_id do
          %{p | team_name: team_name}
        else
          p
        end
      end)

      new_game_state = %{new_state.state | teams: teams, players: players}

      %{new_state | state: new_game_state}
    end
  end

  defp remove_player_from_team(state, team_name, player_id) do
    # Update team's players
    teams = Map.update!(state.state.teams, team_name, fn team ->
      %{team | players: Enum.reject(team.players, fn p -> p.id == player_id end)}
    end)

    # Update player's team
    players = Enum.map(state.state.players, fn p ->
      if p.id == player_id do
        %{p | team_name: nil}
      else
        p
      end
    end)

    new_game_state = %{state.state | teams: teams, players: players}

    %{state | state: new_game_state}
  end

  defp add_join_request(state, team_name, player_id) do
    # Check if request already exists
    team = get_team(state, team_name)

    if is_nil(team) or Map.has_key?(team.join_requests, player_id) do
      state
    else
      # Add request
      teams = Map.update!(state.state.teams, team_name, fn team ->
        new_requests = Map.put(team.join_requests, player_id, [])
        %{team | join_requests: new_requests}
      end)

      new_game_state = %{state.state | teams: teams}

      %{state | state: new_game_state}
    end
  end

  defp add_vote(state, voter_id, player_id, team_name, vote) do
    # Get team
    team = get_team(state, team_name)

    if is_nil(team) or not Map.has_key?(team.join_requests, player_id) do
      state
    else
      # Check if voter is in the team
      voter_in_team = Enum.any?(team.players, fn p -> p.id == voter_id end)

      if not voter_in_team do
        state
      else
        # Add vote
        teams = Map.update!(state.state.teams, team_name, fn team ->
          if vote do
            new_votes = [voter_id | Map.get(team.join_requests, player_id, [])]
            new_requests = Map.put(team.join_requests, player_id, new_votes)
            %{team | join_requests: new_requests}
          else
            team
          end
        end)

        new_game_state = %{state.state | teams: teams}

        %{state | state: new_game_state}
      end
    end
  end

  defp check_vote_result(state, player_id, team_name) do
    # Get team
    team = get_team(state, team_name)

    if is_nil(team) or not Map.has_key?(team.join_requests, player_id) do
      {state, :pending}
    else
      # Count votes
      votes = Map.get(team.join_requests, player_id, [])
      yes_votes = length(votes)
      total_voters = length(team.players)

      # Check majority
      if yes_votes > total_voters / 2 do
        # Add player to team
        new_state = add_player_to_team(state, team_name, player_id)

        # Remove request
        teams = Map.update!(new_state.state.teams, team_name, fn team ->
          %{team | join_requests: Map.delete(team.join_requests, player_id)}
        end)

        new_game_state = %{new_state.state | teams: teams}

        {%{new_state | state: new_game_state}, :joined}
      else
        {state, :pending}
      end
    end
  end

  # Broadcast functions

  defp broadcast_player_join(state, player_id, player_name) do
    message = %{
      action: "player_join",
      player_id: player_id,
      player_name: player_name
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_player_leave(state, player_id, team_name) do
    message = %{
      action: "player_leave",
      player_id: player_id,
      team_name: team_name
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_team_creation(state, team_name) do
    team = get_team(state, team_name)

    message = %{
      action: "team_update",
      team_name: team_name,
      team_data: %{
        position: team.position,
        players: team.players,
        join_requests: Map.keys(team.join_requests)
      }
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_team_update(state, team_name) do
    team = get_team(state, team_name)

    message = %{
      action: "team_update",
      team_name: team_name,
      team_data: %{
        position: team.position,
        players: team.players,
        join_requests: Map.keys(team.join_requests)
      }
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_join_request(state, team_name, player_id) do
    message = %{
      action: "join_request",
      team_name: team_name,
      player_id: player_id,
      player_name: get_player_name(state, player_id)
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_game_start(state) do
    message = %{
      action: "game_start",
      turn_order: state.state.turn_order,
      current_team: Enum.at(state.state.turn_order, state.state.current_team_index)
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_game_end(state, winner) do
    message = %{
      action: "game_end",
      winner: winner
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_dice_roll(state, team_name, dice_roll, new_position) do
    next_index = rem(state.state.current_team_index + 1, length(state.state.turn_order))
    next_team = Enum.at(state.state.turn_order, next_index)

    message = %{
      action: "dice_roll",
      team_name: team_name,
      dice_roll: dice_roll,
      new_position: new_position,
      next_team: next_team
    }

    broadcast_to_all_clients(state, message)
  end

  defp broadcast_to_all_clients(state, message) do
    Enum.each(state.clients, fn {_player_id, client_data} ->
      if client_data.callback_port do
        send_callback(client_data.callback_port, message)
      end
    end)
  end

  defp send_callback(port, message) do
    Task.start(fn ->
      try do
        {:ok, socket} = :gen_tcp.connect('localhost', port, [:binary, packet: :line, active: false])
        json = Jason.encode!(message) <> "\n"
        :gen_tcp.send(socket, json)
        :gen_tcp.close(socket)
      rescue
        e -> Logger.error("Error sending callback: #{inspect(e)}")
      end
    end)
  end

  defp get_player_name(state, player_id) do
    player = Enum.find(state.state.players, fn p -> p.id == player_id end)
    player && player.name || "Unknown"
  end
end
