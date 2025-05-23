defmodule P2pGame.MixProject do
  use Mix.Project

  def project do
    [
      app: :p2p_game,
      version: "0.1.0",
      elixir: "~> 1.18",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: [:logger],
      mod: {P2pGame.Application, []}
    ]
  end

  # Run "mix help deps" to learn about dependencies.
  defp deps do
    [
      # JSON library for message encoding/decoding
      {:jason, "~> 1.4"}
    ]
  end
end
