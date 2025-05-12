defmodule P2pGame.Application do
  # See https://hexdocs.pm/elixir/Application.html
  # for more information on OTP Applications
  @moduledoc false

  use Application
  require Logger

  @impl true
  def start(_type, _args) do
    Logger.info("Starting P2P Game Application")

    children = [
      # Registry for game servers
      {Registry, keys: :unique, name: P2pGame.GameRegistry},

      # Game supervisor for dynamic game servers
      {P2pGame.GameSupervisor, []},

      # Discovery server for game announcements
      {P2pGame.DiscoveryServer, []}
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: P2pGame.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
