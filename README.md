# Crypto Trading Bot

Bot do handlu kryptowalutami na giełdzie Binance (Spot), zoptymalizowany do działania w kontenerze Docker.

---

## 1. Wymagania

- [Docker](https://www.docker.com/products/docker-desktop/) zainstalowany na maszynie.
- [Git](https://git-scm.com/) do klonowania repozytorium.
- Konto na [Binance](https://www.binance.com/) z wygenerowanym kluczem API (uprawnienia do handlu Spot).

---

## 2. Architektura i Logika Bota

### Główne założenia strategii:
Bot implementuje strategię grid trading, która polega na składaniu zleceń kupna i sprzedaży w określonych interwałach cenowych.

1.  **Dynamiczna Wielkość Zlecenia:**
    - Całkowity kapitał (wartość PLN + BTC) jest dzielony przez `MAX_ILOSC_ZLECEN` (domyślnie **100**).
    - Zapewnia to skalowalność – im większy kapitał, tym większe zlecenia.

2.  **Scenariusz Startowy (Brak Otwartych Zleceń):**
    - Jeśli na koncie nie ma żadnych otwartych zleceń sprzedaży (SELL), bot natychmiast składa zlecenie kupna (MARKET BUY) za obliczoną kwotę.
    - Po zrealizowaniu zakupu, automatycznie wystawia zlecenie sprzedaży (LIMIT SELL) z ceną o **1% wyższą** od średniej ceny zakupu.

3.  **Zarządzanie Istniejącymi Zleceniami:**
    - Jeśli na rynku istnieją już zlecenia sprzedaży, bot monitoruje cenę i reaguje na jej spadki.
    - Próg wejścia jest dynamicznie obliczany na podstawie historycznego ATH (All-Time High) oraz ceny najniższego otwartego zlecenia:
      ```
      próg = (cena_najniższego_zlecenia * 0.125%) + (ATH * 1%)
      ```
    - Jeśli aktualna cena rynkowa spadnie poniżej `cena_najniższego_zlecenia - próg`, bot składa kolejne zlecenie kupna.

4.  **Ochrona przed Brakiem Środków (PLN):**
    - W sytuacji, gdy na koncie zabraknie PLN na kolejne zlecenie kupna, a cena nadal spada, bot:
        1. Anuluje **najwyższe** (najdroższe) zlecenie sprzedaży.
        2. Wystawia nowe zlecenie sprzedaży (LIMIT SELL) z ceną o **1% wyższą** od aktualnej ceny rynkowej, uwalniając w ten sposób środki i "zagęszczając" siatkę zleceń.

5.  **Automatyczna Redukcja Zleceń Sprzedaży:**
    - Aby zapobiec nadmiernemu blokowaniu środków w wielu małych zleceniach, bot automatycznie dba o to, by w danym momencie istniały **maksymalnie 2 aktywne zlecenia sprzedaży**.
    - Jeśli liczba zleceń sprzedaży przekroczy 2, bot **anuluje najstarsze (najwyższe cenowo)** zlecenia, aż pozostaną tylko dwa najnowsze. Pozostałe środki (BTC) stają się dostępne i oczekują na nowe, korzystniejsze okazje do sprzedaży w przyszłości.

6.  **Logowanie i Pętla:**
    - Wszystkie operacje są logowane do pliku `logbtcpln.txt` z dokładnym znacznikiem czasowym.
    - Bot podejmuje decyzje co **5 sekund**, zapewniając szybką reakcję na zmiany rynkowe.

---

## 3. Struktura Projektu

```
/
├─ main.py           # Główna logika bota
├─ .env              # Plik konfiguracyjny (klucze API)
├─ requirements.txt  # Zależności Python
├─ .gitignore        # Pliki ignorowane przez Git
└─ Dockerfile        # Definicja kontenera Docker
```

---

## 4. Konfiguracja i Uruchomienie

### a. Konfiguracja Kluczy API

1.  Utwórz plik `.env` w głównym katalogu projektu.
2.  Wklej do niego swoje klucze API z Binance:

    ```env
    BINANCE_API_KEY=TWÓJ_KLUCZ_API
    BINANCE_API_SECRET=TWÓJ_SEKRETNY_KLUCZ
    ```
    > **WAŻNE:** Plik `.env` jest ignorowany przez Git, aby chronić Twoje klucze. Nigdy nie udostępniaj go publicznie.

### b. Uruchomienie za pomocą Dockera

1.  **Zbuduj obraz Dockera:**
    Otwórz terminal w katalogu projektu i wykonaj polecenie:
    ```bash
    docker build -t crypto-bot .
    ```

2.  **Uruchom kontener:**
    Uruchom bota w tle za pomocą polecenia:
    ```bash
    docker run -d --name moj-bot --restart always --env-file .env crypto-bot
    ```
    - `-d`: uruchomienie w trybie "detached" (w tle).
    - `--name moj-bot`: nadanie nazwy kontenerowi.
    - `--restart always`: automatyczne ponowne uruchomienie w przypadku awarii.
    - `--env-file .env`: wstrzyknięcie zmiennych środowiskowych z pliku `.env`.

### c. Monitorowanie Logów

Aby na żywo śledzić działanie bota, użyj polecenia:
```bash
docker logs -f moj-bot
```

---

## 5. Rozwój i Wersjonowanie

Projekt jest zarządzany przez Git. Aby wprowadzić zmiany:

```bash
# Dodaj zmiany do przechowalni
git add .

# Zatwierdź zmiany z opisem
git commit -m "feat: Opis wprowadzonych zmian"

# Wyślij na zdalne repozytorium
git push origin main
```

---

## 6. Bezpieczeństwo

- **Izolacja:** Docker zapewnia pełną izolację środowiska bota od systemu operacyjnego.
- **Klucze API:** Nigdy nie umieszczaj kluczy API bezpośrednio w kodzie. Używaj pliku `.env`.
- **Uprawnienia:** Ogranicz uprawnienia klucza API na Binance tylko do handlu Spot.
