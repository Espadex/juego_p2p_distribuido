@echo off
rem Check if Elixir path argument is provided
if "%1"=="" (
    echo Starting game without Elixir path
    python connector.py
) else (
    echo Starting game with Elixir path: %1
    python connector.py --elixir-path "%1"
)
