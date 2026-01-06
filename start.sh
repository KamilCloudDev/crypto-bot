#!/bin/bash

# Ścieżka do pliku .env (zakładamy, że jest w tym samym folderze co skrypt)
ENV_PATH="./.env"
LOG_FILE="logbtcpln.txt"

# Sprawdzenie czy plik .env istnieje
if [ ! -f "$ENV_PATH" ]; then
    echo "❌ Błąd: Nie znaleziono pliku .env w $ENV_PATH"
    exit 1
fi

# (Opcjonalnie) Załadowanie zmiennych do środowiska skryptu Bash
export $(grep -v '^#' "$ENV_PATH" | xargs)

# 1. Automatyczne sprawdzanie i naprawa pliku logów
if [ -d "$LOG_FILE" ]; then
    echo "⚠️ Wykryto folder zamiast pliku logów. Usuwam i naprawiam..."
    rm -rf "$LOG_FILE"
    touch "$LOG_FILE"
elif [ ! -f "$LOG_FILE" ]; then
    echo "📝 Tworzę brakujący plik logów..."
    touch "$LOG_FILE"
fi

# Ustawienie uprawnień
chmod 666 "$LOG_FILE"

# 2. Budowanie obrazu
docker build -t btc-bot-final .

# 3. Usuwanie starego kontenera
docker rm -f btc-pln-bot || true

# 4. Uruchomienie bota
# Zmieniono --env-file na lokalny plik .env
docker run -d \
  --name btc-pln-bot \
  --env-file "$ENV_PATH" \
  --restart always \
  -v "$(pwd)/$LOG_FILE:/app/$LOG_FILE" \
  btc-bot-final

echo "✅ Gotowe! Bot działa korzystając z kluczy w $ENV_PATH."
echo "------------------------------------------"
tail -n 10 "$LOG_FILE"
